from .space import ElectoralDistricts
from .utils.initialization import *
from .utils.statistics import *
from .utils.redistricting import *

import mesa

class GerrySort(mesa.Model):
    def __init__(self, state='GA', print_output=False, save_plans=False, vis_level=None, data=None, election='PRES20', 
                 max_iters=4, npop=11000, sorting=True, gerrymandering=True, 
                 control_rule='CONGDIST', initial_control='Model', tolerance=0.5, beta=100.0,
                 ensemble_size=250, epsilon=0.01, sigma=0.01,
                 n_moving_options=10, distance_decay=0.0, capacity_mul=1.0, 
                 intervention='None', intervention_weight=0.0):
        self.simulation_id = str(uuid.uuid4())[:8]  # Unique simulation ID
        self.state = state
        # Set up the scheduler and space
        self.schedule = mesa.time.RandomActivation(self)
        self.space = ElectoralDistricts()
        self.print = print_output
        self.save_plans = save_plans
        self.space.vis_level = vis_level
        self.steps = 0
        self.running = True
        # Set model parameters
        self.election = election
        self.max_iters = max_iters
        self.npop = npop
        self.sorting = sorting
        self.gerrymandering = gerrymandering
        self.control_rule = control_rule
        self.tolerance = tolerance
        self.beta = beta
        self.ensemble_size = ensemble_size
        self.epsilon = epsilon
        self.sigma = sigma
        self.n_moving_options = n_moving_options
        self.distance_decay = distance_decay
        self.capacity_mul = capacity_mul
        # Set intervention parameters
        self.intervention = intervention
        self.intervention_weight = intervention_weight
        # Load Initial Plan
        load_data(self, state, data)
        # Initialize model statistics
        setup_datacollector(self)
        # Create geographical units
        create_precincts(self)
        create_counties(self)
        create_congressional_districts(self)
        # Create precinct to county/congressional district map
        self.space.create_precinct_to_county_map(self.precincts)
        self.space.create_precinct_to_congdist_map(self.precincts)
        # Create population
        create_population(self)
        # Update majorities
        self.update_majorities([self.precincts, self.counties, self.congdists])
        # Update utility of all agents
        self.update_utilities()
        # Update statistics
        update_statistics(self, statistics=[competitiveness, compactness,
                                            efficiency_gap, mean_median, declination, 
                                            pop_deviation, unhappy_happy, avg_utility, segregation,
                                            congdist_seats, projected_winner, projected_margin])
        # Ininitialize party controlling the state based on initial plan
        if initial_control == 'Model':
            self.control = self.projected_winner
        elif initial_control in ['Democrats', 'Republicans', 'Fair']:
            self.control = initial_control
        # Setup datacollector and collect data
        self.datacollector.collect(self)
        # Print statistics
        if self.print:
            print_statistics(self)
            print('Model initialized!')

    def update_majorities(self, maps):
        for map in maps:
            for unit in map:
                unit.update_majority()

    def update_utilities(self):
        [agent.update_utility() for agent in self.population]

    def self_sort(self):
        if self.print: print('Sorting...')
        # Move agents if unhappy
        self.total_moves = 0
        for agent in self.population:
            if agent.is_unhappy:
                agent.sort()

    def gerrymander(self):
        if self.print: print(f'Gerrymandering in favor of {self.control}...')
        # Run the MCMC algorithm to find the best plan (optimized for the control party)
        find_best_plan(self)
        # Update the boundaries of the congressional districts and keep track of reassigned precincts
        reassigned_precincts = redistrict(self)
        # Update the precinct to congressional district map
        update_mapping(self, reassigned_precincts)

    def step(self):
        self.steps += 1
        if self.print: print(f'Model step {self.steps}...')

        # 1. Gerrymander
        if self.gerrymandering: 
            self.gerrymander()
        
        # 2. Sort agents
        if self.sorting:
            self.self_sort()
        
        # 3. Update majorities (Election)
        self.update_majorities([self.precincts, self.counties, self.congdists])
        # Update utility of all agents
        self.update_utilities()
        # Update statistics
        update_statistics(self)
        
        # Collect data
        self.datacollector.collect(self)
        # Print statistics
        if self.print: print_statistics(self)
        if self.save_plans:
            filename = f'data/generated_maps/{self.state}_sim_{self.simulation_id}_step_{self.steps}.geojson'
            save_current_map(self, filename=filename)
        
        # Check if the model should stop
        if self.steps >= self.max_iters:
            self.running = False
            if self.print: 
                print(f'Simulation done! (steps={self.steps})')
                print('------------------------------------')
        else:
            # The party in control is the projected winner
            if self.control_rule != 'FIXED':    
                self.control = self.projected_winner
            if self.print: 
                print('Model advanced!')
                print('------------------------------------')
