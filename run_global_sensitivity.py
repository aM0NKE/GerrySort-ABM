import numpy as np
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from SALib.sample import sobol as sobel_sample
from SALib.analyze import sobol as sobol_analyze
import os
import json
from tqdm import tqdm

from gerrysort.model import GerrySort


# Define the model wrapper for GerrySort
def gerrysort_model(state, params, data, run_id, output_dir):
    """
    Wrapper function to run the GerrySort model with sampled parameters.
    """
    # Set fixed parameters
    npops = {'MN': 5800, 'WI': 5900, 'MI': 10000, 'PA': 13000, 'GA': 11000, 'TX': 30500}
    npop = npops[state]
    print_output = False
    vis_level = None
    data = data
    election = 'PRES20'
    sorting = True
    gerrymandering = True
    control_rule = 'FIXED'
    initial_control = 'Republicans'
    max_iters = 4
    epsilon = 0.01

    # Extract parameters
    tolerance, beta, ensemble_size, sigma, n_moving_options, distance_decay, capacity_mul = params

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
        tolerance=float(tolerance),
        beta=float(beta),
        ensemble_size=int(ensemble_size),
        epsilon=float(epsilon),
        sigma=float(sigma),
        n_moving_options=int(n_moving_options),
        distance_decay=float(distance_decay),
        capacity_mul=float(capacity_mul)
    )

    # Run the model and extract the output of interest
    model.run_model()

    # Save model data for this run
    model_data = model.datacollector.get_model_vars_dataframe()
    model_data_filename = os.path.join(output_dir, f'model_data_{run_id}.csv')
    model_data.to_csv(model_data_filename, index=False)
    return model_data

state = 'GA'
data = gpd.read_file(f'data/processed/{state}.geojson')
sample_size = 16

output_dir = f'results/sensitivity_analysis/global/{state}_{sample_size}_FIXED_REP_global_results'
os.makedirs(output_dir, exist_ok=True)

# Define the problem
problem = {
    'num_vars': 7,
    'names': [
        'tolerance', 'beta', 'ensemble_size', 
        'sigma', 'n_moving_options', 'distance_decay', 'capacity_mul'
    ],
    'bounds': [
        [0.0, 1.0],  # tolerance
        [0.0, 200.0],  # beta
        [50, 500],  # ensemble_size
        [0.001, 0.1],  # sigma
        [1, 20],  # n_moving_options
        [0.0, 1.0],  # distance_decay
        [0.9, 1.1]  # capacity_mul
    ]
}

# Load or save parameter space
if not os.path.exists(os.path.join(output_dir, 'parameter_space.csv')):
    # Generate samples using Sobol Sequences
    param_values = sobel_sample.sample(problem, sample_size)
    # Convert sampled parameter values to a DataFrame for easier plotting
    param_df = pd.DataFrame(param_values, columns=problem['names'])
    param_df.to_csv(os.path.join(output_dir, 'parameter_space.csv'), index=False)
    print(f"Parameter space saved to {output_dir}")
else:
    param_df = pd.read_csv(os.path.join(output_dir, 'parameter_space.csv'))
    param_values = param_df.values
    print(f"Parameter space loaded from {output_dir}")

# Plot pairwise scatter plots of the parameter space
def plot_parameter_space(param_df, filename):
    """
    Plots pairwise scatter plots of the sampled parameter space.
    """
    # Use Seaborn's pairplot for pairwise scatter plots
    sns.set_theme(style="ticks")
    g = sns.pairplot(param_df, diag_kind="kde", corner=True)
    g.figure.suptitle("Pairwise Scatter Plots of Sampled Parameter Space", y=1.02)
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
# Save parameter space plots
param_space_filename = os.path.join(output_dir, 'parameter_space.png')
plot_parameter_space(param_df, param_space_filename)
print(f"Parameter space plots saved to {param_space_filename}")

# Run the model for each set of parameters and save model data
for run_id, params in enumerate(tqdm(param_values)):
    output = gerrysort_model(state, params, data, run_id, output_dir)
