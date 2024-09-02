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
from .redistricting_utils import gerrymander


class GerrySort(mesa.Model):
    def __init__(self, console=False, tolarence=0.5, beta=0.0, capacity_mul=1.0, gerrymandering=True, sorting=True, npop=1000, n_proposed_maps=10, n_moving_options=10, moving_cooldown=5, distance_decay=0.5):
        '''
        Initialize the model with the given parameters.

        Parameters:
            tolarence (float): threshold for agent unhappiness
            beta (float): temperature for the Boltzmann distribution
            capacity_mul (float): multiplier for the capacity of each county
            gerrymandering (bool): whether to simulate gerrymandering
            sorting (bool): whether to simulate sorting
            npop (int): number of agents in the model
            n_proposed_maps (int): size of the potential map pool for gerrymandering
            n_moving_options (int): number of moving options for sorting
            moving_cooldown (int): number of steps between sorting moves
        '''
        # super().__init__() # TODO: Use this to set model parameters -> seems like it only works for certain attr (crs, geometry, model, etc.)


        # Debug (set this to true to print details in console)
        self.console = console
        if self.console:
            print('------------------------------------')
            print('Initializing model...')

        # Set up the schedule and space
        self.schedule = mesa.time.BaseScheduler(self) # TODO: Look into other schedulers
        self.space = ElectoralDistricts()

        # Load GeoData files
        self.precincts = gpd.read_file('data/MN/MN_precincts.geojson') # Needed to generate new plans (TODO: check if this works with: .to_crs(self.space.crs))
        self.initial_plan = gpd.read_file('data/MN/MN_CONGDIST_initial.geojson').to_crs(self.space.crs)
        # TODO: Add state house and senate maps to conduct elections
        self.state_leg_map = gpd.read_file('data/MN/MN_MNLEGDIST_initial.geojson').to_crs(self.space.crs)
        self.state_sen_map = gpd.read_file('data/MN/MN_MNSENDIST_initial.geojson').to_crs(self.space.crs)
        self.fitness_landscape = gpd.read_file('data/MN/MN_county_ruca_votes_housing_income.geojson').to_crs(self.space.crs)
        self.check_crs_consistency() # Check CRS consistency

        # Set parameters to model attributes
        self.npop = npop
        self.tolarence = tolarence
        self.capacity_mul = capacity_mul
        self.gerrymandering = gerrymandering
        self.sorting = sorting
        if gerrymandering: 
            self.set_up_gerrychain('TOTPOP', 'CONGDIST', n_proposed_maps)
        # if sorting:
        self.beta = beta
        self.n_moving_options = n_moving_options
        self.moving_cooldown = moving_cooldown
            # self.distance_decay = distance_decay # TODO: check if still included in model

        # Set up the data collector
        self.datacollector = mesa.DataCollector(
            {'unhappy': 'unhappy', 
            'happy': 'happy',
            'red_congressional_seats': 'red_congressional_seats',
            'blue_congressional_seats': 'blue_congressional_seats',
            'tied_congressional_seats': 'tied_congressional_seats',
            'red_state_house_seats': 'red_state_house_seats',
            'blue_state_house_seats': 'blue_state_house_seats',
            'tied_state_house_seats': 'tied_state_house_seats',
            'red_state_senate_seats': 'red_state_senate_seats',
            'blue_state_senate_seats': 'blue_state_senate_seats',
            'tied_state_senate_seats': 'tied_state_senate_seats',
            'efficiency_gap': 'efficiency_gap',
            'mean_median': 'mean_median',
            'declination': 'declination',
            'projected_winner': 'projected_winner',
            'control': 'control',
            'n_moves': 'n_moves'}
        )

        # Create three agent types
        # TODO: Add state (senate/house) electoral districts to simulate elections
        self.create_counties_districts('COUNTY', 'district')
        self.create_population()

        # Update census data
        self.update_census_data()

        # Update utility of all agents
        self.update_utilities()

        # Ininitialize party controlling the state based on initial plan
        self.control = self.projected_winner 

        # Collect data
        self.datacollector.collect(self)

        if self.console: print('Model initialized!')

    # Define model properties (collected at each step)
    @property
    def unhappy(self):
        '''
        Return the number of unhappy agents in the model.
        '''
        num_unhappy = 0
        for agent in self.population:
            if agent.is_unhappy:
                num_unhappy += 1
        return num_unhappy

    @property
    def happy(self):
        '''
        Return the number of happy agents in the model.
        '''
        num_happy = 0
        for agent in self.population:
            if not agent.is_unhappy:
                num_happy += 1
        return num_happy
    
    @property 
    def n_moves(self):
        '''
        Return the number of agents that have moved in the current step.
        '''
        n_moves = 0
        for agent in self.population:
            if agent.last_moved == 0:
                n_moves += 1
        return n_moves

    @property
    def red_congressional_seats(self):
        '''
        Return the number of US House electoral districts that favor the Republican party.
        '''
        num_red = 0
        for agent in self.USHouseDistricts:
            if agent.red_pct > 0.5:
                num_red += 1
        return num_red
    
    @property
    def blue_congressional_seats(self):
        '''
        Return the number of US House electoral districts that favor the Democratic party.
        '''
        num_blue = 0
        for agent in self.USHouseDistricts:
            if agent.red_pct < 0.5:
                num_blue += 1
        return num_blue
    
    @property
    def tied_congressional_seats(self):
        '''
        Return the number of US House electoral districts that are tied.
        '''
        return self.num_USHouseDistricts - self.red_congressional_seats - self.blue_congressional_seats
    
    @property
    def red_state_house_seats(self):
        '''
        Return the number of state house seats that favor the Republican party.
        '''
        num_red = 0
        for agent in self.StateHouseDistricts:
            if agent.red_pct > 0.5:
                num_red += 1
        return num_red
    
    @property
    def blue_state_house_seats(self):
        '''
        Return the number of state house seats that favor the Democratic party.
        '''
        num_blue = 0
        for agent in self.StateHouseDistricts:
            if agent.red_pct < 0.5:
                num_blue += 1
        return num_blue
    
    @property
    def tied_state_house_seats(self):
        '''
        Return the number of state house seats that are tied.
        '''
        return self.num_StateHouseDistricts - self.red_state_house_seats - self.blue_state_house_seats
    
    @property
    def red_state_senate_seats(self):
        '''
        Return the number of state senate seats that favor the Republican party.
        '''
        num_red = 0
        for agent in self.StateSenateDistricts:
            if agent.red_pct > 0.5:
                num_red += 1
        return num_red
    
    @property
    def blue_state_senate_seats(self):
        '''
        Return the number of state senate seats that favor the Democratic party.
        '''
        num_blue = 0
        for agent in self.StateSenateDistricts:
            if agent.red_pct < 0.5:
                num_blue += 1
        return num_blue
    
    @property
    def tied_state_senate_seats(self):
        '''
        Return the number of state senate seats that are tied.
        '''
        return self.num_StateSenateDistricts - self.red_state_senate_seats - self.blue_state_senate_seats

    @property
    def projected_winner(self):
        '''
        Returns the party that has both a majority in state house and senate.
        (Returns 'Tied' if no party has a majority in both chambers)
        '''
        if self.red_state_house_seats > self.blue_state_house_seats:
            if self.red_state_senate_seats > self.blue_state_senate_seats:
                return 'Republican'
        elif self.red_state_house_seats < self.blue_state_house_seats:
            if self.red_state_senate_seats < self.blue_state_senate_seats:
                return 'Democratic'
        return 'Tied'
    
    @property
    def projected_margin(self):
        '''
        Returns the margin of the projected winner in the state.
        '''
        if self.projected_winner == 'Republican':
            return (self.red_state_house_seats - self.blue_state_house_seats) + (self.red_state_senate_seats - self.blue_state_senate_seats)
        elif self.projected_winner == 'Democratic':
            return (self.blue_state_house_seats - self.red_state_house_seats) + (self.blue_state_senate_seats - self.red_state_senate_seats)
        return 0

    # TODO: Reevaluate the gerrymandering metrics.    
    # Three common gerrymandering quantifications: efficiency gap, mean-median difference, and declination
    @property
    def efficiency_gap(self):
        '''
        Return the efficiency gap of the plan and population distribution at the current step.
        '''
        # Sum wasted votes for every district for each party
        total_wasted_votes_red = 0
        total_wasted_votes_blue = 0
        for agent in self.USHouseDistricts:
            red_wasted_votes, blue_wasted_votes = agent.calculate_wasted_votes()
            total_wasted_votes_red += red_wasted_votes
            total_wasted_votes_blue += blue_wasted_votes

        # Calculate efficiency gap
        efficiency_gap = (total_wasted_votes_blue - total_wasted_votes_red) / self.npop
        return efficiency_gap
    
    @property
    def mean_median(self):
        '''
        Return the mean-median difference of the plan and population distribution at the current step.
        '''
        # Get dem vote shares (1 - red_pct) for each district
        dem_pct = []
        for agent in self.USHouseDistricts:
            dem_pct.append(1 - agent.red_pct)

        # Sort dem vote shares over all districts
        dem_pct.sort()

        # Calculate mean and median
        median = dem_pct[len(dem_pct) // 2] # TODO: find way to take average of two middle values if even number of districts
        mean = sum(dem_pct) / len(dem_pct)

        # Return mean-median difference
        return mean - median
    
    @property
    def declination(self):
        '''
        Return the declination of the plan and population distribution at the current step.
        '''
        # Get democratic vote share for each republican and democrat districts
        rep_districts_dem_pct = [1 - district.red_pct for district in self.USHouseDistricts if district.red_pct > 0.5]
        dem_districts_dem_pct = [1 - district.red_pct for district in self.USHouseDistricts if district.red_pct < 0.5]
        
        # Sort districts by dem vote share (1 - red_pct)
        rep_districts_dem_pct.sort()
        dem_districts_dem_pct.sort()
        
        # Find median dem vote shares (1 - red_pct) and median district number for both districts 
        median_rep = rep_districts_dem_pct[len(rep_districts_dem_pct) // 2] # TODO: find way to take average of two middle values if even number of districts
        median_dem = dem_districts_dem_pct[len(dem_districts_dem_pct) // 2]

        # Find 50-50 point
        fifty_fifty_point = len(rep_districts_dem_pct) + 0.5 # TODO: check if this correct

        # Calculate slopes from median districts to fifty-fifty point
        slope_rep = (0.5 - median_rep) / (fifty_fifty_point - median_rep) # TODO: check if this correct
        slope_dem = (0.5 - median_dem) / (fifty_fifty_point - median_dem)

        # Return declination
        declination = (2 * (slope_dem - slope_rep)) / pi
        return declination
        
    def check_crs_consistency(self):
        '''
        Checks if the CRS of all GeoDataFrames are consistent.
        '''
        # TODO: add other GeoDataFrames
        assert self.fitness_landscape.crs == self.initial_plan.crs == self.state_leg_map.crs == self.state_sen_map.crs, f'CRS mismatch: fitness_landscape=({self.fitness_landscape.crs}); initial_plan=({self.initial_plan.crs}); state_leg_map=({self.state_leg_map.crs}); state_sen_map=({self.state_sen_map.crs})'
        if self.console: print('All CRS are consistent.')
    
    def set_up_gerrychain(self, totpop_id, district_id, n_proposed_maps):
        '''
        Set up the gerrychain Markov chain for generating new plans.

        totpop_id: column name for total population numbers of dataframe consisting precinct data
        district_id: column name for district names of dataframe consisting precinct data
        n_proposed_maps: model parameter value for number of proposed maps per gerrymandering cycle
        '''
        self.graph = Graph.from_geodataframe(self.precincts)
        self.updaters = {
            'population': updaters.Tally(totpop_id, alias='population'),
            'cut_edges': updaters.cut_edges,
            'perimeter': updaters.perimeter,
            'area': updaters.Tally('area', alias='area'),
            'geometry': updaters.boundary_nodes,
        }
        self.initial_partition = GeographicPartition(
            self.graph,
            assignment=district_id,
            updaters=self.updaters
        )
        self.ideal_population = sum(self.initial_partition['population'].values()) / len(self.initial_partition)
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
        if self.console: print('GerryChain set up.')

    def create_counties_districts(self, county_id, district_id):
        '''
        Create counties and US House districts agents for the model.

        county_id: column name for county names of dataframe consisting initial plan data
        district_id: column name for electoral district names of dataframe consisting initial plan data
        '''
        # TODO: add state leg and senate districts to model to run elections.
        # Set up congressional electoral districts for simulating gerrymandering/electoral processes
        ac_cong = mg.AgentCreator(DistrictAgent, model=self, agent_kwargs={'type': 'congressional'})
        self.USHouseDistricts = ac_cong.from_GeoDataFrame(self.initial_plan, unique_id=district_id)
        self.num_USHouseDistricts = len(self.USHouseDistricts)
        if self.console: 
            print('# of electoral districts:')
            print('\tCongressional: ', self.num_USHouseDistricts)

        # Set up state house electoral districts for simulating state house elections
        ac_leg = mg.AgentCreator(DistrictAgent, model=self, agent_kwargs={'type': 'state-house'})
        self.StateHouseDistricts = ac_leg.from_GeoDataFrame(self.state_leg_map, unique_id=district_id)
        self.num_StateHouseDistricts = len(self.StateHouseDistricts)
        if self.console: print('\tState House: ', self.num_StateHouseDistricts)
        # self.space.add_districts(self.StateHouseDistricts)

        # Set up state senate electoral districts for simulating state senate elections
        ac_sen = mg.AgentCreator(DistrictAgent, model=self, agent_kwargs={'type': 'state-senate'})
        self.StateSenateDistricts = ac_sen.from_GeoDataFrame(self.state_sen_map, unique_id=district_id)
        self.num_StateSenateDistricts = len(self.StateSenateDistricts)
        if self.console: print('\tState Senate: ', self.num_StateSenateDistricts)
        # self.space.add_districts(self.StateSenateDistricts)

        # Set up counties for simulating population shifts
        ac_c = mg.AgentCreator(CountyAgent, model=self)
        self.counties = ac_c.from_GeoDataFrame(self.fitness_landscape, unique_id=county_id)
        self.n_counties = len(self.counties)
        self.space.add_counties(self.counties)

        # Rename unique_id
        [setattr(district, 'unique_id', f'{district.type}-{district.unique_id}') for district in self.USHouseDistricts]
        [setattr(district, 'unique_id', f'{district.type}-{district.unique_id}') for district in self.StateHouseDistricts]
        [setattr(district, 'unique_id', f'{district.type}-{district.unique_id}') for district in self.StateSenateDistricts]

        # Add districts to the scheduler
        [self.schedule.add(district) for district in self.USHouseDistricts]
        [self.schedule.add(district) for district in self.StateHouseDistricts]
        [self.schedule.add(district) for district in self.StateSenateDistricts]

        # Add districts to visualization map
        self.space.add_districts(self.USHouseDistricts)

        # Update the county to congressional district map
        self.space.update_county_to_district_map(self.counties, self.USHouseDistricts)

        if self.console: print('Counties and districts created.')

    def update_census_data(self):
        '''
        Updates the data of all electoral district agents in the model.
        '''
        # Color districts based on initial plan
        for district in self.USHouseDistricts:
            district.update_district_data()
            district.update_district_color()
        
        # Update data of state house and senate districts
        for district in self.StateHouseDistricts:
            district.update_district_data()
            district.update_district_color()
            
        for district in self.StateSenateDistricts:
            district.update_district_data()
            district.update_district_color()

    def update_utilities(self):
        '''
        Updates utilities of all agents in model.
        '''
        [agent.update_utility() for agent in self.population]

    def create_population(self):
        '''
        Create and add Person agents for the model.
        '''
        # Initialize population list
        self.population = []

        # Initialize party counts
        self.ndems = 0
        self.nreps = 0

        # Initialize total state capacity
        self.total_cap = 0

        # Add agents to the space per county
        for county in self.counties:

            # Determine initial number of people in the county
            pop_county = ceil(county.TOTPOP_SHR * self.npop)
            # Set county capacity (update state total capacity)
            county.capacity = ceil(county.CAPACITY_SHR * self.npop * self.capacity_mul)
            self.total_cap += county.capacity
            if self.console: print(f'County {county.unique_id} (District: {self.space.county_district_map[county.unique_id]}) has {pop_county} people and {county.capacity} capacity')

            # Add people to the county
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
                self.space.add_person_to_county(person, new_county_id=county.unique_id)
                self.schedule.add(person)
                self.population.append(person)

                # Update party counts
                if person.is_red: 
                    self.nreps += 1
                else: 
                    self.ndems += 1

            # Add county to the scheduler
            self.schedule.add(county)

        # Update the number of people in the model
        self.npop = len(self.population)
        # self.update_utilities()
        if self.console: print('People created.')

    def step(self):
        if self.console:
            print('------------------------------------')
            print('Advancing model... (t={})'.format(self.schedule.steps+1))

        # Advance all agents one step (includes sorting)
        self.schedule.step()
        if self.console: print('All agents stepped. (sorting complete)')

        # Perform gerrymandering
        if self.gerrymandering: 
        # if not self.unhappy:     # Only gerrymander when sorting has converged
            gerrymander(self)
            if self.console: print('Gerrymandering complete.')

        # Update utilities
        self.update_utilities()

        # Collect data
        self.datacollector.collect(self)
