import geopandas as gpd
import os

import mesa
from .space import ElectoralDistricts
from .utils.initialization import *
from .utils.statistics import *
from .utils.redistricting import *

class GerrySort(mesa.Model):
    def __init__(self, state='MN', data=None, max_iters=5, 
                 npop=1000, gerrymandering=True, sorting=True, 
                 tolarence=0.5, beta=0.0, n_proposed_maps=5, 
                 n_moving_options=5, moving_cooldown=5, 
                 distance_decay=0.5, capacity_mul=1.0):
        # Set up the scheduler and space
        self.schedule = mesa.time.BaseScheduler(self) # TODO: Look into other schedulers
        self.space = ElectoralDistricts()

        # Set model running conditions
        self.running = True
        self.iter = 0
        self.max_iters = max_iters

        # Set model parameters
        self.gerrymandering = gerrymandering
        self.sorting = sorting
        self.npop = npop
        self.tolarence = tolarence
        self.capacity_mul = capacity_mul
        self.n_proposed_maps = n_proposed_maps
        self.beta = beta
        self.n_moving_options = n_moving_options
        self.moving_cooldown = moving_cooldown
        self.distance_decay = distance_decay

        # Load GeoData file
        load_data(self, state, data)

        # Initialize model statistics
        setup_datacollector(self)

        # Create geographical units
        create_precincts(self)
        create_counties(self)
        # create_state_legislatures(self)
        create_congressional_districts(self)

        # Create precinct to county/congressional district map
        self.space.create_precinct_to_county_map(self.precincts)
        self.space.create_precinct_to_congdist_map(self.precincts)

        # Create population
        create_population(self)

        # Update majorities
        self.update_majorities(self.precincts)
        self.update_majorities(self.counties)
        self.update_majorities(self.congdists)

        # Update utility of all agents
        self.update_utilities()
        # Update statistics
        self.update_statistics(statistics=[unhappy_happy, congdist_seats, 
                                    # red_state_house_seats, blue_state_house_seats, tied_state_house_seats, 
                                    # red_state_senate_seats, blue_state_senate_seats, tied_state_senate_seats,  
                                    # efficiency_gap, mean_median, declination,
                                    projected_winner, projected_margin, 
                                    variance])
        # Ininitialize party controlling the state based on initial plan
        self.control = self.projected_winner 

        # Setup datacollector and collect data
        self.datacollector.collect(self)
        # # Print all statistics
        print('Statistics:') # TODO: Compare intial statistics with real data
        print(f'\tUnhappy: {self.unhappy} | Unhappy Red: {self.unhappy_red} | Unhappy Blue: {self.unhappy_blue}')
        print(f'\tHappy: {self.happy} | Happy Red: {self.happy_red} | Happy Blue: {self.happy_blue}')
        print(f'\tRed Congressional Seats: {self.red_congdist_seats} | Blue Congressional Seats: {self.blue_congdist_seats} | Tied Congressional Seats: {self.tied_congdist_seats}')
        print(f'\tPopulation counts: {[district.num_people for district in self.congdists]}')
        print(f'\tVariance: {self.variance}')
        # # print(f'\tRed State House Seats: {self.red_state_house_seats} | Blue State House Seats: {self.blue_state_house_seats} | Tied State House Seats: {self.tied_state_house_seats}')
        # # print(f'\tRed State Senate Seats: {self.red_state_senate_seats} | Blue State Senate Seats: {self.blue_state_senate_seats} | Tied State Senate Seats: {self.tied_state_senate_seats}')
        # print(f'\tEfficiency Gap: {self.efficiency_gap}')
        # print(f'\tMean Median: {self.mean_median}')
        # print(f'\tDeclination: {self.declination}')
        print(f'\tControl: {self.control}')
        print(f'\tProjected Winner: {self.projected_winner}')
        print(f'\tProjected Margin: {self.projected_margin}')
        print('Model initialized!')
        print('------------------------------------')

    def update_statistics(self, statistics=[unhappy_happy, 
                                            congdist_seats,
                                        #  red_state_house_seats, blue_state_house_seats, tied_state_house_seats, 
                                        #  red_state_senate_seats, blue_state_senate_seats, tied_state_senate_seats,  
                                        #  efficiency_gap, mean_median, declination,
                                         projected_winner, projected_margin, 
                                         variance]):
        for stat in statistics:
            stat(self)

    def update_majorities(self, geo_units):
        for unit in geo_units:
            unit.update_majority()

    def update_utilities(self):
        [agent.update_utility() for agent in self.population]

    def self_sort(self):
        self.total_moves = 0
        print('Sorting...')
        # Update moving cooldown
        for agent in self.population:
            # Check if utility is below threshold and cooldown has passed
            if agent.is_unhappy and self.moving_cooldown <= agent.last_moved:
                agent.sort()
        print(f'\t{self.total_moves} agents moved.')

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
        print('Gerrymandering...')
        print(f'\tThis is a {self.control} state.')
            
        # Evalaute the plans
        eval_results = evaluate_plans(self)
        print(f'\t {len(eval_results)} plans evaluated.')

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
        print(f'\tMap changed by {self.change_map} mi^2.')

    def step(self):
        self.control = self.projected_winner

        if self.sorting:
            self.self_sort()
            print('Sorting complete!')

        if self.gerrymandering: 
        # if not self.unhappy:     # Only gerrymander when sorting has converged
            self.gerrymander()
            print('Gerrymandering complete!')

        # Update majorities
        self.update_majorities(self.precincts)
        self.update_majorities(self.counties)
        self.update_majorities(self.congdists)
        
        # Update utility of all agents
        self.update_utilities()
        # Update statistics
        self.update_statistics(statistics=[unhappy_happy, congdist_seats, 
                                    # red_state_house_seats, blue_state_house_seats, tied_state_house_seats, 
                                    # red_state_senate_seats, blue_state_senate_seats, tied_state_senate_seats,  
                                    # efficiency_gap, mean_median, declination,
                                    projected_winner, projected_margin, 
                                    variance])

        # Collect data
        self.datacollector.collect(self)

        self.iter += 1
        
        # # Print some model info
        print('Statistics:')
        print(f'\tUnhappy: {self.unhappy} | Unhappy Red: {self.unhappy_red} | Unhappy Blue: {self.unhappy_blue}')
        print(f'\tHappy: {self.happy} | Happy Red: {self.happy_red} | Happy Blue: {self.happy_blue}')
        print(f'\tRed Congressional Seats: {self.red_congdist_seats} | Blue Congressional Seats: {self.blue_congdist_seats} | Tied Congressional Seats: {self.tied_congdist_seats}')
        print(f'\tPopulation counts: {[district.num_people for district in self.congdists]}')
        print(f'\tVariance: {self.variance}')
        # # print(f'\tRed State House Seats: {self.red_state_house_seats} | Blue State House Seats: {self.blue_state_house_seats} | Tied State House Seats: {self.tied_state_house_seats}')
        # # print(f'\tRed State Senate Seats: {self.red_state_senate_seats} | Blue State Senate Seats: {self.blue_state_senate_seats} | Tied State Senate Seats: {self.tied_state_senate_seats}')
        # print(f'\tEfficiency Gap: {self.efficiency_gap}')
        # print(f'\tMean Median: {self.mean_median}')
        # print(f'\tDeclination: {self.declination}')
        print(f'\tControl: {self.control}')
        print(f'\tProjected Winner: {self.projected_winner}')
        print(f'\tProjected Margin: {self.projected_margin}')
        print(f'\tNumber of Moves: {self.total_moves}')
        # print(f'\tChange in Map: {self.change_map}')
        # print('Capacity counties:')
        # [print(f'\t{county.unique_id}: {county.num_people}/{county.capacity}') for county in self.counties]

        # If energy (total moves and change in map) is zero, then the model has converged
        # if self.total_moves == 0 and self.change_map == 0 or self.iter >= self.max_iters:
        if self.iter >= self.max_iters:
            print('Model converged! (t={})'.format(self.iter))
            self.running = False
        else:
            print('Model advanced!')
            print('------------------------------------')