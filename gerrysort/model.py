import random
import geopandas as gpd
import uuid

import mesa
import mesa_geo as mg

from .agents import PersonAgent, DistrictAgent, CountyAgent
from .space import ElectoralDistricts


class GeoSchellingPoints(mesa.Model):
    def __init__(self, similarity_threshold=0.5, gerrymandering=True, npop=1000, map_sample_size=10):
        super().__init__()

        # Set up the schedule and space
        self.schedule = mesa.time.RandomActivation(self)
        self.space = ElectoralDistricts()

        # Load the data
        self.ensemble = gpd.read_file("data/MN_test/MN_CONGDIST_ensemble.geojson").to_crs(self.space.crs)
        self.initial_plan = gpd.read_file("data/MN_test/MN_CONGDIST_initial.geojson").to_crs(self.space.crs)
        self.fitness_landscape = gpd.read_file("testing/data/MN_county_ruca_votes.geojson").to_crs(self.space.crs)
        
        # # NOTE: CRS CHECK
        # print(self.space.crs)
        # print(self.ensemble.crs)
        # print(self.initial_plan.crs)
        # print(self.fitness_landscape.crs)

        # Set parameters
        self.npop = npop
        PersonAgent.SIMILARITY_THRESHOLD = similarity_threshold
        self.gerrymandering = gerrymandering
        self.map_sample_size = map_sample_size

        # Set up the data collector
        self.datacollector = mesa.DataCollector(
            {"unhappy": "unhappy", 
             "happy": "happy",
             "red_districts": "red_districts", 
             "blue_districts": "blue_districts", 
             "tied_districts": "tied_districts",
             "efficiency_gap": "efficiency_gap",
             "control": "control"}
        )

        # Set op voting districts for simulating gerrymandering/electoral processes
        ac_d = mg.AgentCreator(DistrictAgent, model=self)
        self.districts = ac_d.from_GeoDataFrame(self.initial_plan, unique_id="district")
        self.n_districts = len(self.districts)
        self.space.add_districts(self.districts)

        # Set up counties for simulating population shifts
        ac_c = mg.AgentCreator(CountyAgent, model=self)
        self.counties = ac_c.from_GeoDataFrame(self.fitness_landscape, unique_id="COUNTY")
        self.n_counties = len(self.counties)
        self.space.add_counties(self.counties)

        # Update the county to district map
        self.space.update_county_to_district_map(self.counties, self.districts)

        # Add agents to the space per county
        for county in self.counties:
            pop_county = int(county.TOTPOP_SHR * self.npop)
            for _ in range(pop_county):
                person = PersonAgent(
                    unique_id=uuid.uuid4().int,
                    model=self,
                    crs=self.space.crs,
                    geometry=county.random_point(),
                    is_red=county.PRES16D_SHR < random.random(),
                    district_id=self.space.county_district_map[county.unique_id],
                    county_id=county.unique_id,
                )
                self.space.add_person_to_county(person, county_id=county.unique_id)
                self.schedule.add(person)
            # print(person.crs)
            self.schedule.add(county)
            # print(county.crs)

        # Add districts to the scheduler and update their color
        for district in self.districts:
            district.update_district_data()
            district.update_district_color()
            self.schedule.add(district)
            # print(district.crs)

        # Collect data
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
        return self.npop - self.unhappy
    
    @property
    def red_districts(self):
        num_red = 0
        for agent in self.space.agents:
            if isinstance(agent, DistrictAgent) and agent.red_pct > 0.5:
                num_red += 1
        return num_red
    
    @property
    def blue_districts(self):
        num_blue = 0
        for agent in self.space.agents:
            if isinstance(agent, DistrictAgent) and agent.red_pct < 0.5:
                num_blue += 1
        return num_blue
    
    @property
    def tied_districts(self):
        return self.n_districts - self.red_districts - self.blue_districts

    @property
    def control(self):
        if self.red_districts > self.blue_districts:
            return "Republican"
        elif self.red_districts < self.blue_districts:
            return "Democratic"
        else:
            return "Tie"
        
    @property
    def efficiency_gap(self):
        total_wasted_votes_red = 0
        total_wasted_votes_blue = 0

        for agent in self.space.agents:
            if isinstance(agent, DistrictAgent):
                red_wasted_votes, blue_wasted_votes = agent.calculate_wasted_votes()
                total_wasted_votes_red += red_wasted_votes
                total_wasted_votes_blue += blue_wasted_votes

        total_votes = total_wasted_votes_red + total_wasted_votes_blue

        try: efficiency_gap = abs(total_wasted_votes_red - total_wasted_votes_blue) / total_votes
        except ZeroDivisionError: efficiency_gap = 0

        return efficiency_gap
    
    def redistrict(self, plan_n):
        # Select the districts in the plan
        new_districts = self.ensemble[self.ensemble['plan'] == plan_n].to_crs(self.space.crs)

        # Get current districts
        curr_districts = [region for region in self.space.agents if isinstance(region, DistrictAgent)]

        # Update the boundaries of the districts
        for curr_district in curr_districts:
            new_district = new_districts[new_districts['district'] == curr_district.unique_id]
            if not new_district.empty:
                new_geometry = new_district['geometry'].iloc[0]
                curr_district.update_district_geometry(new_geometry)
                curr_district.update_district_data()
                curr_district.update_district_color()
    
    def gerrymander(self):
        # Sample size of plans
        sample_size = 10

        # Draw a sample of plans
        sample = random.sample(list(self.ensemble['plan'].unique()), sample_size)

        # Save the control before gerrymandering
        control_before = self.control
        # Save the number of districts favoring the party in control before gerrymandering
        if control_before == "Red":
            districts_before = self.red_districts
        elif control_before == "Blue":
            districts_before = self.blue_districts
        else:
            districts_before = 0

        # If state is tied, do a random redistricting
        if control_before == 'Tie':
            self.redistrict(random.choice(self.ensemble['plan'].unique()))
            print("Random redistricting plan")
            return
        
        # Result dictionary plan|red_districts|blue_districts|tied_districts|efficiency_gap
        results = {}
        # Else redistrict to favor the party in control
        for plan_n in sample:
            self.redistrict(plan_n)
            results[plan_n] = {
                "red_districts": self.red_districts,
                "blue_districts": self.blue_districts,
                "tied_districts": self.tied_districts,
                "efficiency_gap": self.efficiency_gap
            }
        # print(control_before)
        # print(results)
        # Find the plan that maximizes the number of districts favoring the party in control or efficiency gap
        if control_before == "Red":
            best_plan = max(results, key=lambda x: results[x]['red_districts'])
            # print("Red state, maximizing red districts")
            # print(f"From {districts_before} to {results[best_plan]['red_districts']}")
        elif control_before == "Blue":
            best_plan = max(results, key=lambda x: results[x]['blue_districts'])
            # print("Blue state, maximizing blue districts")
            # print(f"From {districts_before} to {results[best_plan]['blue_districts']}")
        else:
            best_plan = min(results, key=lambda x: results[x]['efficiency_gap'])
            # print("Tied state, minimizing efficiency gap")
            # print(f"From {self.efficiency_gap} to {results[best_plan]['efficiency_gap']}")

        # Redistrict to the best plan
        self.redistrict(best_plan)

    def step(self):
        # Step all types of agents
        self.schedule.step()

        # Only gerrymander when sorting has converged
        if not self.unhappy:
            if self.gerrymandering: 
                self.gerrymander()

        # Collect data
        self.datacollector.collect(self)