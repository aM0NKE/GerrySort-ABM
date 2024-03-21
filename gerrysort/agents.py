import random

import mesa_geo as mg
from shapely.geometry import Point, Polygon, MultiPolygon
import geopandas as gpd
from math import radians, sin, cos, sqrt, atan2, ceil
from geopy.distance import great_circle


class PersonAgent(mg.GeoAgent):
    is_red: bool
    district_id: str
    county_id: str
    utility: float
    is_unhappy: bool

    def __init__(self, unique_id, model, geometry, crs, is_red, district_id, county_id):
        super().__init__(unique_id, model, geometry, crs)
        self.is_red = is_red
        self.district_id = district_id
        self.county_id = county_id
        self.utility = 0

    @property
    def is_unhappy(self):
        return self.utility < self.SIMILARITY_THRESHOLD

    def calculate_utility(self, county_id, A=1, alpha=(1, 1, 1)):
        # Party affilliation matching county party majority
        county = self.model.space.get_county_by_id(county_id)
        if self.is_red and county.red_pct > 0.5:
            X1 = 1
        elif not self.is_red and county.red_pct < 0.5:
            X1 = 1
        else:
            X1 = 0

        # Party affilliation matching district party majority
        district = self.model.space.get_district_by_id(self.district_id)
        if self.is_red and district.red_pct > 0.5:
            X2 = 1
        elif not self.is_red and district.red_pct < 0.5:
            X2 = 1
        else:
            X2 = 0.25

        # Urbanicity matching county urbanicity
        if self.is_red and county.RUCACAT == 'rural':
            X3 = 1
        elif self.is_red and county.RUCACAT == 'small_town':
            X3 = 0.5
        elif not self.is_red and county.RUCACAT == 'urban':
            X3 = 1
        elif not self.is_red and county.RUCACAT == 'large_town':
            X3 = 0.5
        else:
            X3 = 0

        # Return utility
        a1, a2, a3 = alpha
        utility = A * X1**a1 * X2**a2 * X3**a3
        return utility

    def update_utility(self):
        self.utility = self.calculate_utility(self.county_id)

    def sort(self):
        # Evaluate potential moving options
        for i in range(self.model.n_moving_options):
            # Get a random county
            random_county_id = self.model.space.get_random_county_id()
            random_county_utility = self.calculate_utility(random_county_id)
            random_county_centroid = self.model.space.get_county_by_id(random_county_id).geometry.centroid
            
            # Calculate distance to random county
            MAX_DIST = 475 # normalize distance by max distance (MN: 475 miles)
            distance = great_circle((self.geometry.y, self.geometry.x), (random_county_centroid.y, random_county_centroid.x)).miles / MAX_DIST
            
            # Calculate discounted utility
            discounted_utility =  random_county_utility * (self.model.distance_decay * (1 - distance))
            
            # Move if discounted utility is greater than current utility
            if discounted_utility > self.utility:
                self.model.space.remove_person_from_county(self)
                self.model.space.add_person_to_county(self, county_id=random_county_id)
                break

    def step(self):
        self.update_utility()
        if self.utility < self.SIMILARITY_THRESHOLD:
            self.sort()

class CountyAgent(mg.GeoAgent):
    num_people: int
    red_cnt: int
    blue_cnt: int
    color: str
    red_pct: float
    district_id: str

    def __init__(self, unique_id, model, geometry, crs):
        super().__init__(unique_id, model, geometry, crs)
        self.num_people = 0
        self.red_cnt = 0
        self.blue_cnt = 0
        self.red_pct = 0
        self.district_id = None

    def random_point(self):
        min_x, min_y, max_x, max_y = self.geometry.bounds
        while not self.geometry.contains(
            random_point := Point(
                random.uniform(min_x, max_x), random.uniform(min_y, max_y)
            )
        ):
            continue
        return random_point
    
    def update_county_data(self):
        self.num_people = 0
        self.red_cnt = 0
        self.blue_cnt = 0

        for person in self.model.space.agents:
            if isinstance(person, PersonAgent) and self.geometry.contains(person.geometry):
                self.num_people += 1
                if person.is_red:
                    self.red_cnt += 1
                else:
                    self.blue_cnt += 1
            
            person.county_id = self.unique_id

        try: self.red_pct = self.red_cnt / self.num_people
        except ZeroDivisionError: self.red_pct = 0.5

    def step(self):
        self.update_county_data()

class DistrictAgent(mg.GeoAgent):
    num_people: int
    red_cnt: int
    blue_cnt: int
    color: str
    red_pct: float

    def __init__(self, unique_id, model, geometry, crs):
        super().__init__(unique_id, model, geometry, crs)
        self.num_people = 0
        self.red_cnt = 0
        self.blue_cnt = 0
        self.color = 'Grey'

    @property
    def red_pct(self):
        if self.red_cnt == 0:
            return 0
        elif self.blue_cnt == 0:
            return 1
        elif self.red_cnt == 0 and self.blue_cnt == 0:
            return 0.5
        else:
            return self.red_cnt / (self.red_cnt + self.blue_cnt)

    def calculate_wasted_votes(self):
        red_wasted_votes = 0
        blue_wasted_votes = 0
        
        if self.red_pct > 0.5:
            red_wasted_votes = self.red_cnt - ceil((self.red_cnt + self.blue_cnt) / 2)
            blue_wasted_votes = self.blue_cnt

        elif self.red_pct < 0.5:
            red_wasted_votes = self.red_cnt
            blue_wasted_votes = self.blue_cnt - ceil((self.red_cnt + self.blue_cnt) / 2)

        else:
            red_wasted_votes = 0
            blue_wasted_votes = 0
        
        return red_wasted_votes, blue_wasted_votes
    
    def update_district_geometry(self, new_geometry):
        if isinstance(new_geometry, Polygon):
            new_geometry = MultiPolygon([new_geometry])

        self.geometry = new_geometry

    def update_district_data(self):
        self.num_people = 0
        self.red_cnt = 0
        self.blue_cnt = 0

        for person in self.model.space.agents:
            if isinstance(person, PersonAgent) and self.geometry.contains(person.geometry):
                self.num_people += 1
                if person.is_red:
                    self.red_cnt += 1
                else:
                    self.blue_cnt += 1

                person.district_id = self.unique_id
    
    def update_district_color(self):
        if self.red_cnt > self.blue_cnt:
            self.color = "Red"
        elif self.red_cnt < self.blue_cnt:
            self.color = "Blue"
        else:
            self.color = "Grey"

    def step(self):
        self.update_district_data()
        self.update_district_color()
