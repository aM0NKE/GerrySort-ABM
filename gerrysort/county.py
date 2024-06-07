import mesa_geo as mg
import random
from shapely.geometry import Point, Polygon, MultiPolygon

from .person import PersonAgent

class CountyAgent(mg.GeoAgent):
    capacity: int
    num_people: int
    red_cnt: int
    blue_cnt: int
    color: str
    red_pct: float
    district_id: str

    def __init__(self, unique_id, model, geometry, crs):
        super().__init__(unique_id, model, geometry, crs)
        self.capacity = 0
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