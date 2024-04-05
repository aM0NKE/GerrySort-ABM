from gerrychain import (Partition, Graph, MarkovChain,
                        updaters, constraints, accept,
                        GeographicPartition)
from gerrychain.proposals import recom
from gerrychain.tree import bipartition_tree
from gerrychain.constraints import contiguous
from functools import partial

import random
import geopandas as gpd
import uuid
from math import pi, ceil

import mesa
import mesa_geo as mg

from .agents import PersonAgent, DistrictAgent, CountyAgent
from .space import ElectoralDistricts


class GerrySort(mesa.Model):
    def __init__(self, similarity_threshold=0.5, gerrymandering=True, max_recomb_steps=10, npop=1000, map_sample_size=10, n_moving_options=10, distance_decay=0.5):
        super().__init__()

        # Set up the schedule and space
        self.schedule = mesa.time.RandomActivation(self)
        self.space = ElectoralDistricts()

        # Load the data
        self.precincts = gpd.read_file("data/MN_test/MN_precincts.geojson")
        self.ensemble = gpd.read_file("data/MN_test/MN_STATELEG_ensemble.geojson").to_crs(self.space.crs)
        self.initial_plan = gpd.read_file("data/MN_test/MN_STATELEG_initial.geojson").to_crs(self.space.crs)
        self.fitness_landscape = gpd.read_file("testing/data/MN_county_ruca_votes_housing_income.geojson").to_crs(self.space.crs)
        
        # # NOTE: CRS CHECK
        # print(self.space.crs)
        # print(self.ensemble.crs)
        # print(self.initial_plan.crs)
        # print(self.fitness_landscape.crs)

        # Set up Gerrychain
        self.pop_col = "TOTPOP"
        self.dist_col = "MNSENDIST"
        self.graph = Graph.from_geodataframe(self.precincts)
        self.updaters = {
            "population": updaters.Tally(self.pop_col, alias="population"),
            "cut_edges": updaters.cut_edges,
            "perimeter": updaters.perimeter,
            "area": updaters.Tally("area", alias="area"),
            "geometry": updaters.boundary_nodes,
        }
        self.initial_partition = GeographicPartition(
            self.graph,
            assignment=self.dist_col,
            updaters=self.updaters
        )
        self.ideal_population = sum(self.initial_partition["population"].values()) / len(self.initial_partition)
        self.proposal = partial(
            recom,
            pop_col=self.pop_col,
            pop_target=self.ideal_population,
            epsilon=0.01,
            node_repeats=2,
        )
        self.max_recomb_steps = max_recomb_steps
        self.recom_chain = MarkovChain(
            proposal=self.proposal,
            constraints=[contiguous],
            accept=accept.always_accept,
            initial_state=self.initial_partition,
            total_steps=self.max_recomb_steps,
        )

        # Set parameters
        self.npop = npop
        self.ndems = 0
        self.nreps = 0
        PersonAgent.SIMILARITY_THRESHOLD = similarity_threshold
        self.gerrymandering = gerrymandering
        self.map_sample_size = map_sample_size
        self.n_moving_options = n_moving_options
        self.distance_decay = distance_decay

        # Set up the data collector
        self.datacollector = mesa.DataCollector(
            {"unhappy": "unhappy", 
             "happy": "happy",
             "red_districts": "red_districts", 
             "blue_districts": "blue_districts", 
             "tied_districts": "tied_districts",
             "efficiency_gap": "efficiency_gap",
             "mean_median": "mean_median",
             "declination": "declination",
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

        total_cap = 0
        # Add agents to the space per county
        for county in self.counties:
            pop_county = ceil(county.TOTPOP_SHR * self.npop)
            # Lower density > more space
            county.capacity = ceil(county.CAPACITY_SHR * self.npop)
            total_cap += county.capacity
            # print(f'County {county.unique_id} has {pop_county} people and {county.capacity} capacity')
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
                if person.is_red: self.nreps += 1
                else: self.ndems += 1
            # print(person.crs)
            self.schedule.add(county)
            # print(county.crs)

        # print(f'Total n pop: {self.npop} | Total capacity: {total_cap}')

        # Add districts to the scheduler and update their color
        for district in self.districts:
            district.update_district_data()
            district.update_district_color()
            self.schedule.add(district)
            # print(district.crs)

        # Keep track of previous control (for gerrymandering)
        self.prev_control = self.control 

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
            return "Tied"
        
    @property
    def efficiency_gap(self):
        # Calculate wasted votes
        total_wasted_votes_red = 0
        total_wasted_votes_blue = 0
        for agent in self.space.agents:
            if isinstance(agent, DistrictAgent):
                red_wasted_votes, blue_wasted_votes = agent.calculate_wasted_votes()
                total_wasted_votes_red += red_wasted_votes
                total_wasted_votes_blue += blue_wasted_votes

        # Return efficiency gap (npop = total number of votes)
        efficiency_gap = abs(total_wasted_votes_blue - total_wasted_votes_red) / self.npop
        return efficiency_gap
    
    @property
    def mean_median(self):
        # Get dem vote shares (1 - red_pct) for each district
        dem_pct = []
        for agent in self.space.agents:
            if isinstance(agent, DistrictAgent):
                dem_pct.append(1 - agent.red_pct)

        # Sort dem vote shares
        dem_pct.sort()

        # Calculate mean and median
        median = dem_pct[len(dem_pct) // 2]
        mean = sum(dem_pct) / len(dem_pct)

        # Return mean-median difference
        return mean - median
    
    @property
    def declination(self):
        # Get districts for Democrats and Republicans
        rep_districts = [district for district in self.space.agents if isinstance(district, DistrictAgent) and district.red_pct > 0.5]
        dem_districts = [district for district in self.space.agents if isinstance(district, DistrictAgent) and district.red_pct < 0.5]
        
        # Sort districts by dem vote share (1 - red_pct)
        rep_districts.sort(key=lambda x: 1 - x.red_pct)
        dem_districts.sort(key=lambda x: 1 - x.red_pct)
        
        # Find median dem vote shares (1 - red_pct) and median district number for both districts 
        median_rep = len(rep_districts) // 2
        median_dem = len(dem_districts) // 2
        dem_share_rep = 1 - rep_districts[median_rep].red_pct
        dem_share_dem = 1 - dem_districts[median_dem].red_pct

        # Find 50-50 point
        fifty_fifty_point = len(rep_districts) + 0.5

        # Calculate slopes from median districts to fifty-fifty point
        slope_rep = (0.5 - dem_share_rep) / (fifty_fifty_point - median_rep)
        slope_dem = (0.5 - dem_share_dem) / (fifty_fifty_point - median_dem)

        # Return declination
        declination = (2 * (slope_dem - slope_rep)) / pi
        return declination
    
    def redistrict(self, new_districts):
        # Select the districts in the plan
        # new_districts = self.ensemble[self.ensemble['plan'] == plan_n].to_crs(self.space.crs)

        # Get current districts
        curr_districts = [district for district in self.space.agents if isinstance(district, DistrictAgent)]

        # Update the boundaries of the districts
        for curr_district in curr_districts:
            # print(curr_district.unique_id, type(curr_district.unique_id))
            new_district = new_districts[new_districts['district'] == curr_district.unique_id]
            if not new_district.empty:
                new_geometry = new_district['geometry'].iloc[0]
                curr_district.update_district_geometry(new_geometry)
                curr_district.update_district_data()
                curr_district.update_district_color()

    def gerrymander(self):
        # Generate/save ensemble of plans
        for i, partition in enumerate(self.recom_chain):
            self.precincts['plan_{}'.format(i)] = [partition.assignment[n] for n in self.graph.nodes]

        # Process the plans
        unprocessed_plans = self.precincts[[f'plan_{i}' for i in range(self.max_recomb_steps)] + ['geometry']]
        processed_plans = unprocessed_plans.melt(id_vars='geometry', var_name='plan', value_vars=[f'plan_{i}' for i in range(self.max_recomb_steps)], value_name='district')
        processed_plans['plan'] = processed_plans['plan'].str.replace('plan_', '')
        processed_plans = processed_plans.dissolve(by=['plan', 'district']).reset_index()
        processed_plans['district'] = processed_plans['district'].astype(str)

        # print(processed_plans.head())
        # Print district values type
        # print(processed_plans.dtypes)

        # Evaluate the plans
        results = {}
        for i in range(self.max_recomb_steps):
            new_districts = processed_plans[processed_plans['plan'] == str(i)].to_crs(self.space.crs)
            # print("New districts", new_districts)
            self.redistrict(new_districts)
            results[f'{i}'] = {
                "red_districts": self.red_districts,
                "blue_districts": self.blue_districts,
                "tied_districts": self.tied_districts,
                "efficiency_gap": self.efficiency_gap,
                "mean_median": self.mean_median,
                "declination": self.declination
            }
        # print("TESTING...", results)
        # Find the plan that maximizes the number of districts favoring the party in control
        if self.prev_control == "Republican":
            best_plan = max(results, key=lambda x: results[x]['red_districts'])
        elif self.prev_control == "Democratic":
            best_plan = max(results, key=lambda x: results[x]['blue_districts'])
        else:
            best_plan = min(results, key=lambda x: results[x]['mean_median'])
        # print("Best plan", best_plan, results[best_plan])
        # Redistrict to the best plan
        best_plan_districts = processed_plans[processed_plans['plan'] == best_plan].to_crs(self.space.crs)
        # print("Best plan districts", best_plan_districts)
        # self.redistrict(best_plan_districts)

        # Keep track controlling party before population shift
        self.prev_control = self.control
    
    # def gerrymander(self):
    #     # Draw a sample of plans
    #     sample = random.sample(list(self.ensemble['plan'].unique()), self.map_sample_size)
        
    #     # Evaluate the plans
    #     results = {}
    #     for plan_n in sample:
    #         self.redistrict(plan_n)
    #         results[plan_n] = {
    #             "red_districts": self.red_districts,
    #             "blue_districts": self.blue_districts,
    #             "tied_districts": self.tied_districts,
    #             "efficiency_gap": self.efficiency_gap,
    #             "mean_median": self.mean_median,
    #             "declination": self.declination
    #         }

    #     # Find the plan that maximizes the number of districts favoring the party in control
    #     if self.prev_control == "Republican":
    #         best_plan = max(results, key=lambda x: results[x]['red_districts'])
    #         # print("Red state, maximizing red districts")
    #         # print(f"From {districts_before} to {results[best_plan]['red_districts']}")
    #     elif self.prev_control == "Democratic":
    #         best_plan = max(results, key=lambda x: results[x]['blue_districts'])
    #         # print("Blue state, maximizing blue districts")
    #         # print(f"From {districts_before} to {results[best_plan]['blue_districts']}")
    #     # or minimizing efficiency gap (in case of tie)
    #     else:
    #         best_plan = min(results, key=lambda x: results[x]['efficiency_gap'])
    #         # print("Tied state, minimizing efficiency gap")
    #         # print(f"From {self.efficiency_gap} to {results[best_plan]['efficiency_gap']}")

    #     # Redistrict to the best plan
    #     self.redistrict(best_plan)

    #     # Keep track controlling party before population shift
    #     self.prev_control = self.control

    def step(self):
        # Step all types of agents
        self.schedule.step()

        # Only gerrymander when sorting has converged
        # if not self.unhappy:
        if self.gerrymandering: 
            self.gerrymander()

        # Collect data
        self.datacollector.collect(self)