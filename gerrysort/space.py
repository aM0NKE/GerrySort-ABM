import mesa_geo as mg
from .agents.geo_unit import GeoAgent

import geopandas as gpd
import random
from typing import Dict

class ElectoralDistricts(mg.GeoSpace):
    id_precinct_map: Dict[str, GeoAgent]
    id_county_map: Dict[str, GeoAgent]
    id_congdist_map: Dict[str, GeoAgent]
    precinct_county_map: Dict[str, str]
    precinct_congdist_map: Dict[str, str]

    def __init__(self):
        super().__init__(crs=4326, warn_crs_conversion=True)
        self.id_congdist_map = {}
        self.id_county_map = {}
        self.id_precinct_map = {}
        self.precinct_county_map = {}
        self.precinct_congdist_map = {}

    def add_precincts(self, precincts):
        for precinct in precincts:
            if isinstance(precinct, GeoAgent):
                self.id_precinct_map[precinct.unique_id] = precinct

    def add_counties(self, counties):
        for county in counties:
            if isinstance(county, GeoAgent):
                self.id_county_map[county.unique_id] = county

    def add_districts(self, districts):
        # Add districts to the space
        super().add_agents(districts)
        # Add districts to the id map
        for district in districts:
            if isinstance(district, GeoAgent):
                self.id_congdist_map[district.unique_id] = district

    def create_precinct_to_county_map(self, precincts):
        for precinct in precincts:
            # Get county
            county = self.get_county_by_id(precinct.COUNTYFIPS)
            # Add precinct to county agent
            county.precincts.append(precinct.unique_id)
            # Add county to precinct-county map
            self.precinct_county_map[precinct.unique_id] = precinct.COUNTYFIPS

    def create_precinct_to_congdist_map(self, precincts):
        for precinct in precincts:
            # Get district
            district = self.get_district_by_id(precinct.CONGDIST)
            # Add precinct to district agent
            district.precincts.append(precinct.unique_id)
            # Add district to precinct-district map
            self.precinct_congdist_map[precinct.unique_id] = precinct.CONGDIST

    def add_person_to_precinct(self, person, new_precinct_id, new_position=None):
        # Update precinct attributes
        precinct = self.get_precinct_by_id(new_precinct_id)
        precinct.num_people += 1
        if person.color == 'Red':
            precinct.reps.append(person.unique_id)
        elif person.color == 'Blue':
            precinct.dems.append(person.unique_id)

        # Update county attributes
        county = self.get_county_by_id(self.precinct_county_map[new_precinct_id])
        county.num_people += 1
        if person.color == 'Red':
            county.rep_cnt += 1
        elif person.color == 'Blue':
            county.dem_cnt += 1

        # Update congdist attributes
        district = self.get_district_by_id(self.precinct_congdist_map[new_precinct_id])
        district.num_people += 1
        if person.color == 'Red':
            district.rep_cnt += 1
        elif person.color == 'Blue':
            district.dem_cnt += 1

        # Update person attributes
        person.precinct_id = new_precinct_id
        person.county_id = self.precinct_county_map[new_precinct_id]
        person.district_id = self.precinct_congdist_map[new_precinct_id]
        if new_position is not None: 
            person.geometry = new_position
        else:
            person.geometry = precinct.random_point()

        # Add agent to map
        super().add_agents(person)

    def remove_person_from_precinct(self, person):
        # Update precinct attributes
        precinct = self.get_precinct_by_id(person.precinct_id)
        precinct.num_people -= 1
        if person.color == 'Red':
            precinct.reps.remove(person.unique_id)
        elif person.color == 'Blue':
            precinct.dems.remove(person.unique_id)

        # Update county attributes
        county = self.get_county_by_id(person.county_id)
        county.num_people -= 1
        if person.color == 'Red':
            county.rep_cnt -= 1
        elif person.color == 'Blue':
            county.dem_cnt -= 1

        # Update congdist attributes
        district = self.get_district_by_id(person.district_id)
        district.num_people -= 1
        if person.color == 'Red':
            district.rep_cnt -= 1
        elif person.color == 'Blue':
            district.dem_cnt -= 1

        # Clear attributes
        person.precinct_id = None
        person.county_id = None
        person.district_id = None
        person.geometry = None

        # Remove agent to map
        super().remove_agent(person)

    # def remove_person_from_county(self, person):
    #     '''
    #     Removes person from county for visualization and clears it's attributes.

    #     person: Person agent instance
    #     '''
    #     # Update num_pop counter
    #     # print(f'Removing person {person.unique_id} from {person.county_id} ({self.county_district_map[person.county_id]}).')
    #     county = self.get_county_by_id(person.county_id)
    #     # print('REMOVING PERSON')
    #     # print('[BEFORE]', county.num_people, '/' , county.capacity)
    #     county.num_people -= 1
    #     # print('[AFTER]', county.num_people, '/' , county.capacity, '\n')
    #     # Clear attributes
    #     # person.county_id = None
    #     # person.district_id = None
    #     # person.geometry = None
    #     # Remove agent to map
    #     super().remove_agent(person)


    def get_random_precinct_id(self) -> str:
        return random.choice(list(self.id_precinct_map.keys()))

    def get_random_county_id(self) -> str:
        return random.choice(list(self.id_county_map.keys()))

    def get_random_district_id(self) -> str:
        return random.choice(list(self.id_congdist_map.keys()))
    

    def get_precinct_by_id(self, precinct_id) -> GeoAgent:
        return self.id_precinct_map.get(precinct_id)
    
    def get_county_by_id(self, county_id) -> GeoAgent:
        return self.id_county_map.get(county_id)
    
    def get_district_by_id(self, district_id) -> GeoAgent:
        return self.id_congdist_map.get(district_id)
