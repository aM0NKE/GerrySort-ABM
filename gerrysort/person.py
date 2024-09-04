import mesa_geo as mg
import numpy as np
from geopy.distance import great_circle

class PersonAgent(mg.GeoAgent):
    is_red: bool
    district_id: str
    county_id: str
    utility: float
    is_unhappy: bool

    def __init__(self, unique_id, model, geometry, crs, is_red, district_id, county_id):
        '''
        Initialize the person agent.

        Attributes:
            unique_id (int): unique identifier of the agent
            model (GerrySort): model the agent is part of
            geometry (tuple): location coordinates (x, y)
            is_red (bool): agent's party affiliation
            district_id (str): electoral district name agent is located in
            county_id (str): county name agent is located in
            utility (float): utility value of the agent
            last_moved (int): counter of the last time step the agent relocated
             
        '''
        super().__init__(unique_id, model, geometry, crs)
        self.is_red = is_red
        self.district_id = district_id
        self.county_id = county_id
        self.utility = 0
        self.last_moved = float('inf')

    @property
    def is_unhappy(self):
        '''
        Returns false when agent is unhappy.
        '''
        return self.utility < self.model.tolarence
    
    def calculate_utility(self, county_id, district_id, A=1, alpha=(1, 1, 1, 1)): 
        '''
        Recalculates the agent's utility score.
        
        Formula: A * (X1**a1 * X2**a2 * X3**a3) * X4

        Variables:
            X1: party affiliation match
            X2: electoral district match
            X3: county match
            X4: capacity penalty
        '''
        # Party affilliation matching county party majority
        county = self.model.space.get_county_by_id(county_id)
        if self.is_red and county.red_pct > 0.5:
            X1 = 1
        elif not self.is_red and county.red_pct < 0.5:
            X1 = 1
        else:
            X1 = 0.1

        # Party affilliation matching district party majority
        district = self.model.space.get_district_by_id(district_id)
        if self.is_red and district.red_pct > 0.5:
            X2 = 1
        elif not self.is_red and district.red_pct < 0.5:
            X2 = 1
        else:
            X2 = 0.1

        # Urbanicity matching county urbanicity
        if self.is_red and county.RUCACAT == 'rural':
            X3 = 1
        elif self.is_red and county.RUCACAT == 'small_town':
            X3 = 0.5
        elif self.is_red and county.RUCACAT == 'large_town':
            X3 = 0.25
        elif not self.is_red and county.RUCACAT == 'urban':
            X3 = 1
        elif not self.is_red and county.RUCACAT == 'large_town':
            X3 = 0.5
        elif not self.is_red and county.RUCACAT == 'small_town':
            X3 = 0.25
        else:
            X3 = .1

        # Reward/penalize capacity 
        if county.num_people < county.capacity:
            X4 = 1
        else:
            X4 = 0.1

        # Return utility
        a1, a2, a3, a4 = alpha
        utility = A * (X1**a1 * X2**a2 * X3**a3) * X4
        return utility

    def update_utility(self):
        self.utility = self.calculate_utility(self.county_id, self.district_id)
        if self.model.console: print('Updated utility: ', self.unique_id, self.is_red, self.utility)

    def calculate_delta_U(self, U_new, U_current):
        """
        Calculates the change in utility for moving from current location to a new location.

        U_new: utility value of the new location
        U_current: utility value of the current location
        """
        return U_new - U_current

    def calculate_probabilities(self, U_current, potential_utilities):
        """
        Calculates the probabilities of moving to each potential new location.

        U_current: utility value of the current location
        potential_utilities: list of utility values for each potential new location
        beta: temperature parameter
        """
        delta_U = np.array([self.calculate_delta_U(U_new, U_current) for U_new in potential_utilities])
        exp_values = np.exp(self.model.beta * delta_U)
        probabilities = exp_values / np.sum(exp_values)
        return probabilities

    def simulate_movement(self, moving_options, U_current):
        """
        Simulates the movement process for a household.

        moving_options: dictionary storing id, utility, and position of potential moving options
        U_current: utility value of the current location
        """
        probabilities = self.calculate_probabilities(U_current, moving_options['utility'])
        chosen_index = np.random.choice(len(moving_options['utility']), p=probabilities)

        # Move to chosen location
        self.model.space.remove_person_from_county(self)
        self.model.space.add_person_to_county(self, new_county_id=moving_options['county_id'][chosen_index], new_position=moving_options['position'][chosen_index])
        self.last_moved = 0
        return moving_options['utility'][chosen_index]

    def sort(self):
        '''
        Simulates the self-sorting phenomonon.
        '''
        # Create dictionary with potental moving options
        moving_options = {
            'county_id': [],
            'district_id': [],
            'utility': [],
            'position': []
        }

        # Consider an x number of random potential moving options
        for i in range(self.model.n_moving_options):
            # Draw a random county id and find corresponding district
            random_county_id = self.model.space.get_random_county_id()
            random_district_id = self.model.space.county_district_map[random_county_id]

            # Return random county instance
            random_county = self.model.space.get_county_by_id(random_county_id)
            new_location = random_county.random_point() # Find a random point within the county

            # Calculate discounted utility
            random_county_utility = self.calculate_utility(random_county_id, random_district_id)
            # TODO: Do we consider a discounted utility based on distance to potential relocation spot?
            # MAX_DIST = 475 # normalize distance by max distance (MN: 475 miles)
            # distance = great_circle((self.geometry.y, self.geometry.x), (new_location.y, new_location.x)).miles / MAX_DIST
            # discounted_utility = random_county_utility * (self.model.distance_decay * (1 - distance))

            # Store moving options
            moving_options['county_id'].append(random_county_id)
            moving_options['district_id'].append(random_district_id)
            moving_options['position'].append(new_location)
            moving_options['utility'].append(random_county_utility)

        # Simulate movement
        new_utility = self.simulate_movement(moving_options, self.utility)