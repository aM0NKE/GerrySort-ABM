from gerrychain import (Partition, Graph, MarkovChain,
                        updaters, constraints, accept,
                        GeographicPartition)
from gerrychain.proposals import recom
from gerrychain.tree import bipartition_tree
from gerrychain.constraints import contiguous
from functools import partial

import numpy as np
import random
import geopandas as gpd
import uuid
from math import pi, ceil

import mesa
import mesa_geo as mg

from .person import PersonAgent
from .district import DistrictAgent
from .county import CountyAgent
from .space import ElectoralDistricts
from .redistricting_utils import redistrict, gerrymander


class GerrySort(mesa.Model):
    def __init__(self, tolarence=0.5, beta=0.0, gerrymandering=True, sorting=True, npop=1000, n_proposed_maps=10, n_moving_options=10, moving_cooldown=5, distance_decay=0.5):
        super().__init__()

        # Set up the schedule and space
        self.schedule = mesa.time.RandomActivation(self)
        self.space = ElectoralDistricts()

        # Load the data
        self.precincts = gpd.read_file("data/MN_test/MN_precincts.geojson")
        # self.ensemble = gpd.read_file("data/MN_test/MN_CONGDIST_ensemble.geojson").to_crs(self.space.crs)
        self.initial_plan = gpd.read_file("data/MN_test/MN_CONGDIST_initial.geojson").to_crs(self.space.crs)
        self.fitness_landscape = gpd.read_file("testing/data/MN_county_ruca_votes_housing_income.geojson").to_crs(self.space.crs)

        # Check CRS consistency
        self.check_crs_consistency()

        # Set parameters
        self.npop = npop
        self.ndems = 0
        self.nreps = 0
        self.gerrymandering = gerrymandering
        if gerrymandering: self.set_up_gerrychain('TOTPOP', 'CONGDIST', n_proposed_maps)
        if sorting:
            self.sorting = sorting
            self.tolarence = tolarence
            self.beta = beta
            self.n_moving_options = n_moving_options
            self.moving_cooldown = moving_cooldown
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
             "control": "control",
             "n_moves": "n_moves"}
        )

        # Create three agent types
        self.create_counties_districts('COUNTY', 'district')
        self.create_people()

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
    def n_moves(self):
        n_moves = 0
        for agent in self.space.agents:
            if isinstance(agent, PersonAgent) and agent.last_moved == 0:
                n_moves += 1
        return n_moves

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
        # NOTE: IndexError: list index out of range: dem_share_rep = 1 - rep_districts[median_rep].red_pct
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

    def check_crs_consistency(self):
        # Extract the CRS of each GeoDataFrame
        crs_initial_plan = self.initial_plan.crs
        crs_fitness_landscape = self.fitness_landscape.crs

        assert crs_fitness_landscape == crs_initial_plan, f"CRS mismatch: fitness_landscape ({crs_fitness_landscape}) != initial_plan ({crs_initial_plan})"

        print("All CRS are consistent.")
    
    def set_up_gerrychain(self, totpop_id, district_id, n_proposed_maps):

        self.graph = Graph.from_geodataframe(self.precincts)
        self.updaters = {
            "population": updaters.Tally(totpop_id, alias="population"),
            "cut_edges": updaters.cut_edges,
            "perimeter": updaters.perimeter,
            "area": updaters.Tally("area", alias="area"),
            "geometry": updaters.boundary_nodes,
        }
        self.initial_partition = GeographicPartition(
            self.graph,
            assignment=district_id,
            updaters=self.updaters
        )
        self.ideal_population = sum(self.initial_partition["population"].values()) / len(self.initial_partition)
        self.proposal = partial(
            recom,
            pop_col=totpop_id,
            pop_target=self.ideal_population,
            epsilon=0.01,
            node_repeats=2,
        )
        self.n_proposed_maps = n_proposed_maps
        self.recom_chain = MarkovChain(
            proposal=self.proposal,
            constraints=[contiguous],
            accept=accept.always_accept,
            initial_state=self.initial_partition,
            total_steps=self.n_proposed_maps,
        )

    def create_counties_districts(self, county_id, district_id):
        # Set op voting districts for simulating gerrymandering/electoral processes
        ac_d = mg.AgentCreator(DistrictAgent, model=self)
        self.districts = ac_d.from_GeoDataFrame(self.initial_plan, unique_id=district_id)
        self.n_districts = len(self.districts)
        self.space.add_districts(self.districts)

        # Set up counties for simulating population shifts
        ac_c = mg.AgentCreator(CountyAgent, model=self)
        self.counties = ac_c.from_GeoDataFrame(self.fitness_landscape, unique_id=county_id)
        self.n_counties = len(self.counties)
        self.space.add_counties(self.counties)

        # Update the county to district map
        self.space.update_county_to_district_map(self.counties, self.districts)

    def create_people(self):
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
                    is_red=county.PRES16R_SHR > random.random(),
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

    def step(self):
        # Step all types of agents
        self.schedule.step()

        # if not self.unhappy:     # Only gerrymander when sorting has converged
        if self.gerrymandering: 
            gerrymander(self)

        # Collect data
        self.datacollector.collect(self)
