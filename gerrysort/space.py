from .agents.geo_unit import GeoAgent

import mesa_geo as mg
import random
from typing import Dict

class ElectoralDistricts(mg.GeoSpace):
    id_person_map: Dict[str, GeoAgent]
    id_precinct_map: Dict[str, GeoAgent]
    id_county_map: Dict[str, GeoAgent]
    id_congdist_map: Dict[str, GeoAgent]
    precinct_county_map: Dict[str, str]
    precinct_congdist_map: Dict[str, str]

    def __init__(self):
        super().__init__(crs=5070, warn_crs_conversion=True)
        self.id_person_map = {}
        self.id_precinct_map = {}
        self.id_county_map = {}
        self.id_congdist_map = {}
        self.precinct_county_map = {}
        self.precinct_congdist_map = {}
        self.vis_level = None

    def add_agents(self, persons):
        for person in persons:
            self.id_person_map[person.unique_id] = person

    def add_precincts(self, precincts):
        if self.vis_level == 'PRECINCT': super().add_agents(precincts)
        for precinct in precincts:
            self.id_precinct_map[precinct.unique_id] = precinct

    def add_counties(self, counties):
        if self.vis_level == 'COUNTY': super().add_agents(counties)
        for county in counties:
            self.id_county_map[county.unique_id] = county

    def add_congdists(self, congdists):
        if self.vis_level == 'CONGDIST': super().add_agents(congdists)
        for congdist in congdists:
            self.id_congdist_map[congdist.unique_id] = congdist

    def create_precinct_to_county_map(self, precincts):
        for precinct in precincts:
            # Get county
            county = self.get_county_by_id(precinct.COUNTY_NAME)
            # Add precinct to county agent
            county.precincts.append(precinct.unique_id)
            # Add county to precinct-county map
            self.precinct_county_map[precinct.unique_id] = precinct.COUNTY_NAME

    def create_precinct_to_congdist_map(self, precincts):
        for precinct in precincts:
            congdist = self.get_congdist_by_id(precinct.CONGDIST)
            congdist.precincts.append(precinct.unique_id)
            self.precinct_congdist_map[precinct.unique_id] = precinct.CONGDIST

    def add_person_to_space(self, person, new_precinct_id, new_position=None):
        # Update precinct attributes
        precinct = self.get_precinct_by_id(new_precinct_id)
        precinct.num_people += 1
        if person.color == 'Red':
            precinct.reps.append(person.unique_id)
            precinct.rep_cnt += 1
        elif person.color == 'Blue':
            precinct.dems.append(person.unique_id)
            precinct.dem_cnt += 1
        # Update county attributes
        new_county_id = self.precinct_county_map[new_precinct_id]
        county = self.get_county_by_id(new_county_id)
        county.num_people += 1
        if person.color == 'Red':
            county.rep_cnt += 1
        elif person.color == 'Blue':
            county.dem_cnt += 1
        # Update electoral district attributes
        new_congdist_id = self.precinct_congdist_map[new_precinct_id]
        congdist = self.get_congdist_by_id(new_congdist_id)
        congdist.num_people += 1
        if person.color == 'Red':
            congdist.rep_cnt += 1
        elif person.color == 'Blue':
            congdist.dem_cnt += 1
        # Update person attributes
        person.precinct_id = new_precinct_id
        person.county_id = new_county_id
        person.congdist_id = new_congdist_id
        if new_position is not None: 
            person.geometry = new_position
        else:
            person.geometry = precinct.random_point()
        # Add agent to map
        super().add_agents(person)

    def remove_person_from_space(self, person):
        # Update precinct attributes
        precinct = self.get_precinct_by_id(person.precinct_id)
        precinct.num_people -= 1
        if person.color == 'Red':
            precinct.reps.remove(person.unique_id)
            precinct.rep_cnt -= 1
        elif person.color == 'Blue':
            precinct.dems.remove(person.unique_id)
            precinct.dem_cnt -= 1
        # Update county attributes
        county = self.get_county_by_id(person.county_id)
        county.num_people -= 1
        if person.color == 'Red':
            county.rep_cnt -= 1
        elif person.color == 'Blue':
            county.dem_cnt -= 1
        # Update electoral district attributes
        congdist = self.get_congdist_by_id(person.congdist_id)
        congdist.num_people -= 1
        if person.color == 'Red':
            congdist.rep_cnt -= 1
        elif person.color == 'Blue':
            congdist.dem_cnt -= 1
        # Clear attributes
        person.precinct_id = None
        person.county_id = None
        person.district_id = None
        person.geometry = None
        # Remove agent to map
        super().remove_agent(person)

    def get_random_person_id(self) -> str:
        return random.choice(list(self.id_person_map.keys()))

    def get_random_precinct_id(self) -> str:
        return random.choice(list(self.id_precinct_map.keys()))

    def get_random_county_id(self) -> str:
        return random.choice(list(self.id_county_map.keys()))

    def get_random_district_id(self) -> str:
        return random.choice(list(self.id_congdist_map.keys()))
    
    def get_person_by_id(self, person_id) -> GeoAgent:
        return self.id_person_map.get(person_id)

    def get_precinct_by_id(self, precinct_id) -> GeoAgent:
        return self.id_precinct_map.get(precinct_id)
    
    def get_county_by_id(self, county_id) -> GeoAgent:
        return self.id_county_map.get(county_id)
    
    def get_congdist_by_id(self, district_id) -> GeoAgent:
        return self.id_congdist_map.get(district_id)
