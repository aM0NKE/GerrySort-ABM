import random
from typing import Dict

import mesa_geo as mg

from .agents.district import DistrictAgent
from .agents.county import CountyAgent

class ElectoralDistricts(mg.GeoSpace):
    _id_district_map: Dict[str, DistrictAgent]
    _id_county_map: Dict[str, CountyAgent]
    county_district_map: Dict[str, str]

    def __init__(self):
        super().__init__(crs=4326, warn_crs_conversion=True)
        self._id_district_map = {}
        self._id_county_map = {}

    def add_districts(self, districts):
        '''
        Adds and saves electoral districts to visualization map.

        districts: list of electoral district instances to redistrict
        '''
        # Add districts to the space
        super().add_agents(districts)

        # Add districts to the id map
        for agent in districts:
            if isinstance(agent, DistrictAgent):
                self._id_district_map[agent.unique_id] = agent
        print(f"Added {len(districts)} districts to the space.")

    def add_counties(self, counties):
        '''
        Saves counties to county-id map.

        counties: list of county instances used to relocate
        '''
        # super().add_agents(counties)

        # Add counties to the id map
        for agent in counties:
            if isinstance(agent, CountyAgent):
                self._id_county_map[agent.unique_id] = agent

    def update_county_to_district_map(self, counties, districts):
        '''
        Clears the county-district map and rebuilds it after the redistricting process.

        counties: list of county instances used to relocate
        districts: list of electoral district instances to redistrict
        '''
        # Clear the map
        self.county_district_map = {}

        # Find county to district mapping
        for county in counties:
            county_centroid = county.geometry.centroid
            for district in districts:
                district = district.to_crs(county.crs)

                if county_centroid.within(district.geometry):

                # if geometries overlap for at least 50% of the area
                # if county.geometry.intersection(district.geometry).area >= 0.4 * county.geometry.area:
                    self.county_district_map[county.unique_id] = district.unique_id
                    break  # Stop iteration once a match is found

    def remove_person_from_county(self, person):
        '''
        Removes person from county for visualization and clears it's attributes.

        person: Person agent instance
        '''
        # print(f"Removing {person.unique_id} from {person.county_id} ({person.district_id}).")
        # Update num_pop counter
        # print(f'Person {person.unique_id} is leaving {person.county_id} ({self.county_district_map[person.county_id]}).')
        county = self.get_county_by_id(person.county_id)
        # print('REMOVING PERSON')
        # print('[BEFORE]', county.num_people, '/' , county.capacity)
        county.num_people -= 1
        # print('[AFTER]', county.num_people, '/' , county.capacity, '\n')
        # county.num_people -= 1
        # Clear attributes
        person.county_id = None
        person.district_id = None
        person.geometry = None
        # Remove agent to map
        super().remove_agent(person)
    
    def add_person_to_county(self, person, new_county_id, new_position=None):
        '''
        Adds person to county for visualization and updates attributes.

        person: Person agent instance
        new_county_id: new county id
        new_position: new coordinates of relocation destination
        '''
        # print(f"Adding {person.unique_id} to {new_county_id} ({self.county_district_map[new_county_id]}).")
        # Update num_pop counter
        county = self._id_county_map[new_county_id]
        # print('ADDING PERSON')
        # print('[BEFORE]', county.num_people, '/' , county.capacity)
        county.num_people += 1
        # print('[AFTER]', county.num_people, '/' , county.capacity, '\n')


        # Update attributes
        person.county_id = new_county_id
        person.district_id = self.county_district_map[new_county_id]
        if new_position is not None: 
            person.geometry = new_position
        else: 
            person.geometry = self._id_county_map[new_county_id].random_point()

        # Add agent to map
        super().add_agents(person)
        # person.update_utility()

    def get_random_district_id(self) -> str:
        return random.choice(list(self._id_district_map.keys()))
    
    def get_random_county_id(self) -> str:
        return random.choice(list(self._id_county_map.keys()))

    def get_district_by_id(self, district_id) -> DistrictAgent:
        return self._id_district_map.get(district_id)
    
    def get_county_by_id(self, county_id) -> CountyAgent:
        return self._id_county_map.get(county_id)
    