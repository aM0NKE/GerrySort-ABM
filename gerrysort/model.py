import geopandas as gpd
import os

import mesa
from .space import ElectoralDistricts
from .utils.initialization import *
from .utils.statistics import *
from .utils.redistricting import *

class GerrySort(mesa.Model):
    def __init__(self, state='MN', ensemble=None, initial_plan=None, state_leg_map=None, state_sen_map=None, fitness_landscape=None, max_iters=5, npop=1000, gerrymandering=True, sorting=True, tolarence=0.5, beta=0.0, n_proposed_maps=5, n_moving_options=5, moving_cooldown=5, distance_decay=0.5, capacity_mul=1.0,):
        '''
        Initialize the model with the given parameters.

        Parameters:
            state (str): state to simulate
            console (bool): whether to print details in console
            tolarence (float): threshold for agent unhappiness
            beta (float): temperature for the Boltzmann distribution
            capacity_mul (float): multiplier for the capacity of each county
            gerrymandering (bool): whether to simulate gerrymandering
            sorting (bool): whether to simulate sorting
            npop (int): number of agents in the model
            n_proposed_maps (int): size of the potential map pool for gerrymandering
            n_moving_options (int): number of moving options for sorting
            moving_cooldown (int): number of steps between sorting moves
        
        TODO: Add assert statements after initialization and after each step!
        '''
        # Debug (set this to true to print details in console)
        # print('Initializing model...')

        # Set up the schedule and space
        self.schedule = mesa.time.BaseScheduler(self) # TODO: Look into other schedulers
        self.space = ElectoralDistricts()
        self.running = True
        self.iter = 0
        self.max_iters = max_iters

        # Set phenomona flags
        self.gerrymandering = gerrymandering
        self.sorting = sorting

        # Load GeoData files
        self.state = state
        self.ensemble = ensemble.to_crs(self.space.crs)
        self.initial_plan = initial_plan.to_crs(self.space.crs)
        self.state_leg_map = state_leg_map.to_crs(self.space.crs)
        self.state_sen_map = state_sen_map.to_crs(self.space.crs)
        self.fitness_landscape = fitness_landscape.to_crs(self.space.crs)
        check_crs_consistency(self)

        # Set parameters to model attributes
        self.npop = npop
        self.tolarence = tolarence
        self.capacity_mul = capacity_mul
        self.n_proposed_maps = n_proposed_maps
        self.beta = beta
        self.n_moving_options = n_moving_options
        self.moving_cooldown = moving_cooldown
        # self.distance_decay = distance_decay # TODO: check if still included in model

        # Set up statistics the data collector
        self.unhappy = 0
        self.unhappy_red = 0
        self.unhappy_blue = 0
        self.happy = 0
        self.happy_blue = 0
        self.happy_red = 0
        self.n_moves = 0
        self.red_congressional_seats = 0
        self.blue_congressional_seats = 0
        self.tied_congressional_seats = 0
        self.red_state_house_seats = 0
        self.blue_state_house_seats = 0
        self.tied_state_house_seats = 0
        self.red_state_senate_seats = 0
        self.blue_state_senate_seats = 0
        self.tied_state_senate_seats = 0
        self.efficiency_gap = 0
        self.mean_median = 0
        self.declination = 0
        self.projected_winner = None
        self.projected_margin = 0
        self.variance = 0 # TODO: create variance statistic for population distribution across electoral districts (to check if map valid)
        self.change_map = 0 # TODO: create statistic for change in map square kilometers (energy)
        self.datacollector = mesa.DataCollector(
            {'unhappy': 'unhappy', 
            'unhappy_red': 'unhappy_red',
            'unhappy_blue': 'unhappy_blue',
            'happy': 'happy',
            'happy_red': 'happy_red',
            'happy_blue': 'happy_blue',
            'red_congressional_seats': 'red_congressional_seats',
            'blue_congressional_seats': 'blue_congressional_seats',
            'tied_congressional_seats': 'tied_congressional_seats',
            'variance': 'variance',
            'red_state_house_seats': 'red_state_house_seats',
            'blue_state_house_seats': 'blue_state_house_seats',
            'tied_state_house_seats': 'tied_state_house_seats',
            'red_state_senate_seats': 'red_state_senate_seats',
            'blue_state_senate_seats': 'blue_state_senate_seats',
            'tied_state_senate_seats': 'tied_state_senate_seats',
            'efficiency_gap': 'efficiency_gap',
            'mean_median': 'mean_median',
            'declination': 'declination',
            'control': 'control',
            'projected_winner': 'projected_winner',
            'projected_margin': 'projected_margin',
            'control': 'control',
            'n_moves': 'n_moves',
            'change_map': 'change_map'
            })

        # Create counties, districts, and population
        create_counties_districts(self)
        create_population(self)

        # Update census data
        self.update_census_data() # TODO: FIX PROBLEM HERE!

        # Update statistics
        self.update_statistics(statistics=[red_congressional_seats, blue_congressional_seats, tied_congressional_seats, 
                                    red_state_house_seats, blue_state_house_seats, tied_state_house_seats, 
                                    red_state_senate_seats, blue_state_senate_seats, tied_state_senate_seats,  
                                    efficiency_gap, mean_median, declination,
                                    projected_winner, projected_margin, 
                                    variance])
        # Update utility of all agents
        self.update_utilities()
        self.update_statistics(statistics=[unhappy_happy])

        # Ininitialize party controlling the state based on initial plan
        self.control = self.projected_winner 

        # Setup datacollector and collect data
        self.datacollector.collect(self)
        # Print all statistics
        # print('Statistics:') # TODO: Compare intial statistics with real data
        # print(f'\tUnhappy: {self.unhappy} | Unhappy Red: {self.unhappy_red} | Unhappy Blue: {self.unhappy_blue}')
        # print(f'\tHappy: {self.happy} | Happy Red: {self.happy_red} | Happy Blue: {self.happy_blue}')
        # print(f'\tRed Congressional Seats: {self.red_congressional_seats} | Blue Congressional Seats: {self.blue_congressional_seats} | Tied Congressional Seats: {self.tied_congressional_seats}')
        # print(f'\tPopulation counts: {[district.num_people for district in self.USHouseDistricts]}')
        # print(f'\tVariance: {self.variance}')
        # print(f'\tRed State House Seats: {self.red_state_house_seats} | Blue State House Seats: {self.blue_state_house_seats} | Tied State House Seats: {self.tied_state_house_seats}')
        # print(f'\tRed State Senate Seats: {self.red_state_senate_seats} | Blue State Senate Seats: {self.blue_state_senate_seats} | Tied State Senate Seats: {self.tied_state_senate_seats}')
        # print(f'\tEfficiency Gap: {self.efficiency_gap}')
        # print(f'\tMean Median: {self.mean_median}')
        # print(f'\tDeclination: {self.declination}')
        # print(f'\tControl: {self.control}')
        # print(f'\tProjected Winner: {self.projected_winner}')
        # print(f'\tProjected Margin: {self.projected_margin}')
        # print(f'\tNumber of Moves: {self.n_moves}')
        # Print distribution of person.county_id
        # print('County distribution:')
        # dist = {county.unique_id: 0 for county in self.counties}
        # for person in self.population:
        #     dist[person.county_id] += 1
        # print(dist)
        # print('Model initialized!')

    def update_statistics(model, statistics=[unhappy_happy, n_moves, 
                                         red_congressional_seats, blue_congressional_seats, tied_congressional_seats, 
                                         red_state_house_seats, blue_state_house_seats, tied_state_house_seats, 
                                         red_state_senate_seats, blue_state_senate_seats, tied_state_senate_seats,  
                                         efficiency_gap, mean_median, declination,
                                         projected_winner, projected_margin, 
                                         variance]):
        '''
        Updates all or a subset of the model statistics.
        '''
        for stat in statistics:
            stat(model)

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

        for county in self.counties:
            county.update_district_data()

    def update_utilities(self):
        '''
        Updates utilities of all agents in model.
        '''
        [agent.update_utility() for agent in self.population]

    def self_sort(self):
        '''
        Self-sorting process for agents in the model.
        '''
        # Update moving cooldown
        for agent in self.population:
            # Check if utility is below threshold and cooldown has passed
            if agent.is_unhappy and self.moving_cooldown <= agent.last_moved:
                agent.sort()
            else:
                agent.last_moved += 1

    def gerrymander(self):
        '''
        Performs the gerrymandering phenomon.

        Steps:
            1. draws random ensemble of plans
            2. evaluates ensemble
            3. selects map from ensemble (+current map) that maximizes 
            the parisan gain by party in controll of redistricting
            (in case of tie, the most neutral map is selected)

        TODO: Do variance check for validity map
        '''
        # Evalaute the plans
        eval_results = evaluate_plans(self)

        # Find the plan that maximizes the number of districts favoring the party in control
        if self.control == 'Republican':
            # Select plan with most red districts
            best_plan = max(eval_results, key=lambda x: eval_results[x]['red_congressional_seats'])
            # print('\nBest Republican plan:', best_plan)
            # print('Republican state, maximizing red districts')    
        elif self.control == 'Democratic':
            # Select plan that most blue districts
            best_plan = max(eval_results, key=lambda x: eval_results[x]['blue_congressional_seats'])
            # print('\nBest Democratic plan:', best_plan)
            # print('Democrart state, maximizing blue districts')
        # Or, in case of a tie, select the plan that minimizes efficiency gap
        elif self.control == 'Tied':
            # Select plan with efficiency gap closest to 0 (fairness)
            best_plan = min(eval_results, key=lambda x: abs(eval_results[x]['efficiency_gap']))
            # print('\nBest plan:', best_plan)
            # print('Tied state, minimizing efficiency gap')

        # Update the model with the best plan
        redistrict(self, eval_results[best_plan]['geometry'])

        # Update map_change statistic
        change_map(self, eval_results['-1'], eval_results[best_plan])

    def step(self):
        # print('------------------------------------')
        self.control = self.projected_winner

        if self.sorting:
            self.self_sort()
            # print('Sorting complete.')

        if self.gerrymandering: 
        # if not self.unhappy:     # Only gerrymander when sorting has converged
            self.gerrymander()
            # print('Gerrymandering complete.')

        # Update census data
        self.update_census_data()

        # Update agents' utilities
        self.update_utilities()

        # Update and collect data
        self.update_statistics()
        self.datacollector.collect(self)

        self.iter += 1
        
        # Print some model info
        # print('Statistics:')
        # print(f'\tUnhappy: {self.unhappy} | Unhappy Red: {self.unhappy_red} | Unhappy Blue: {self.unhappy_blue}')
        # print(f'\tHappy: {self.happy} | Happy Red: {self.happy_red} | Happy Blue: {self.happy_blue}')
        # print(f'\tRed Congressional Seats: {self.red_congressional_seats} | Blue Congressional Seats: {self.blue_congressional_seats} | Tied Congressional Seats: {self.tied_congressional_seats}')
        # print(f'\tPopulation counts: {[district.num_people for district in self.USHouseDistricts]}')
        # print(f'\tVariance: {self.variance}')
        # print(f'\tRed State House Seats: {self.red_state_house_seats} | Blue State House Seats: {self.blue_state_house_seats} | Tied State House Seats: {self.tied_state_house_seats}')
        # print(f'\tRed State Senate Seats: {self.red_state_senate_seats} | Blue State Senate Seats: {self.blue_state_senate_seats} | Tied State Senate Seats: {self.tied_state_senate_seats}')
        # print(f'\tEfficiency Gap: {self.efficiency_gap}')
        # print(f'\tMean Median: {self.mean_median}')
        # print(f'\tDeclination: {self.declination}')
        # print(f'\tControl: {self.control}')
        # print(f'\tProjected Winner: {self.projected_winner}')
        # print(f'\tProjected Margin: {self.projected_margin}')
        # print(f'\tNumber of Moves: {self.n_moves}')
        # print(f'\tChange in Map: {self.change_map}')
        # print('Capacity counties:')
        # [print(f'\t{county.unique_id}: {county.num_people}/{county.capacity}') for county in self.counties]
        # Print distribution of person.county_id
        # print('County distribution:')
        # dist = {county.unique_id: 0 for county in self.counties}
        # for person in self.population:
        #     dist[person.county_id] += 1
        # print(dist)
        # If energy (total moves and change in map) is zero, then the model has converged
        # if self.n_moves == 0 and self.change_map == 0 or self.iter >= self.max_iters:
        if self.iter >= self.max_iters:
            # print('Model converged! (t={})'.format(self.time))
            self.running = False
        # print('Model advanced!')
        # print('------------------------------------')