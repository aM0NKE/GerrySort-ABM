import geopandas as gpd
import os

from gerrysort.model import GerrySort

debug = True

# Set number of experiment trials
trials = 1

# Set the parameters for the model
state = 'MI'
max_iters = 5
npop=500               # 5,800,000 people in MN
gerrymandering=True
sorting=True
tolarence=0.5
beta=100.0                # O means that moving decision is totally random
n_proposed_maps=5
n_moving_options=5
moving_cooldown=0
distance_decay=1.0
capacity_mul=1.0

# Open the data
ensemble = gpd.read_file(os.path.join('data/processed_states', state, state + '_CONGDIST_ensemble.geojson'))
initial_plan = gpd.read_file(os.path.join('data/processed_states', state, state + '_CONGDIST_initial.geojson'))
state_leg_map = gpd.read_file(os.path.join('data/processed_states', state, state + '_LEGDIST.geojson'))
state_sen_map = gpd.read_file(os.path.join('data/processed_states', state, state + '_SENDIST.geojson'))
fitness_landscape = gpd.read_file(os.path.join('data/processed_states', state, state + '_FitnessLandscape.geojson'))

for i in range(trials):
    # Create the model
    model = GerrySort(
        debug=debug,
        state=state,
        ensemble=ensemble,
        initial_plan=initial_plan,
        state_leg_map=state_leg_map,
        state_sen_map=state_sen_map,
        fitness_landscape=fitness_landscape,
        max_iters=max_iters,
        npop=npop,
        gerrymandering=gerrymandering,
        sorting=sorting,
        tolarence=tolarence,
        beta=beta,
        n_proposed_maps=n_proposed_maps,
        n_moving_options=n_moving_options,
        moving_cooldown=moving_cooldown,
        distance_decay=distance_decay,
        capacity_mul=capacity_mul
    )

    # Run the model
    model.run_model()

    # Print the results
    print(f'Experiment {i + 1} completed.')
    print('Model converged after: {} iterations'.format(model.iter))
    print('Statistics:')
    print(f'\tUnhappy: {model.unhappy} | Unhappy Red: {model.unhappy_red} | Unhappy Blue: {model.unhappy_blue}')
    print(f'\tHappy: {model.happy} | Happy Red: {model.happy_red} | Happy Blue: {model.happy_blue}')   
    print(f'\tCongressional Seats | Red: {model.red_congressional_seats} | Blue: {model.blue_congressional_seats} | Tied: {model.tied_congressional_seats}')
    print(f'\t\tEfficiency Gap: {model.efficiency_gap}')
    print(f'\t\tMean Median: {model.mean_median}')
    print(f'\t\tDeclination: {model.declination}')
    print(f'\tControl: {model.control} | Projected Margin: {model.projected_margin}')
    print(f'\t\tState House Seats | Red: {model.red_state_house_seats} | Blue: {model.blue_state_house_seats} | Tied: {model.tied_state_house_seats}')
    print(f'\t\tState Senate Seats | Red: {model.red_state_senate_seats} | Blue: {model.blue_state_senate_seats} | Tied: {model.tied_state_senate_seats}')
    print('-----------------------------------\n')
