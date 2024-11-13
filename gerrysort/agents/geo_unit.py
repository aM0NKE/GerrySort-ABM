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
            rep_cnt = len(self.reps)
            dem_cnt = len(self.dems)
        else:
            rep_cnt = self.rep_cnt
            dem_cnt = self.dem_cnt
        if rep_cnt > dem_cnt:
            self.color = 'Red'
        elif rep_cnt < dem_cnt:
            self.color = 'Blue'
        else:
            self.color = 'Grey'

    def calculate_wasted_votes(self):
        '''
        Returns the wasted votes in a geographical unit for the Dem and Rep party.
        '''
        rep_wasted_votes = 0
        dem_wasted_votes = 0

        if self.type == 'precinct':
            total_votes = len(self.reps) + len(self.dems)
        else:
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
    
    def update_geometry(self, new_geometry):
        # Print type for debugging
        # print('NEW new geometry type:', type(new_geometry))
        old_geometry = self.geometry
        # check if old geometry is same as new geometry
        if old_geometry == new_geometry:
            print('Old and new geometries are the same')
        else:
            print('Old and new geometries are different')
        self.geometry = new_geometry