import mesa_geo as mg
import random
from math import ceil
from shapely.geometry import Point, Polygon, MultiPolygon

from .person import PersonAgent

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
