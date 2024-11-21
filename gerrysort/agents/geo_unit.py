import mesa_geo as mg
from shapely.geometry import Point
from math import ceil
import random

class GeoAgent(mg.GeoAgent):
    type: str
    reps: list
    dems: list
    rep_cnt: int
    dem_cnt: int
    num_people: int
    capacity: int
    precincts: list
    color: str

    def __init__(self, unique_id, model, geometry, crs, type):
        super().__init__(unique_id, model, geometry, crs)
        self.type = type
        self.num_people = 0
        self.rep_cnt = 0
        self.dem_cnt = 0
        self.color = 'Grey'

        if self.type == 'precinct':
            self.reps = []
            self.dems = []
        elif self.type == 'county':
            self.capacity = 0
            self.precincts = []
        elif self.type == 'congressional':
            self.competitive = None
            self.precincts = []
        else: # State house and senate districts
            self.precincts = []

    def random_point(self):
        min_x, min_y, max_x, max_y = self.geometry.bounds
        while not self.geometry.contains(
            random_point := Point(
                random.uniform(min_x, max_x), random.uniform(min_y, max_y)
            )):
            continue
        return random_point

    def update_majority(self):
        if self.rep_cnt > self.dem_cnt:
            self.color = 'Red'
        elif self.dem_cnt > self.rep_cnt:
            self.color = 'Blue'
        else:
            self.color = 'Grey'

    def calculate_wasted_votes(self):
        rep_wasted_votes = 0
        dem_wasted_votes = 0

        total_votes = self.rep_cnt + self.dem_cnt
        majority_threshold = ceil(total_votes / 2)
        if self.color == 'Red':
            rep_wasted_votes = self.rep_cnt - majority_threshold
            dem_wasted_votes = self.dem_cnt
        elif self.color == 'Blue':
            rep_wasted_votes = self.rep_cnt
            dem_wasted_votes = self.dem_cnt - majority_threshold
        else:
            rep_wasted_votes = 0
            dem_wasted_votes = 0
        
        return rep_wasted_votes, dem_wasted_votes
    