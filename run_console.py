from gerrysort.model import GerrySort

import geopandas as gpd
import os

# Set number of experiment trials
trials = 1

# Set the parameters for the model
state = 'MN'
max_iters = 5
npop=5800               # 5,800,000 people in MN
sorting=True
gerrymandering=True
control_rule='CONGDIST'
initial_control='Data'
tolarence=0.5
beta=100.0              # 0 means that moving decision is totally random
ensemble_size=3
epsilon=0.1
n_moving_options=5
moving_cooldown=0
distance_decay=0.0      # 0.0 means that distance will not affect utility of moving options
capacity_mul=1.0

# Open the data
data = gpd.read_file(os.path.join('gerrysort/data/MN/MN_precincts_election_results_2020.geojson'))

for i in range(trials):
    print(f'EXPERIMENT {i + 1}/{trials} STARTED...')
    model = GerrySort(
        state=state,
        data=data,
        max_iters=max_iters,
        npop=npop,
        sorting=sorting,
        gerrymandering=gerrymandering,
        control_rule=control_rule,
        initial_control=initial_control,
        tolarence=tolarence,
        beta=beta,
        ensemble_size=ensemble_size,
        epsilon=epsilon,
        n_moving_options=n_moving_options,
        moving_cooldown=moving_cooldown,
        distance_decay=distance_decay,
        capacity_mul=capacity_mul
    )
    model.run_model()
    print(f'EXPERIMENT {i + 1}/{trials} FINISHED!\n')
