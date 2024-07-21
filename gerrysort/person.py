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
        Initialize person agent.
        '''
        super().__init__(unique_id, model, geometry, crs)
        self.is_red = is_red
        self.district_id = district_id
        self.county_id = county_id
        self.utility = 0
        self.last_moved = float('inf')

    @property
    def is_unhappy(self):
        self.update_utility()
        return self.utility < self.model.tolarence

    def calculate_utility(self, county_id, A=1, alpha=(1, 1, 1, 1)): 
        # Party affilliation matching county party majority
        county = self.model.space.get_county_by_id(county_id)
        if self.is_red and county.red_pct > 0.5:
            X1 = 1
        elif not self.is_red and county.red_pct < 0.5:
            X1 = 1
        else:
            X1 = 0

        # Party affilliation matching district party majority
        district = self.model.space.get_district_by_id(self.district_id)
        if self.is_red and district.red_pct > 0.5:
            X2 = 1
        elif not self.is_red and district.red_pct < 0.5:
            X2 = 1
        else:
            X2 = 0

        # Urbanicity matching county urbanicity
        if self.is_red and county.RUCACAT == 'rural':
            X3 = 1
        elif self.is_red and county.RUCACAT == 'small_town':
            X3 = 0.5
        elif not self.is_red and county.RUCACAT == 'urban':
            X3 = 1
        elif not self.is_red and county.RUCACAT == 'large_town':
            X3 = 0.5
        else:
            X3 = 0

        # Reward/penalize capacity 
        if county.num_people < county.capacity:
            X4 = 1
        else:
            X4 = 0

        # Return utility
        a1, a2, a3, a4 = alpha
        utility = A * (X1**a1 * X2**a2 * X3**a3) * X4
        return utility

    def update_utility(self):
        self.utility = self.calculate_utility(self.county_id)
        # print(self.utility)

    def calculate_delta_U(self, U_new, U_current):
        """
        Calculate the change in utility for moving from current location to a new location.

        U_new: utility value of the new location
        U_current: utility value of the current location
        """
        return U_new - U_current

    def calculate_probabilities(self, U_current, potential_utilities, beta):
        """
        Calculate the probabilities of moving to each potential new location.

        U_current: utility value of the current location
        potential_utilities: list of utility values for each potential new location
        beta: temperature parameter
        """
        delta_U = np.array([self.calculate_delta_U(U_new, U_current) for U_new in potential_utilities])
        exp_values = np.exp(beta * delta_U)
        probabilities = exp_values / np.sum(exp_values)
        return probabilities

    def simulate_movement(self, moving_options, U_current, potential_utilities, beta):
        """
        Simulate the movement process for a household.

        U_current: utility value of the current location
        potential_utilities: list of utility values for each potential new location
        beta: temperature parameter
        """
        probabilities = self.calculate_probabilities(U_current, potential_utilities, beta)
        chosen_index = np.random.choice(len(potential_utilities), p=probabilities)

        # Move to chosen location
        self.model.space.remove_person_from_county(self)
        self.model.space.add_person_to_county(self, county_id=moving_options['county_id'][chosen_index], new_position=moving_options['position'][chosen_index])
        self.last_moved = 0
        print("Utility: ", self.utility)

        return potential_utilities[chosen_index]

    def sort(self):
        moving_options = {
            'county_id': [],
            'utility': [],
            'position': []
        }

        # Evaluate potential moving options
        for i in range(self.model.n_moving_options):
            # Get a random county
            random_county_id = self.model.space.get_random_county_id()
            random_county = self.model.space.get_county_by_id(random_county_id)

            # Calculate distance to new location
            new_location = random_county.random_point()
            MAX_DIST = 475 # normalize distance by max distance (MN: 475 miles)
            distance = great_circle((self.geometry.y, self.geometry.x), (new_location.y, new_location.x)).miles / MAX_DIST
            
            # Calculate discounted utility
            random_county_utility = self.calculate_utility(random_county_id)
            # discounted_utility = random_county_utility * (self.model.distance_decay * (1 - distance))

            # Store moving options
            moving_options['county_id'].append(random_county_id)
            moving_options['position'].append(new_location)
            moving_options['utility'].append(random_county_utility)


        current_utility = self.utility
        potential_utilities = moving_options['utility']
        beta = self.model.beta
        
        # Simulate movement
        new_utility = self.simulate_movement(moving_options, current_utility, potential_utilities, beta)

    def step(self):
        # Update agent's utility
        self.update_utility()

        if self.model.sorting:
            # Check if utility is below threshold and cooldown has passed
            if self.is_unhappy and self.model.moving_cooldown < self.last_moved:
                self.sort()
            else:
                self.last_moved += 1