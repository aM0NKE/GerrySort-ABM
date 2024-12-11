
from gerrysort.model import GerrySort
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt
from SALib.sample import sobol_sequence
from SALib.analyze import sobol
from SALib.sample import latin

state = 'MN'
npop = 5800
data = gpd.read_file(f'data/processed/{state}.geojson')

# Define the parameter space for global sensitivity analysis
parameter_space = {
    'num_vars': 5,
    'names': ['tolarence', 'beta', 'ensemble_size', 'epsilon', 'sigma'],
    'bounds': [[0.0, 1.0],  # Tolerance
               [0.0, 100.0],  # Beta
               [50, 250],  # Ensemble Size
               [0.1, 1],  # Epsilon
               [0, 1]]  # Sigma
}

# Outputs to analyze
outputs = ['rep_congdist_seats', 'dem_congdist_seats', 'efficiency_gap', 'declination', 'mean_median']

# Generate samples
problem = parameter_space
param_values = sobol_sequence.sample(4, problem['num_vars'])

# Rescale integer parameters
param_values[:, 1] = np.rint(param_values[:, 1] * (parameter_space['bounds'][1][1] - parameter_space['bounds'][1][0]) + parameter_space['bounds'][1][0])
param_values[:, 2] = np.rint(param_values[:, 2] * (parameter_space['bounds'][2][1] - parameter_space['bounds'][2][0]) + parameter_space['bounds'][2][0])

# Placeholder for simulation results
global_results = {output: [] for output in outputs}

for params in param_values:
    print(f"Running simulation with parameters: {params}")
    model = GerrySort(
        state=state,
        data=data,
        max_iters=1,
        npop=npop,
        sorting=True,
        gerrymandering=True,
        control_rule='FIXED',
        initial_control='Fair',
        tolarence=params[0],
        beta=params[1],
        ensemble_size=int(params[2]),
        epsilon=0.1,
        sigma=params[4],
        n_moving_options=5,
        moving_cooldown=0,
        distance_decay=0.0,
        capacity_mul=1.0
    )
    model.run_model()

    # Collect output variables
    model_data = model.datacollector.get_model_vars_dataframe().iloc[-1]
    for output in outputs:
        global_results[output].append(model_data[output])

    

# Ensure results are in the correct format for Sobol analysis
for output in outputs:
    Y = np.array(global_results[output])

    # Sobol Analysis
    si = sobol.analyze(problem, Y, calc_second_order=True)
    print(f"Global Sensitivity for {output}:\n", si)

    # Plot first-order, second-order, and total sensitivity indices
    indices = ['S1', 'ST', 'S2']
    values = [si['S1'], si['ST'], np.sum(si['S2'], axis=1)]
    plt.figure(figsize=(10, 6))
    for i, index in enumerate(indices):
        plt.bar(problem['names'], values[i], alpha=0.6, label=index)

    plt.title(f"Sensitivity Indices for {output}")
    plt.xlabel("Parameters")
    plt.ylabel("Sensitivity Index")
    plt.legend()
    plt.show()