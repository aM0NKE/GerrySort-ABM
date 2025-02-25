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
def gerrysort_model(params, data, run_id, output_dir):
    """
    Wrapper function to run the GerrySort model with sampled parameters.
    """
    # Unpack parameters
    state = 'MN'  # Fixed for this example
    npop = 5800
    print_output = False
    vis_level = None
    data = data
    election = 'PRES20'
    sorting = True
    gerrymandering = True
    control_rule = 'CONGDIST'
    initial_control = 'Model'
    max_iters = 4

    moving_cooldown = 0
    capacity_mul = 1.0
    epsilon = 0.01

    # tolerance, beta, ensemble_size, epsilon, sigma, n_moving_options, moving_cooldown, distance_decay, capacity_mul = params
    tolerance, beta, ensemble_size, sigma, n_moving_options, distance_decay = params

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
        moving_cooldown=int(moving_cooldown),
        distance_decay=float(distance_decay),
        capacity_mul=float(capacity_mul)
    )

    # Run the model and extract the output of interest
    model.run_model()

    # Save model data for this run
    model_data = model.datacollector.get_model_vars_dataframe()
    model_data_filename = os.path.join(output_dir, f'model_data_run_{run_id}.csv')
    model_data.to_csv(model_data_filename, index=False)

    # Return output variable
    output = model.rep_congdist_seats
    return output


# Define the problem
problem = {
    'num_vars': 6,
    'names': [
        'tolerance', 'beta', 'ensemble_size', 
        'sigma', 'n_moving_options', 'distance_decay'
    ],
    'bounds': [
        # [1000, 10000],  # npop
        [0.1, 1.0],  # tolerance
        [0.0, 200.0],  # beta
        [10, 250],  # ensemble_size
        # [0.01, 0.1],  # epsilon
        [0.01, 0.1],  # sigma
        [1, 20],  # n_moving_options
        # [0, 4],  # moving_cooldown
        [0.0, 1.0],  # distance_decay
        # [0.5, 2.0]  # capacity_mul
    ]
}

# Save parameter space plots
output_dir = 'MN_256_sensitivity_analysis_results'
os.makedirs(output_dir, exist_ok=True)

if not os.path.exists(os.path.join(output_dir, 'parameter_space.csv')):
    # Generate samples using Sobol Sequences
    param_values = sobel_sample.sample(problem, 16)
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
    sns.set(style="ticks")
    g = sns.pairplot(param_df, diag_kind="kde", corner=True)
    g.fig.suptitle("Pairwise Scatter Plots of Sampled Parameter Space", y=1.02)
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
# Save parameter space plots
param_space_filename = os.path.join(output_dir, 'parameter_space.png')
plot_parameter_space(param_df, param_space_filename)
print(f"Parameter space plots saved to {param_space_filename}")


# Run the model for each set of parameters and save model data
Y = []
data = gpd.read_file(f'data/processed/MN.geojson')
for run_id, params in enumerate(tqdm(param_values)):
    output = gerrysort_model(params, data, run_id, output_dir)
    Y.append(output)
Y = np.array(Y)

# Y = []
# # Open moodel_data_runs and create Y
# for run_id, params in enumerate(tqdm(param_values)):
#     model_data = pd.read_csv(os.path.join(output_dir, f'model_data_run_{run_id}.csv'))
#     Y.append(model_data['efficiency_gap'].values[-1])
# Y = np.array(Y)

# Perform Sobol sensitivity analysis
Si = sobol_analyze.analyze(problem, Y, print_to_console=True)

# Save sensitivity analysis results to a JSON file
def save_sensitivity_results(Si, problem, filename):
    """
    Saves sensitivity analysis results to a JSON file.
    """
    results = {
        'problem': problem,
        'S1': Si['S1'].tolist(),
        'S1_conf': Si['S1_conf'].tolist(),
        'ST': Si['ST'].tolist(),
        'ST_conf': Si['ST_conf'].tolist(),
    }
    with open(filename, 'w') as f:
        json.dump(results, f, indent=4)
# Save sensitivity results
sensitivity_json_filename = os.path.join(output_dir, 'sensitivity_results.json')
save_sensitivity_results(Si, problem, sensitivity_json_filename)
print(f"Sensitivity analysis results saved to {sensitivity_json_filename}")


# Plotting the results
def plot_sensitivity_indices(Si, problem, filename):
    fig, ax = plt.subplots(1, 2, figsize=(12, 6))

    # First-order indices
    ax[0].bar(problem['names'], Si['S1'], yerr=Si['S1_conf'], capsize=5)
    ax[0].set_title('First-order Sobol indices')
    ax[0].set_ylabel('Sensitivity index')

    # Total-order indices
    ax[1].bar(problem['names'], Si['ST'], yerr=Si['ST_conf'], capsize=5)
    ax[1].set_title('Total-order Sobol indices')
    ax[1].set_ylabel('Sensitivity index')

    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
# Save sensitivity analysis plots
sensitivity_filename = os.path.join(output_dir, 'sobol_indices.png')
plot_sensitivity_indices(Si, problem, sensitivity_filename)
print(f"Sensitivity analysis plots saved to {sensitivity_filename}")
