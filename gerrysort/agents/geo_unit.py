import mesa_geo as mg
import random
from math import ceil
from shapely.geometry import Point, Polygon, MultiPolygon

class GeoAgent(mg.GeoAgent):
    type: str
    num_people: int
    red_cnt: int
    blue_cnt: int
    red_pct: float
    blue_pct: float
    color: str

    def __init__(self, unique_id, model, geometry, crs, type):
        super().__init__(unique_id, model, geometry, crs)
        self.type = type
        
        self.num_people = 0
        if self.type == 'precinct':
            self.reps = []
            self.dems = []
            self.color = 'Grey'
        elif self.type == 'county':
            self.rep_cnt = 0
            self.dem_cnt = 0
            self.capacity = 0
            self.precincts = []
            self.color = 'Grey'
        if self.type == 'congressional':
            self.rep_cnt = 0
            self.dem_cnt = 0
            self.num_people = 0
            self.precincts = []
            self.color = 'Grey'

    def random_point(self):
        # Extract bounds of county
        min_x, min_y, max_x, max_y = self.geometry.bounds
        # Draw random point within bounds
        while not self.geometry.contains(
            random_point := Point(
                random.uniform(min_x, max_x), random.uniform(min_y, max_y)
            )):
            continue
        return random_point

    def update_majority(self):
        if self.type == 'precinct':
            red_cnt = len(self.reps)
            blue_cnt = len(self.dems)
        else:
            red_cnt = self.rep_cnt
            blue_cnt = self.dem_cnt
        if red_cnt > blue_cnt:
            self.color = 'Red'
        elif red_cnt < blue_cnt:
            self.color = 'Blue'
        else:
            self.color = 'Grey'

    def calculate_wasted_votes(self):
        '''
        Returns the wasted votes in a geographical unit for the Dem and Rep party.
        '''
        red_wasted_votes = 0
        blue_wasted_votes = 0

        total_votes = self.red_cnt + self.blue_cnt
        majority_threshold = ceil(total_votes / 2)
        
        if self.color == 'Red':
            red_wasted_votes = self.red_cnt - majority_threshold
            blue_wasted_votes = self.blue_cnt
        elif self.color == 'Blue':
            red_wasted_votes = self.red_cnt
            blue_wasted_votes = self.blue_cnt - majority_threshold
        else:
            red_wasted_votes = 0
            blue_wasted_votes = 0
        
        return red_wasted_votes, blue_wasted_votes
    
    def update_geometry(self, new_geometry):
        '''
        Updates the geometry of a geographical unit.
        '''
        if isinstance(new_geometry, Polygon):
            new_geometry = MultiPolygon([new_geometry])
        self.geometry = new_geometry

