import numpy as np
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import os
from tqdm import tqdm

from gerrysort.model import GerrySort

# Define the model wrapper for GerrySort (same as before)
def gerrysort_model(state, params, data, run_id, output_dir):
    """
    Wrapper function to run the GerrySort model with sampled parameters.
    """
    # Unpack parameters
    npops = {'MN': 5800, 'WI': 5900, 'MI': 10000, 'PA': 13000, 'GA': 11000, 'TX': 30500}
    npop = npops[state]
    print_output = False
    vis_level = None
    data = data
    election = 'PRES20'
    sorting = True
    gerrymandering = True
    control_rule = 'CONGDIST'
    initial_control = 'Model'
    max_iters = 4
    epsilon = 0.01

    # Initialize the GerrySort model
    model = GerrySort(
        state=state,
        print_output=print_output,
        vis_level=vis_level,
        data=data,
        election=election,
        max_iters=int(max_iters),
        npop=int(npop),
        sorting=bool(sorting),
        gerrymandering=bool(gerrymandering),
        control_rule=control_rule,
        initial_control=initial_control,
        tolerance=float(params[0]),
        beta=float(params[1]),
        ensemble_size=int(params[2]),
        epsilon=float(epsilon),
        sigma=float(params[3]),
        n_moving_options=int(params[4]),
        distance_decay=float(params[5]),
        capacity_mul=float(params[6])
    )

    # Run the model and extract the output of interest
    model.run_model()

    # Save model data for this run
    model_data = model.datacollector.get_model_vars_dataframe()
    model_data_filename = os.path.join(output_dir, f'model_data_{run_id}.csv')
    model_data.to_csv(model_data_filename, index=False)
    return model_data

# Main script
states = ['GA']
start_from = 19
runs = 1

# Define the baseline parameters
baseline_params = {
    'tolerance': 0.5,
    'beta': 200.0,
    'ensemble_size': 250,
    'sigma': 0.01,
    'n_moving_options': 10,
    'distance_decay': 0.0,
    'capacity_mul': 1.0
}

# Define the parameter ranges for OFAT analysis
param_ranges = {
    'tolerance': [0.0, 0.25, 0.5, 0.75, 1.0],
    'beta': [0.0, 50.0, 100.0, 150.0, 200.0],
    'ensemble_size': [50, 100, 250, 500],
    'sigma': [0.001, 0.01, .1],
    'n_moving_options': [5, 10, 15, 20],
    'distance_decay': [0.0, 0.25, 0.5, 1.0],
    'capacity_mul': [0.9, 1.0, 1.1]
}

for state in states:
    # Create output directory for OFAT results
    output_dir = f'results/sensitivity_analysis/local/{state}_MODEL'
    os.makedirs(output_dir, exist_ok=True)

    # Load data
    data = gpd.read_file(f'data/processed/{state}.geojson')

    # Perform OFAT sensitivity analysis
    results = {}
    for param_name, param_values in tqdm(param_ranges.items()):
        print(f"Running OFAT analysis for parameter: {param_name}")
        for value in param_values:
            # Run the model `runs` times for each parameter value
            for run in range(runs):
                # Create a copy of the baseline parameters
                params = list(baseline_params.values())
                # Replace the current parameter's value
                param_index = list(baseline_params.keys()).index(param_name)
                params[param_index] = value
                # Generate a unique run ID
                run_id = f"{param_name}_{value}_run_{run+start_from}"
                # Run the model
                model_data = gerrysort_model(state, params, data, run_id, output_dir)
