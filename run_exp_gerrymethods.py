import geopandas as gpd
import os

from gerrysort.model import GerrySort

start_from = 10

# Set amount of simulation runs per fixed control per fixed experiment
runs = 15

# Set params
# states = ["MN", "WI", "MI", "PA", "GA", "TX"]
states = ["GA", "WI"]
election='PRES20'
max_iters = 4


npops = {'MN': 5800, 'WI': 5900, 'MI': 10000, 'PA': 13000, 'GA': 11000, 'TX': 30500}
sorting_space = [True, False, True]
gerrymandering_space = [False, True, True]

initial_controls = ['Democrats']
# initial_controls = ['Model']

tolerance = 0.5
beta = 100.0
ensemble_size = 250
epsilon = 0.01
sigma = 0.0
n_moving_options = 10
moving_cooldown = 0
distance_decay = 0.0
capacity_mul = 1.0

output_path = 'results/experiments/gerry_methods/250tilted_run/'

for i, state in enumerate(states):
    print(f'CONDUCTING EXPERIMENTS FOR {state}')
    data = gpd.read_file(f'data/processed/{state}.geojson')
    npop = npops[state]

    for initial_control in initial_controls:
        print(f'FIXED CONTROL IN FAVOR OF: {initial_control}')
        if initial_control == 'Model':
            control_rule = 'CONGDIST'
            # control_rule = 'STATELEG'
        else:
            control_rule = 'FIXED'

        for exp in range(3):
            if exp == 0 or exp == 1:
                continue
            sorting = sorting_space[exp]
            gerrymandering = gerrymandering_space[exp]
            print(f'\tEXPERIMENT {exp}/2 | (Sorting: {sorting}, Gerrymandering: {gerrymandering})')            
            for run in range(start_from, start_from+runs):
                print(f'\t\tRUN {run}/{start_from+runs-1}')
                model = GerrySort(
                    state=state,
                    data=data,
                    max_iters=max_iters,
                    npop=npop,
                    sorting=sorting,
                    gerrymandering=gerrymandering,
                    control_rule=control_rule,
                    initial_control=initial_control,
                    tolerance=tolerance,
                    beta=beta,
                    ensemble_size=ensemble_size,
                    epsilon=epsilon,
                    sigma=sigma,
                    n_moving_options=n_moving_options,
                    moving_cooldown=moving_cooldown,
                    distance_decay=distance_decay,
                    capacity_mul=capacity_mul
                )
                model.run_model()
                
                # Save model data
                model_data = model.datacollector.get_model_vars_dataframe()
                model_data.to_csv(os.path.join(output_path, f'{state}_{initial_control}_{control_rule}_{exp}_{run}.csv'), index=False)
                
                # Save param configuration
                params_name = os.path.join(output_path, f'{state}_{initial_control}_{control_rule}_{exp}_{run}_params.txt')
                with open(params_name, 'w') as f:
                    f.write(f'State: {state}\n')
                    f.write(f'Experiment: {exp}\n')
                    f.write(f'Run: {run}\n')
                    f.write(f'Params:\n')
                    f.write(f'\tMax Iters: {max_iters}\n')
                    f.write(f'\tNpop: {npop}\n')
                    f.write(f'\tSorting: {sorting}\n')
                    f.write(f'\tGerrymandering: {gerrymandering}\n')
                    f.write(f'\tControl Rule: {control_rule}\n')
                    f.write(f'\tInitial Control: {initial_control}\n')
                    f.write(f'\tTolerance: {tolerance}\n')
                    f.write(f'\tBeta: {beta}\n')
                    f.write(f'\tEnsemble Size: {ensemble_size}\n')
                    f.write(f'\tEpsilon: {epsilon}\n')
                    f.write(f'\tSigma: {sigma}\n')
                    f.write(f'\tN Moving Options: {n_moving_options}\n')
                    f.write(f'\tMoving Cooldown: {moving_cooldown}\n')
                    f.write(f'\tDistance Decay: {distance_decay}\n')
                    f.write(f'\tCapacity Mul: {capacity_mul}')

    print(f'FINISHED EXPERIMENTS FOR {state}')
    print('-----------------------------------')
            
