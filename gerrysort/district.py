from .person import PersonAgent

import mesa_geo as mg
from math import ceil
from shapely.geometry import Point, Polygon, MultiPolygon

class DistrictAgent(mg.GeoAgent):

    type: str # TODO: add three district types of electoal districts
    num_people: int
    red_cnt: int
    blue_cnt: int
    color: str
    red_pct: float

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
        self.color = 'Grey'

    @property
    def red_pct(self):
        '''
        Returns the percentage of red people in the electoral district.
        '''
        if self.red_cnt == 0:
            return 0
        elif self.blue_cnt == 0:
            return 1
        elif self.red_cnt == 0 and self.blue_cnt == 0: # NOTE: in case district is empty, assign as tied district.
            return 0.5
        else:
            return self.red_cnt / (self.red_cnt + self.blue_cnt)
        
    @property 
    def blue_pct(self):
        '''
        Returns the percentage of blue people in the electoral district.
        '''
        # if self.blue_cnt == 0:
        #     return 0
        # elif self.red_cnt == 0:
        #     return 1
        # elif self.red_cnt == 0 and self.blue_cnt == 0:
        #     return 0.5
        # else:
        #     return self.blue_cnt / (self.red_cnt + self.blue_cnt)
        return 1 - self.red_pct

    @property
    def majority(self):
        '''
        Returns the majority party of the electoral district.
        '''
        if self.red_cnt > self.blue_cnt:
            return 'Republican'
        elif self.red_cnt < self.blue_cnt:
            return 'Democratic'
        else:
            return 'Tied'

    def calculate_wasted_votes(self):
        '''
        Calculates the wasted votes for the Dem and Rep party.
        '''
        red_wasted_votes = 0
        blue_wasted_votes = 0
        
        if self.majority == 'Republican':
            red_wasted_votes = self.red_cnt - ceil((self.red_cnt + self.blue_cnt) / 2)
            blue_wasted_votes = self.blue_cnt
        elif self.majority == 'Democratic':
            red_wasted_votes = self.red_cnt
            blue_wasted_votes = self.blue_cnt - ceil((self.red_cnt + self.blue_cnt) / 2)
        else:
            red_wasted_votes = 0
            blue_wasted_votes = 0
        
        return red_wasted_votes, blue_wasted_votes
    
    def update_district_geometry(self, new_geometry):
        '''
        Updates the geometry of the electoral district.
        '''
        if isinstance(new_geometry, Polygon):
            new_geometry = MultiPolygon([new_geometry])

        self.geometry = new_geometry

    def update_district_data(self):
        '''
        Updates the data of the electoral district.
        '''
        # Reset counters
        self.num_people = 0
        self.red_cnt = 0
        self.blue_cnt = 0
        # Update district counts
        for person in self.model.population:
            if self.geometry.contains(person.geometry):
                self.num_people += 1
                if person.is_red:
                    self.red_cnt += 1
                else:
                    self.blue_cnt += 1
                # Update the district_id of the person (only if district is congressional)
                if self.type == 'congressional':
                    person.district_id = self.unique_id
    
    def update_district_color(self):
        '''
        Updates the color of the electoral district, used for the visualization.
        '''
        if self.majority == 'Republican':
            self.color = 'Red'
        elif self.majority == 'Democratic':
            self.color = 'Blue'
        else:
            self.color = 'Grey'

    def step(self):
        # TODO: check if this is scheduled correctly
        self.update_district_data()
        self.update_district_color()
