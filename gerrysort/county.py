from .person import PersonAgent

import mesa_geo as mg
import random
from shapely.geometry import Point, Polygon, MultiPolygon

class CountyAgent(mg.GeoAgent):
    capacity: int
    num_people: int
    red_cnt: int
    blue_cnt: int
    color: str
    red_pct: float
    district_id: str

    def __init__(self, unique_id, model, geometry, crs):
        '''
        Initialize county agent.

        unique_id: Unique identifier of the county
        model: Model containing the county
        geometry: Geometry of the county
        crs: Coordinate Reference System of the county

        Attribute:
            district_id: District identifier of the county
            capacity: Maximum capacity of the county
            num_people: Number of people in the county
            red_cnt: Number of republican agents in the county
            blue_cnt: Number of democratic agents in the county
        '''
        super().__init__(unique_id, model, geometry, crs)

        self.district_id = None
        self.capacity = 0
        self.num_people = 0
        self.red_cnt = 0
        self.blue_cnt = 0
        self.red_pct = 0

    def random_point(self):
        '''
        Returns a random point within the county, used to place agents in county.
        '''
        # Extract bounds of county
        min_x, min_y, max_x, max_y = self.geometry.bounds
        # Draw random point within bounds
        while not self.geometry.contains(
            random_point := Point(
                random.uniform(min_x, max_x), random.uniform(min_y, max_y)
            )
        ):
            continue
        return random_point
    
    def update_district_data(self): # TODO: Maybe can be incorporated to add/remove agents to/from county.
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
            # # Update the county_id of the person
            # person.county_id = self.unique_id

        try: self.red_pct = self.red_cnt / self.num_people
        except ZeroDivisionError: self.red_pct = 0.5