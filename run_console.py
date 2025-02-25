import geopandas as gpd
import os

from gerrysort.model import GerrySort

# Define the model wrapper for GerrySort (same as before)
def gerrysort_model(state, params, data, save=False):
    """
    Wrapper function to run the GerrySort model with sampled parameters.
    """
    # Set fixed parameters
    npops = {'MN': 5800, 'WI': 5900, 'MI': 10000, 'PA': 13000, 'GA': 11000, 'TX': 30500}
    npop = npops[state]
    print_output = True
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
    model_data = model.datacollector.get_model_vars_dataframe()
    if save:
        # Save model data for this run
        model_data_filename = 'model_data_single_run.csv'
        model_data.to_csv(model_data_filename, index=False)
        
    return model_data

state = 'MN'
data = gpd.read_file(f'data/processed/{state}.geojson')
params = {
    'sorting': True,
    'gerrymandering': True,
    'control_rule': 'CONGDIST',
    'initial_control': 'Model',
    'tolerance': 0.5,
    'beta': 200.0,
    'ensemble_size': 250,
    'sigma': 0.01,
    'n_moving_options': 10,
    'distance_decay': 0.0,
    'capacity_mul': 1.0
}

model_data = gerrysort_model(state, params, data)
