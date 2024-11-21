from .space import ElectoralDistricts
from .utils.initialization import *
from .utils.statistics import *
from .utils.redistricting import *

import mesa

class GerrySort(mesa.Model):
    def __init__(self, state='MN', level='CONGDIST', data=None, max_iters=5, 
                 npop=5800, sorting=True, gerrymandering=True, 
                 control_rule='CONGDIST', initial_control='Data', tolarence=0.5, 
                 beta=0.0, ensemble_size=5, epsilon=0.1, sigma=0.0,
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
        self.control_rule = control_rule
        self.tolarence = tolarence
        self.beta = beta
        self.ensemble_size = ensemble_size
        self.epsilon = epsilon
        self.sigma = sigma
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
        update_statistics(self)
        # Ininitialize party controlling the state based on initial plan
        if initial_control == 'Data':
            self.control = self.projected_winner
        else:
            self.control = initial_control
        # Setup datacollector and collect data
        self.datacollector.collect(self)
        # Print statistics
        print_statistics(self)
        print('Model initialized!')

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

    def step(self):
        print(f'Model step {self.iter}...')
        # Gerrymander
        if self.gerrymandering: 
            self.gerrymander()
            print(f'\tMap changed by {self.change_map}%')
        # Sort agents
        if self.sorting:
            self.self_sort()
            print(f'\t{self.total_moves} agents moved.')
        # Update majorities (Election)
        self.update_majorities([self.precincts, self.counties, self.congdists, self.legdists, self.sendists])
        # Update utility of all agents
        self.update_utilities()
        # Update statistics
        update_statistics(self)
        # Collect data
        self.datacollector.collect(self)
        # Print statistics
        print_statistics(self)
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
