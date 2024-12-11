from gerrysort.model import GerrySort
import geopandas as gpd

start_from = 0

# Set amount of simulation runs per fixed control per fixed experiment
runs = 10

# Set params
# states = ["MN", "WI", "MI", "PA", "GA", "TX"]
states = ["TX"]
election='PRES20'
max_iters = 4

# npop_space = [5800, 5900, 10000, 13000, 11000, 30500]
npop_space = [30500]
sorting_space = [True, False, True]
gerrymandering_space = [False, True, True]

initial_controls = ['Model', 'Democrats', 'Republicans', 'Fair']
tolarence = 0.5
beta = 100.0
ensemble_size = 250
epsilon = 0.10
sigma = 0.0
n_moving_options = 5
moving_cooldown = 0
distance_decay = 0.0
capacity_mul = 1.0

for i, state in enumerate(states):
    print(f'CONDUCTING EXPERIMENTS FOR {state}')
    data = gpd.read_file(f'data/processed/{state}.geojson')
    npop = npop_space[i]

    for initial_control in initial_controls:
        print(f'FIXED CONTROL IN FAVOR OF: {initial_control}')
        if initial_control == 'Model':
            control_rule = 'CONGDIST'
        else:
            control_rule = 'FIXED'

        for exp in range(3):
            if exp != 2:
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
                    tolarence=tolarence,
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
                model_data.to_csv(f'results/pilot2/{state}/{state}_{initial_control}_{exp}_{run}.csv', index=False)
                # Save param configuration
                with open(f'results/pilot2/{state}/{state}_{initial_control}_{exp}_{run}_params.txt', 'w') as f:
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
                    f.write(f'\tTolarence: {tolarence}\n')
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
            
