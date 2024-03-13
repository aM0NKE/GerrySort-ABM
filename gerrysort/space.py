import random
from typing import Dict

import mesa_geo as mg

from .agents import DistrictAgent, CountyAgent


class ElectoralDistricts(mg.GeoSpace):

    _id_district_map: Dict[str, DistrictAgent]
    _id_county_map: Dict[str, CountyAgent]
    county_district_map: Dict[str, str]

    def __init__(self):
        super().__init__(warn_crs_conversion=False)
        self._id_district_map = {}
        self._id_county_map = {}

    def add_districts(self, districts):
        # Add districts to the space
        super().add_agents(districts)

        # Add districts to the id map
        for agent in districts:
            if isinstance(agent, DistrictAgent):
                self._id_district_map[agent.unique_id] = agent

    def add_counties(self, counties):
        # super().add_agents(counties)

        # Add counties to the id map
        for agent in counties:
            if isinstance(agent, CountyAgent):
                self._id_county_map[agent.unique_id] = agent

    def update_county_to_district_map(self, counties, districts):
        # Clear the map
        self.county_district_map = {}

        # Find county to district mapping
        for county in counties:
            county_centroid = county.geometry.centroid
            for district in districts:
                district = district.to_crs(county.crs)
                if county_centroid.within(district.geometry):
                    self.county_district_map[county.unique_id] = district.unique_id
                    break  # Stop iteration once a match is found
    
    def add_person_to_county(self, person, county_id):
        person.county_id = county_id
        person.district_id = self.county_district_map[county_id]
        person.geometry = self._id_county_map[county_id].random_point()
        super().add_agents(person)

    def remove_person_from_county(self, person):
        person.county_id = None
        person.district_id = None
        person.geometry = None
        super().remove_agent(person)

    def get_random_district_id(self) -> str:
        return random.choice(list(self._id_district_map.keys()))

    def get_district_by_id(self, district_id) -> DistrictAgent:
        return self._id_district_map.get(district_id)
    
    def get_random_county_id(self) -> str:
        return random.choice(list(self._id_county_map.keys()))
    
    def get_county_by_id(self, county_id) -> CountyAgent:
        return self._id_county_map.get(county_id)
    