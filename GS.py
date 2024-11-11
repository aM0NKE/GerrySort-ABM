from gerrysort.model import GerrySort

import os
import geopandas as gpd
import numpy as np
import matplotlib.pyplot as plt
from tqdm import tqdm

from SALib.analyze.sobol import analyze
from SALib.sample.sobol import sample
from SALib.test_functions import Ishigami


# Set state
state = 'MN'

# Open the data
print(f'Opening {state} data...')
ensemble = gpd.read_file(os.path.join('data/processed_states', state, state + '_CONGDIST_ensemble.geojson'))
initial_plan = gpd.read_file(os.path.join('data/processed_states', state, state + '_CONGDIST_initial.geojson'))
state_leg_map = gpd.read_file(os.path.join('data/processed_states', state, state + '_LEGDIST.geojson'))
state_sen_map = gpd.read_file(os.path.join('data/processed_states', state, state + '_SENDIST.geojson'))
fitness_landscape = gpd.read_file(os.path.join('data/processed_states', state, state + '_FitnessLandscape.geojson'))

# Fixed parameters
max_iters = 3
npop=100               # 5,800,000 people in MN
gerrymandering=True
sorting=True
print(f'Fixed Parameters: max_iters={max_iters}, npop={npop}, gerrymandering={gerrymandering}, sorting={sorting}')

# Sobol space
problem = {
    'num_vars': 7,
    'names': ['tolarence', 'beta', 'n_proposed_maps', 
                'n_moving_options', 'moving_cooldown', 
                'distance_decay', 'capacity_mul'],
    'bounds': [[0.1, 1.0], [0.0, 100.0], [1, 10], 
               [1, 10], [0, 5], 
               [0.1, 1.0], [1.0, 2.0]]
}
param_values = sample(problem, 1)
print(f'Parameter space:\n\tValues:\n{param_values}\n\tShape: {param_values.shape}')

def run_model(params, state, ensemble, initial_plan, state_leg_map, state_sen_map, fitness_landscape, max_iters, npop, gerrymandering, sorting):
    model = GerrySort(
        debug=False,
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
        tolarence=params[0],
        beta=params[1],
        n_proposed_maps=params[2],
        n_moving_options=params[3],
        moving_cooldown=params[4],
        distance_decay=params[5],
        capacity_mul=params[6]
    )

    model.run_model()

    return model.declination


# Y = [run_model(params, state, ensemble, initial_plan, state_leg_map, state_sen_map, fitness_landscape, max_iters, npop, gerrymandering, sorting) for params in tqdm(param_values)]
Y = np.array([run_model(params, state, ensemble, initial_plan, state_leg_map, state_sen_map, fitness_landscape, max_iters, npop, gerrymandering, sorting) for params in tqdm(param_values)])
# Y = Ishigami.evaluate(param_values)
# print(Y, Y.shape, type(Y))

# Perform analysis
Si = analyze(problem, Y, print_to_console=True)

# Extract Sobol indices (first-order and total-order indices)
first_order = Si['S1']
total_order = Si['ST']

