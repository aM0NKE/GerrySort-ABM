import geopandas as gpd
import os

from gerrysort.model import GerrySort

# Define the model wrapper for GerrySort (same as before)
def gerrysort_model(state, params, data, run_id, output_dir):
    """
    Wrapper function to run the GerrySort model with sampled parameters.
    """
    # Set fixed parameters
    npops = {'MN': 5800, 'WI': 5900, 'MI': 10000, 'PA': 13000, 'GA': 11000, 'TX': 30500}
    npop = npops[state]
    print_output = False
    vis_level = None
    election = 'PRES20'
    max_iters = 4
    epsilon = 0.01

    # Extract parameter values
    params_values = list(params.values())

    # Initialize the GerrySort model
    model = GerrySort(
        state=state,
        print_output=print_output,
        vis_level=vis_level,
        data=data,
        election=election,
        max_iters=int(max_iters),
        npop=int(npop),
        sorting=bool(params_values[0]),
        gerrymandering=bool(params_values[1]),
        control_rule=params_values[2],
        initial_control=params_values[3],
        tolerance=float(params_values[4]),
        beta=float(params_values[5]),
        ensemble_size=int(params_values[6]),
        epsilon=float(epsilon),
        sigma=float(params_values[7]),
        n_moving_options=int(params_values[8]),
        distance_decay=float(params_values[9]),
        capacity_mul=float(params_values[10])
    )

    # Run the model and extract the output of interest
    model.run_model()

    # Save model data for this run
    model_data = model.datacollector.get_model_vars_dataframe()
    model_data_filename = os.path.join(output_dir, f'model_data_{run_id}.csv')
    model_data.to_csv(model_data_filename, index=False)
    
    return model_data

start_from = 0
runs = 1

states = ["GA", "WI"]
gerrymandering_space = [False, True, True]
sorting_space = [True, False, True]
initial_controls = ['Democrats', 'Republicans', 'Fair', 'Model']

params = {
    'sorting': None,
    'gerrymandering': None,
    'control_rule': None,
    'initial_control': None,
    'tolerance': 0.5,
    'beta': 200.0,
    'ensemble_size': 250,
    'sigma': 0.01,
    'n_moving_options': 10,
    'distance_decay': 0.0,
    'capacity_mul': 1.0
}

for state in states:
    print(f'CONDUCTING EXPERIMENTS FOR {state}')
    output_dir = f'results/experiments/baseline/{state}'
    os.makedirs(output_dir, exist_ok=True)

    data = gpd.read_file(f'data/processed/{state}.geojson')
    for initial_control in initial_controls:
        if initial_control == 'Model':
            params['control_rule'] = 'CONGDIST' # Alternative: 'STATELEG'
            print(f'CONTROL RULE: {params["control_rule"]}')
        else:
            params['control_rule'] = 'FIXED'
            print(f'FIXED CONTROL IN FAVOR OF: {initial_control}')
        params['initial_control'] = initial_control

        for exp in range(3):
            params['sorting'] = sorting_space[exp]
            params['gerrymandering'] = gerrymandering_space[exp]
            print(f'\tEXPERIMENT {exp}/2 | (Sorting: {params["sorting"]}, Gerrymandering: {params["gerrymandering"]})')
            
            for run in range(start_from, start_from+runs):
                print(f'\t\tRUN {run}/{start_from+runs-1}')
                # Generate a unique run ID
                run_id = f'{initial_control}_exp_{exp}_run_{run}'
                # Run the model
                model_data = gerrysort_model(state, params, data, run_id, output_dir)
                # Save param configuration
                params_filename = os.path.join(output_dir, f'params_{run_id}.txt')
                with open(params_filename, 'w') as f:
                    f.write(str(params))

    print(f'FINISHED EXPERIMENTS FOR {state}')
    print('-----------------------------------')

