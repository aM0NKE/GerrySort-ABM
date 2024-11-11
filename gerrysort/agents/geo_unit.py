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
        '''
        Initialize electoral district agent.

        unique_id: Unique identifier of the district
        model: Model containing the district
        geometry: Geometry of the district
        crs: Coordinate Reference System of the district

        Attributes:
            type: Type of the district (congressional, state-senate, state-house)
            num_people: Number of people in the district
            red_cnt: Number of republican agents in the district
            blue_cnt: Number of democratic agents in the district

        '''
        super().__init__(unique_id, model, geometry, crs)
        self.type = type
        self.num_people = 0
        self.red_cnt = 0
        self.blue_cnt = 0
        self.red_pct = 0
        self.blue_pct = 0
        self.color = 'Grey'
        if self.type == 'county':
            self.district_id = None
            self.capacity = 0

    def random_point(self):
        '''
        Returns a random point within a geographical unit, used to place agents in county.
        '''
        # Extract bounds of county
        min_x, min_y, max_x, max_y = self.geometry.bounds
        # Draw random point within bounds
        while not self.geometry.contains(
            random_point := Point(
                random.uniform(min_x, max_x), random.uniform(min_y, max_y)
            )):
            continue
        return random_point

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

    def reset_data(self):
        '''
        Resets the data of the electoral district.
        '''
        self.num_people = 0
        self.red_cnt = 0
        self.blue_cnt = 0
        self.red_pct = 0
        self.blue_pct = 0
        self.color = 'Grey'

    def update_majority(self):
        '''
        Updates the color of the electoral district, used for the visualization.
        '''
        # Update district percentages
        if self.num_people != 0:
            self.red_pct = self.red_cnt / self.num_people
            self.blue_pct = self.blue_cnt / self.num_people
        else:
            self.red_pct = 0
            self.blue_pct = 0

        # Determine majority party
        if self.red_cnt > self.blue_cnt:
            self.color = 'Red'
        elif self.red_cnt < self.blue_cnt:
            self.color = 'Blue'
        else:
            self.color = 'Grey'
