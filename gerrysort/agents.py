import random

import mesa_geo as mg
from shapely.geometry import Point, Polygon, MultiPolygon
import geopandas as gpd


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
        else:
            try: return self.red_cnt / (self.red_cnt + self.blue_cnt)
            except: return 0

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

    def update_red_blue_counts(self):
        # Reset red and blue counts
        self.red_cnt = 0
        self.blue_cnt = 0

        # Update the red and blue counts based on the new geometry
        for person in self.model.space.agents:
            if isinstance(person, PersonAgent) and self.geometry.contains(person.geometry):
                self.add_person(person)
    
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