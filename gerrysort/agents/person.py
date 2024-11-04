import mesa_geo as mg
import numpy as np
import random
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
        self.is_unhappy = None
        self.district_id = district_id
        self.county_id = county_id
        self.utility = 0
        self.last_moved = float('inf')
    
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
            X1 = 0.5

        # Party affilliation matching district party majority
        district = self.model.space.get_district_by_id(district_id)
        if self.is_red and district.red_pct > 0.5:
            X2 = 1
        elif not self.is_red and district.red_pct < 0.5:
            X2 = 1
        else:
            X2 = 0.75

        # Urbanicity matching county urbanicity
        if self.is_red and county.RUCACAT == 'rural':
            X3 = 1
        elif self.is_red and county.RUCACAT == 'small_town':
            X3 = 1
        elif self.is_red and county.RUCACAT == 'large_town':
            X3 = 0.5
        elif not self.is_red and county.RUCACAT == 'urban':
            X3 = 1
        elif not self.is_red and county.RUCACAT == 'large_town':
            X3 = 1
        elif not self.is_red and county.RUCACAT == 'small_town':
            X3 = 0.5
        else:
            X3 = .25

        # Return utility
        a1, a2, a3, a4 = alpha
        utility = A * (X1**a1 * X2**a2 * X3**a3)
        return utility

    def update_utility(self):
        '''
        Updates the agent's utility score and checks if it is happy/unhappy.
        '''
        self.utility = self.calculate_utility(self.county_id, self.district_id)
        self.is_unhappy = self.utility < self.model.tolarence
        # print('Utility: ', self.utility, 'Is Rep: ', self.is_red, 'Unhappy: ', self.is_unhappy, 'Tolerance: ', self.model.tolarence)

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
        potential_utilities = [option['utility'] for option in moving_options.values()]
        probabilities = self.calculate_probabilities(U_current, potential_utilities)
        
        chosen_key = np.random.choice(list(moving_options.keys()), p=probabilities)
        chosen_option = moving_options[chosen_key]

        if chosen_key != '-1':
            self.model.space.remove_person_from_county(self)
            self.model.space.add_person_to_county(
                    self,
                    new_county_id=chosen_option['county_id'],
                    new_position=chosen_option['position']
                )            
            self.last_moved = 0
            self.model.total_moves += 1

        # if self.model.debug:
        #     print('\t\tPotential Utilities: ', potential_utilities)
        #     print('\t\tProbabilities: ', probabilities)
        #     print('\t\tChosen Key: ', chosen_key)

    def sort(self):
        '''
        Simulates the self-sorting phenomonon.
        '''
        # Create dictionary with potental moving options
        moving_options = {}
        moving_options['-1'] = {
            'county_id': self.county_id,
            'district_id': self.district_id,
            'utility': self.utility,
            'position': self.geometry
        }

        # Consider an x number of random potential moving options
        option_cnt = 0
        while option_cnt < self.model.n_moving_options:
            # Select random county (not at capacity)
            not_full_capacity_counties = [county for county in self.model.counties if county.num_people < county.capacity and county.unique_id != self.county_id]
            # Filter out current county
            random_county = random.choice(not_full_capacity_counties)

            # Check if county is at capacity
            while random_county.num_people >= random_county.capacity:
                continue
            option_cnt += 1

            # Find random county instance and generate random point in county
            random_district_id = self.model.space.county_district_map[random_county.unique_id]
            new_location = random_county.random_point()

            # Calculate discounted utility
            random_county_utility = self.calculate_utility(random_county.unique_id, random_district_id)
            # TODO: Do we consider a discounted utility based on distance to potential relocation spot?
            MAX_DIST = 475 # normalize distance by max distance (MN: 475 miles) (Used for normalizing distance between 0-1)
            distance = great_circle((self.geometry.y, self.geometry.x), (new_location.y, new_location.x)).miles  / MAX_DIST
            discounted_utility = random_county_utility * (1 - (self.model.distance_decay * distance)) # DONE: Reformulated this! prev: random_county_utility*(distance_decay*(1-distance))

            # Store moving options
            moving_options[f'{option_cnt}'] = {
                'county_id': random_county.unique_id,
                'district_id': random_district_id,
                'utility': discounted_utility,
                'position': new_location
            }
        
        # Simulate movement
        self.simulate_movement(moving_options, self.utility)