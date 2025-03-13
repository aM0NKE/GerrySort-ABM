import os
import pandas as pd
from mpi4py import MPI

# Initialize MPI
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

# Define parameters
state = 'GA'
runs = 100       # Number of runs per parameter set 
batch_size = 10  # Workers will receive this many jobs at a time
output_dir = f'results/sensitivity_analysis/local/{state}_{runs}_MPI'

# Master
if rank == 0:
    os.makedirs(output_dir, exist_ok=True)
    param_file_path = os.path.join(output_dir, 'parameter_space.csv')

    # Define the controls
    controls = ['Democrats', 'Republicans', 'Model']
    
    # Define the baseline parameters
    baseline_params = {
        'tolerance': 0.5,
        'beta': 100.0,
        'ensemble_size': 250,
        'sigma': 0.01,
        'n_moving_options': 10,
        'distance_decay': 0.0,
        'capacity_mul': 1.0
    }

    # Define the parameter ranges for OFAT analysis
    param_ranges = {
        'tolerance': [0.0, 0.25, 0.5, 0.75, 1.0],
        'beta': [0.0, 25.0, 50.0, 75.0, 100.0],
        'ensemble_size': [50, 100, 250, 500],
        'sigma': [0.001, 0.01, 0.05, .1],
        'n_moving_options': [5, 10, 15, 20],
        'distance_decay': [0.0, 0.25, 0.5, 0.75, 1.0],
        'capacity_mul': [0.9, 1.0, 1.1]
    }

    # Load or create parameter space
    if os.path.exists(param_file_path):
        params_df = pd.read_csv(param_file_path)
    else:
        new_rows = []
        for param_name, param_values in param_ranges.items():
            for value in param_values:
                for control in controls:
                    for run in range(runs):
                        # Create a copy of the baseline parameters
                        params = list(baseline_params.values())
                        # Replace the current parameter's value
                        param_index = list(baseline_params.keys()).index(param_name)
                        params[param_index] = value
                        # Collect new row
                        new_rows.append([len(new_rows), param_name, run, *params, control, False])
        # Save parameter space
        params_df = pd.DataFrame(new_rows, columns=['job_id', 'param', 'run'] + list(baseline_params.keys()) + ['control', 'completed'])
        params_df.to_csv(param_file_path, index=False)

    # Create job queue
    job_queue = params_df[params_df['completed'] == False].values.tolist()
    job_count = len(job_queue)
    completed_jobs = []

    # Distribute initial batch of jobs
    for i in range(1, size):
        if job_queue:
            batch = [job_queue.pop(0) for _ in range(min(batch_size, len(job_queue)))]
            comm.send(batch, dest=i, tag=1)

    while job_queue or job_count > 0:
        # Receive completed jobs from workers
        rank, completed_batch = comm.recv(source=MPI.ANY_SOURCE, tag=2)
        completed_jobs.extend(completed_batch)
        job_count -= len(completed_batch)
        print(f"Rank 0: {job_count}/{len(params_df)} jobs remaining")

        # Assign new job to workers (if available)
        if job_queue:
            batch = [job_queue.pop(0) for _ in range(min(batch_size, len(job_queue)))]
            comm.send(batch, dest=rank, tag=1)

        # Update parameter_space.csv
        params_df.loc[params_df['job_id'].isin(completed_jobs), 'completed'] = True
        params_df.to_csv(param_file_path, index=False)

    # Send termination signal to workers
    for i in range(1, size):
        comm.send(None, dest=i, tag=1)

# Workers
else:
    import geopandas as gpd
    from gerrysort.model import GerrySort
    def gerrysort_model(state, job_id, param, control, params, data, output_dir):
        """
        Wrapper function to run the GerrySort model with sampled parameters.
        """
        tolerance, beta, ensemble_size, sigma, n_moving_options, distance_decay, capacity_mul = params
        # Set the control rule
        if control == 'Democrats':
            control_rule = 'FIXED'
        elif control == 'Republicans':
            control_rule = 'FIXED'
        elif control == 'Model':
            control_rule = 'CONGDIST'
        model = GerrySort(
            state=state,
            print_output=False,
            vis_level=None,
            data=data,
            election='PRES20',
            max_iters=4,
            npop=int({'MN': 5800, 'WI': 5900, 'MI': 10000, 'PA': 13000, 'GA': 11000, 'TX': 30500}[state]),
            sorting=True,
            gerrymandering=True,
            control_rule=control_rule,
            initial_control=control,
            tolerance=float(tolerance),
            beta=float(beta),
            ensemble_size=int(ensemble_size),
            epsilon=0.01,
            sigma=float(sigma),
            n_moving_options=int(n_moving_options),
            distance_decay=float(distance_decay),
            capacity_mul=float(capacity_mul)
        )
        model.run_model()
        model_data = model.datacollector.get_model_vars_dataframe()
        model_data.to_csv(os.path.join(output_dir, f'model_data_{param}_{control}_job_{job_id}.csv'), index=False)
    
    # Load the state data
    data = gpd.read_file(f'data/processed/{state}.geojson')

    while True:
        # Request job from Rank 0
        jobs = comm.recv(source=0, tag=1)
        if jobs is None:
            break  # Termination signal received

        # Execute jobs
        completed_batch = []
        for job in jobs:
            job_id, param, run_id, *params, control, completed = job
            gerrysort_model(state, job_id, param, control, params, data, output_dir)
            completed_batch.append(job_id)

        # Send completed jobs back to Rank 0
        comm.send((rank, completed_batch), dest=0, tag=2)
