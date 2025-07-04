import mesa_geo as mg
import numpy as np
import random

class PersonAgent(mg.GeoAgent):
    utility: float
    is_unhappy: bool
    precinct_id: str
    county_id: str
    congdist_id: str
    color: str

    def __init__(self, unique_id, model, geometry, crs, 
                 is_red, precinct_id, county_id, congdist_id):
        super().__init__(unique_id, model, geometry, crs)
        self.utility = 0
        self.is_unhappy = None
        self.precinct_id = precinct_id
        self.county_id = county_id
        self.congdist_id = congdist_id
        self.color = 'Red' if is_red else 'Blue'
    
    def calculate_utility(self, precinct_id, alpha=((1/3), (1/3), (1/3))): 
        '''        
        Formula: A * (X1**a1 * X2**a2 * X3**a3 * X4**a4)

        Variables:
            X1: precinct party majority match (Direct Neighbors)
            X2: county party majority match (Neighborhood)
            X3: urbanicity match (Dems prefer urban, Reps prefer rural)
        '''
        precinct = self.model.space.get_precinct_by_id(precinct_id)
        if self.color == precinct.color:
            X1 = 1
        else:
            X1 = 0

        county = self.model.space.get_county_by_id(precinct.COUNTY_NAME)
        if self.color == county.color:
            X2 = 1
        else:
            X2 = 0
        
        if self.color == 'Red' and county.COUNTY_RUCACAT == 'rural':
            X3 = 1
        elif self.color == 'Red' and county.COUNTY_RUCACAT == 'small_town':
            X3 = 1
        elif self.color == 'Red' and county.COUNTY_RUCACAT == 'large_town':
            X3 = .5
        elif self.color == 'Blue' and county.COUNTY_RUCACAT == 'urban':
            X3 = 1
        elif self.color == 'Blue' and county.COUNTY_RUCACAT == 'large_town':
            X3 = 1
        elif self.color == 'Blue' and county.COUNTY_RUCACAT == 'small_town':
            X3 = .5
        else:
            X3 = 0.25
        
        # Return utility
        a1, a2, a3 = alpha
        utility = X1*a1 + X2*a2 + X3*a3
        return utility

    def calculate_discounted_utility(self, utility, new_location):
        # Compute Euclidean distance in meters
        distance_meters = self.geometry.distance(new_location)

        # Convert meters to miles
        distance_miles = distance_meters * 0.000621371

        # Max distance dictionary (in miles)
        max_dist_dict = {'MN': 475, 'WI': 360, 'MI': 500, 'OH': 300, 'PA': 330, 'MA': 190, 'NC': 500, 'GA': 385, 'LA': 370, 'TX': 805}
        max_dist = max_dist_dict[self.model.state]

        # Calculate normalized distance
        normalized_distance = distance_miles / max_dist

        # Return discounted utility
        return utility * (1 - (self.model.distance_decay * normalized_distance))

    def update_utility(self):
        self.utility = self.calculate_utility(self.precinct_id)
        self.is_unhappy = self.utility < self.model.tolerance

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
        # Calculate probabilities of moving to each potential new location and choose one
        potential_utilities = [option['discounted_utility'] for option in moving_options.values()]
        probabilities = self.calculate_probabilities(U_current, potential_utilities)
        chosen_key = np.random.choice(list(moving_options.keys()), p=probabilities)
        chosen_option = moving_options[chosen_key]
        
        # Move agent to new location if chosen
        if chosen_key != '-1':
            self.model.space.remove_person_from_space(self)
            self.model.space.add_person_to_space(
                    self,
                    new_precinct_id=chosen_option['precinct_id'],
                    new_position=chosen_option['position']
                )            
            self.model.total_moves += 1
        
        # Update agent's utility
        self.utility = chosen_option['utility']

    def sort(self):
        # Create dictionary with potental moving options
        moving_options = {}
        moving_options['-1'] = {
            'position': self.geometry,
            'precinct_id': self.precinct_id,
            'county_id': self.county_id,
            'congdist_id': self.congdist_id,
            'utility': self.utility,
            'discounted_utility': self.utility
        }
        option_cnt = 0
        while option_cnt < self.model.n_moving_options:
            # Find counties that are not at capacity and select one at random
            not_full_capacity_counties = [county for county in self.model.counties if county.num_people < county.capacity and county.unique_id != self.county_id]
            if len(not_full_capacity_counties) == 0:
                break
            new_county = random.choice(not_full_capacity_counties)
            # Make dictionary of TOTPOP for each precinct in the county
            precincts = {precinct: self.model.space.get_precinct_by_id(precinct).TOTPOP for precinct in new_county.precincts}
            # Set all TOTPOP values of nan to 0
            precincts = {k: v if v == v else 0 for k, v in precincts.items()}
            # Make a probability distribution of precincts based on population
            precinct_probs = {precinct: precincts[precinct] / sum(precincts.values()) for precinct in precincts}
            # Pick a random precinct from random county and sample a new location
            new_precinct_id = random.choices(list(precinct_probs.keys()), weights=list(precinct_probs.values()))[0]
            new_precinct = self.model.space.get_precinct_by_id(new_precinct_id)
            new_location = new_precinct.random_point()
            
            # Calculate discounted utility
            utility = self.calculate_utility(new_precinct_id)
            if self.model.distance_decay == 0:
                discounted_utility = utility
            else:
                discounted_utility = self.calculate_discounted_utility(utility, new_location)
            
            # Store moving options
            option_cnt += 1
            moving_options[f'{option_cnt}'] = {
                'position': new_location,
                'precinct_id': new_precinct_id,
                'county_id': new_county.unique_id,
                'congdist_id': self.model.space.precinct_congdist_map[new_precinct_id],
                'utility': utility,
                'discounted_utility': discounted_utility
            }

        # Simulate movement
        self.simulate_movement(moving_options, self.utility)
        