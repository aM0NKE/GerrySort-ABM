import random

import mesa_geo as mg
from shapely.geometry import Point, Polygon, MultiPolygon
import geopandas as gpd
import math


class PersonAgent(mg.GeoAgent):
    SIMILARITY_THRESHOLD = 0.3

    def __init__(self, unique_id, model, geometry, crs, is_red, region_id):
        super().__init__(unique_id, model, geometry, crs)
        self.is_red = is_red
        self.region_id = region_id

    @property
    def is_unhappy(self):
        if self.is_red:
            return (
                self.model.space.get_region_by_id(self.region_id).red_pct
                < self.SIMILARITY_THRESHOLD
            )
        else:
            return (
                1 - self.model.space.get_region_by_id(self.region_id).red_pct
            ) < self.SIMILARITY_THRESHOLD

    def step(self):
        if self.is_unhappy:
            random_region_id = self.model.space.get_random_region_id()
            self.model.space.remove_person_from_region(self)
            self.model.space.add_person_to_region(self, region_id=random_region_id)


class RegionAgent(mg.GeoAgent):
    init_num_people: int
    red_cnt: int
    blue_cnt: int
    color: str
    red_pct: float

    def __init__(self, unique_id, model, geometry, crs, init_num_people=10):
        super().__init__(unique_id, model, geometry, crs)
        self.init_num_people = init_num_people
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

    def random_point(self):
        min_x, min_y, max_x, max_y = self.geometry.bounds
        while not self.geometry.contains(
            random_point := Point(
                random.uniform(min_x, max_x), random.uniform(min_y, max_y)
            )
        ):
            continue
        return random_point

    def add_person(self, person):
        if person.is_red:
            self.red_cnt += 1
        else:
            self.blue_cnt += 1

    def remove_person(self, person):
        if person.is_red:
            self.red_cnt -= 1
        else:
            self.blue_cnt -= 1

    def calculate_wasted_votes(self):
        red_wasted_votes = 0
        blue_wasted_votes = 0
        
        if self.red_pct > 0.5:
            red_wasted_votes = self.red_cnt - math.ceil((self.red_cnt + self.blue_cnt) / 2)
            blue_wasted_votes = self.blue_cnt

        elif self.red_pct < 0.5:
            red_wasted_votes = self.red_cnt
            blue_wasted_votes = self.blue_cnt - math.ceil((self.red_cnt + self.blue_cnt) / 2)
        
        return red_wasted_votes, blue_wasted_votes

    def update_red_blue_counts(self):
        # Reset red and blue counts
        self.red_cnt = 0
        self.blue_cnt = 0

        # Update the red and blue counts after redistricting
        for person in self.model.space.agents:
            if isinstance(person, PersonAgent) and self.geometry.contains(person.geometry):
                # Add the person to the region
                self.add_person(person)
                # Update person reigon_id
                person.region_id = self.unique_id
    
    def update_color(self):
        # Update the color based on the majority of red or blue PersonAgents
        if self.red_cnt > self.blue_cnt:
            self.color = "Red"
        elif self.red_cnt < self.blue_cnt:
            self.color = "Blue"
        else:
            self.color = "Grey"

    def update_geometry(self, new_geometry):
        if isinstance(new_geometry, Polygon):
            # Convert a single Polygon to a MultiPolygon for consistency
            new_geometry = MultiPolygon([new_geometry])

        # Update the geometry of the RegionAgent
        self.geometry = new_geometry