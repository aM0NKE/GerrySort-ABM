import random
import geopandas as gpd
import uuid

import mesa
import mesa_geo as mg

from .agents import PersonAgent, RegionAgent
from .space import Nuts2Eu


class GeoSchellingPoints(mesa.Model):
    def __init__(self, red_percentage=0.5, similarity_threshold=0.5, redistrict=True):
        super().__init__()

        self.initial_plan = gpd.read_file("data/MN_test/MN_CONGDIST_initial.geojson")
        self.ensemble = gpd.read_file("data/MN_test/MN_CONGDIST_ensemble.geojson")
        self.red_percentage = red_percentage
        PersonAgent.SIMILARITY_THRESHOLD = similarity_threshold
        self.redistrict = redistrict

        self.schedule = mesa.time.RandomActivation(self)
        self.space = Nuts2Eu()

        self.datacollector = mesa.DataCollector(
            {"unhappy": "unhappy", "happy": "happy",
             "red_districts": "red_districts", "blue_districts": "blue_districts",
             "efficiency_gap": "efficiency_gap"}
        )

        # Set up the grid with patches for every NUTS region
        ac = mg.AgentCreator(RegionAgent, model=self)
        regions = ac.from_GeoDataFrame(self.initial_plan, unique_id="district")
        self.space.add_regions(regions)

        for region in regions:
            region.init_num_people
            for _ in range(region.init_num_people):
                person = PersonAgent(
                    unique_id=uuid.uuid4().int,
                    model=self,
                    crs=self.space.crs,
                    geometry=region.random_point(),
                    is_red=region.PRES16D / (region.PRES16D + region.PRES16R) < random.random(),
                    region_id=region.unique_id,
                )
                self.space.add_person_to_region(person, region_id=region.unique_id)
                self.schedule.add(person)
            region.update_color()
            self.schedule.add(region)
        self.datacollector.collect(self)

    @property
    def unhappy(self):
        num_unhappy = 0
        for agent in self.space.agents:
            if isinstance(agent, PersonAgent) and agent.is_unhappy:
                num_unhappy += 1
        return num_unhappy

    @property
    def happy(self):
        return self.space.num_people - self.unhappy
    
    @property
    def red_districts(self):
        num_red = 0
        for region in self.space.agents:
            if isinstance(region, RegionAgent) and region.red_pct > 0.5:
                num_red += 1
        return num_red
    
    @property
    def blue_districts(self):
        num_blue = 0
        for region in self.space.agents:
            if isinstance(region, RegionAgent) and region.red_pct < 0.5:
                num_blue += 1
        return num_blue
    
    @property
    def efficiency_gap(self):
        total_wasted_votes_red = 0
        total_wasted_votes_blue = 0

        for region in self.space.agents:
            if isinstance(region, RegionAgent):
                red_wasted_votes, blue_wasted_votes = region.calculate_wasted_votes()
                total_wasted_votes_red += red_wasted_votes
                total_wasted_votes_blue += blue_wasted_votes

        total_votes = total_wasted_votes_red + total_wasted_votes_blue

        efficiency_gap = abs(total_wasted_votes_red - total_wasted_votes_blue) / total_votes

        return efficiency_gap
    
    def gerrymander(self):
        ensemble = self.ensemble
        # Select a random plan
        plan_n = random.choice(ensemble['plan'].unique())
        # Select the districts in the plan
        new_districts = ensemble[ensemble['plan'] == plan_n].to_crs(self.space.crs)
        # Get region agents
        curr_districts = [region for region in self.space.agents if isinstance(region, RegionAgent)]
        # Update the boundaries of the districts
        for curr_district in curr_districts:
            new_district = new_districts[new_districts['district'] == curr_district.unique_id]
            if not new_district.empty:
                new_geometry = new_district['geometry'].iloc[0]
                curr_district.update_geometry(new_geometry)
                curr_district.update_red_blue_counts()
                curr_district.update_color()

    def step(self):
        self.schedule.step()
        self.datacollector.collect(self)

        # Only gerrymander when sorting has converged
        if not self.unhappy:
            if self.redistrict: 
                self.gerrymander()