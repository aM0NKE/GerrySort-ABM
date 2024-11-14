from .space import ElectoralDistricts
from .utils.initialization import *
from .utils.statistics import *
from .utils.redistricting import *

import mesa

class GerrySort(mesa.Model):
    def __init__(self, state='MN', level='CONGDIST', data=None, max_iters=5, 
                 npop=5800, sorting=True, gerrymandering=True, 
                 initial_control='Data', tolarence=0.5, 
                 beta=0.0, ensemble_size=5, epsilon=0.1,
                 n_moving_options=5, moving_cooldown=0, 
                 distance_decay=0.0, capacity_mul=1.0):
        # Set up the scheduler and space
        self.schedule = mesa.time.BaseScheduler(self) # TODO: Look into other schedulers
        self.space = ElectoralDistricts()
        self.space.level = level
        # Set model running conditions
        self.running = True
        self.iter = 1
        self.max_iters = max_iters
        # Set model parameters
        self.npop = npop
        self.sorting = sorting
        self.gerrymandering = gerrymandering
        self.tolarence = tolarence
        self.beta = beta
        self.ensemble_size = ensemble_size
        self.epsilon = epsilon
        self.n_moving_options = n_moving_options
        self.moving_cooldown = moving_cooldown
        self.distance_decay = distance_decay
        self.capacity_mul = capacity_mul
        # Load GeoData file
        load_data(self, state, data)
        # Initialize model statistics
        setup_datacollector(self)
        # Create geographical units
        create_precincts(self)
        create_counties(self)
        create_state_legislatures(self)
        create_congressional_districts(self)
        # Create precinct to county/congressional district map
        self.space.create_precinct_to_county_map(self.precincts)
        self.space.create_precinct_to_legdist_map(self.precincts)
        self.space.create_precinct_to_sendist_map(self.precincts)
        self.space.create_precinct_to_congdist_map(self.precincts)
        # Create population
        create_population(self)
        # Update majorities
        self.update_majorities([self.precincts, self.counties, self.congdists, self.legdists, self.sendists])
        # Update utility of all agents
        self.update_utilities()
        # Update statistics
        self.update_statistics()
        # Ininitialize party controlling the state based on initial plan
        if initial_control == 'Data':
            self.control = self.projected_winner
        else:
            self.control = initial_control
        # Setup datacollector and collect data
        self.datacollector.collect(self)
        # Print statistics
        self.print_statistics()
        print('Model initialized!')

    def update_statistics(self, statistics=[unhappy_happy, congdist_seats,
                                            legdist_seats, sendist_seats, variance,
                                            efficiency_gap, mean_median, declination,
                                            projected_winner, projected_margin]):
        for stat in statistics:
            stat(self)

    def update_majorities(self, maps):
        for map in maps:
            for unit in map:
                unit.update_majority()

    def update_utilities(self):
        [agent.update_utility() for agent in self.population]

    def self_sort(self):
        print('Sorting...')
        # Move agents if unhappy
        self.total_moves = 0
        for agent in self.population:
            if agent.is_unhappy and self.moving_cooldown <= agent.last_moved:
                agent.sort()
            else:
                agent.last_moved += 1

    def gerrymander(self):
        print(f'Gerrymandering in favor of {self.control}...')
        # Generate ensemble
        plans_list, district_data = generate_ensemble(self)
        # Select plan with maximum partisan gain for party in control (or random in case of tie)
        best_plan = find_best_plan(self, district_data) 
        # Update the model with the best plan
        reassigned_precincts = redistrict(self, plans_list, best_plan)
        # Update precinct to congdist mapping
        update_mapping(self, reassigned_precincts)

    def print_statistics(self):
        print('Statistics:')
        print(f'\tUnhappy: {self.unhappy} | Unhappy Red: {self.unhappy_rep} | Unhappy Blue: {self.unhappy_dem}')
        print(f'\tHappy: {self.happy} | Happy Red: {self.happy_rep} | Happy Blue: {self.happy_dem}')
        print(f'\tRed Congressional Seats: {self.rep_congdist_seats} | Blue Congressional Seats: {self.dem_congdist_seats} | Tied Congressional Seats: {self.tied_congdist_seats}')
        print(f'\tPopulation counts: {[district.num_people for district in self.congdists]}')
        print(f'\tVariance: {self.variance}')
        print(f'\tRed State House Seats: {self.rep_legdist_seats} | Blue State House Seats: {self.dem_legdist_seats} | Tied State House Seats: {self.tied_sendist_seats}')
        print(f'\tRed State Senate Seats: {self.rep_sendist_seats} | Blue State Senate Seats: {self.dem_sendist_seats} | Tied State Senate Seats: {self.tied_sendist_seats}')
        print(f'\tEfficiency Gap: {self.efficiency_gap}')
        print(f'\tMean Median: {self.mean_median}')
        print(f'\tDeclination: {self.declination}')
        print(f'\tControl: {self.control}')
        print(f'\tProjected Winner: {self.projected_winner}')
        print(f'\tProjected Margin: {self.projected_margin}')
        print(f'\t[ENERGY] Number of Moves: {self.total_moves}')
        print(f'\t[ENERGY] % Reassigned Precincts: {self.change_map}')
        # print('Capacity counties:')
        # [print(f'\t{county.unique_id}: {county.num_people}/{county.capacity}') for county in self.counties]

    def step(self):
        print(f'Model step {self.iter}...')
        # Sort agents
        if self.sorting:
            self.self_sort()
            print(f'\t{self.total_moves} agents moved.')
        # Gerrymander
        if self.gerrymandering: 
            self.gerrymander()
            print(f'\tMap changed by {self.change_map}%')
        # Update majorities
        self.update_majorities([self.precincts, self.counties, self.congdists, self.legdists, self.sendists])
        # Update utility of all agents
        self.update_utilities()
        # Update statistics
        self.update_statistics()
        # Collect data
        self.datacollector.collect(self)
        # Print statistics
        self.print_statistics()
        if self.iter >= self.max_iters:
            self.running = False
            print('Model converged! (t={})'.format(self.iter))
            print('------------------------------------')
        else:
            # The party in control is the projected winner
            self.control = self.projected_winner
            self.iter += 1
            print('Model advanced!')
            print('------------------------------------')
