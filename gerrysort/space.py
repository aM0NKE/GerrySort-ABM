import mesa_geo as mg
from .agents.geo_unit import GeoAgent

import geopandas as gpd
import random
from typing import Dict

class ElectoralDistricts(mg.GeoSpace):
    _id_district_map: Dict[str, GeoAgent]
    _id_county_map: Dict[str, GeoAgent]
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
        for district in districts:
            if isinstance(district, GeoAgent):
                self._id_district_map[district.unique_id] = district
        # print(f"Added {len(districts)} districts to the space.")

    def add_counties(self, counties):
        '''
        Saves counties to county-id map.

        counties: list of county instances used to relocate
        '''
        # super().add_agents(counties)

        # Add counties to the id map
        for county in counties:
            if isinstance(county, GeoAgent):
                self._id_county_map[county.unique_id] = county

    def update_county_to_district_map(self, counties, districts):
        '''
        Clears the county-district map and rebuilds it after the redistricting process.

        counties: list of county instances used to relocate
        districts: list of electoral district instances to redistrict
        '''
        # Convert county and district lists to GeoDataFrames
        counties_gdf = gpd.GeoDataFrame([
            {'unique_id': county.unique_id, 'geometry': county.geometry} 
            for county in counties if county.geometry is not None
        ], crs=districts[0].crs)


        districts_gdf = gpd.GeoDataFrame([
            {'unique_id': district.unique_id, 'geometry': district.geometry} 
            for district in districts if district.geometry is not None
        ], crs=districts[0].crs)

        # Choose a projected CRS suitable for area calculations (e.g., EPSG:5070 for the U.S.)
        projected_crs = "EPSG:5070"
        counties_gdf = counties_gdf.to_crs(projected_crs)
        districts_gdf = districts_gdf.to_crs(projected_crs)
            
        # Perform spatial join with 'intersection' to capture overlap areas
        overlay = gpd.overlay(counties_gdf, districts_gdf, how='intersection', keep_geom_type=False)

        # print('overlay: ', overlay)
        # Add area column to determine largest overlap
        overlay['area'] = overlay.geometry.area
        # print('overlay (area): ', overlay['area'])
        # Find the district with maximum overlap for each county
        max_overlap = overlay.loc[overlay.groupby('unique_id_1')['area'].idxmax()]

        # print('max_overlap: \n', max_overlap)
        # Create the county-district map from the result
        self.county_district_map = dict(zip(max_overlap['unique_id_1'], max_overlap['unique_id_2']))

        # Update each county's district assignment based on the map
        for county in counties:
            if county.unique_id in self.county_district_map:
                county.district_id = self.county_district_map[county.unique_id]

    def remove_person_from_county(self, person):
        '''
        Removes person from county for visualization and clears it's attributes.

        person: Person agent instance
        '''
        # Update num_pop counter
        # print(f'Removing person {person.unique_id} from {person.county_id} ({self.county_district_map[person.county_id]}).')
        county = self.get_county_by_id(person.county_id)
        # print('REMOVING PERSON')
        # print('[BEFORE]', county.num_people, '/' , county.capacity)
        county.num_people -= 1
        # print('[AFTER]', county.num_people, '/' , county.capacity, '\n')
        # Clear attributes
        # person.county_id = None
        # person.district_id = None
        # person.geometry = None
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
        # person.county_id = new_county_id
        # person.district_id = self.county_district_map[new_county_id]
        if new_position is not None: 
            person.geometry = new_position
        else: 
            person.geometry = self._id_county_map[new_county_id].random_point()

        # Add agent to map
        super().add_agents(person)

    def get_random_district_id(self) -> str:
        return random.choice(list(self._id_district_map.keys()))
    
    def get_random_county_id(self) -> str:
        return random.choice(list(self._id_county_map.keys()))

    def get_district_by_id(self, district_id) -> GeoAgent:
        return self._id_district_map.get(district_id)
    
    def get_county_by_id(self, county_id) -> GeoAgent:
        return self._id_county_map.get(county_id)
    