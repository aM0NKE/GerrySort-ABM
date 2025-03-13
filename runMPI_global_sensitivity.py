import os
import pandas as pd
from mpi4py import MPI

# Initialize MPI
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

# Define parameters
state = 'GA'
sample_size = 256 # Sobol sample size
batch_size = 25  # Workers will receive this many jobs at a time
output_dir = f'results/sensitivity_analysis/global/{state}_sample_{sample_size}_MPI'

if rank == 0:
    from SALib.sample import sobol as sobel_sample
    
    os.makedirs(output_dir, exist_ok=True)
    param_file_path = os.path.join(output_dir, 'parameter_space.csv')

    # Define Sobol problem
    problem = {
        'num_vars': 7,
        'names': [
            'tolerance', 'beta', 'ensemble_size', 
            'sigma', 'n_moving_options', 'distance_decay', 'capacity_mul'
        ],
        'bounds': [
            [0.0, 1.0],     # tolerance
            [0.0, 100.0],   # beta
            [50, 500],      # ensemble_size
            [0.001, 0.1],   # sigma
            [1, 20],        # n_moving_options
            [0.0, 1.0],     # distance_decay
            [0.9, 1.1]      # capacity_mul
        ]
    }

    # Load or create parameter space
    if os.path.exists(param_file_path):
        params_df = pd.read_csv(param_file_path)
    else:
        param_values = sobel_sample.sample(problem, sample_size)
        params_df = pd.DataFrame(param_values, columns=problem['names'])
        params_df['job_id'] = range(len(params_df))
        params_df['job_id'] = params_df['job_id'].astype(int)
        params_df['completed'] = False
        params_df.to_csv(param_file_path, index=False)

    # Create job queue (and convert run_id is int)
    job_queue = params_df[params_df['completed'] == False][['job_id'] + problem['names']].values.tolist()
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
    def gerrysort_model(state, job_id, params, data, output_dir):
        tolerance, beta, ensemble_size, sigma, n_moving_options, distance_decay, capacity_mul = params
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
            control_rule='CONGDIST',
            initial_control='Model',
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
        model_data.to_csv(os.path.join(output_dir, f'model_data_job_{job_id}.csv'), index=False)
    
    data = gpd.read_file(f'data/processed/{state}.geojson')
    
    while True:
        # Request job from Rank 0
        jobs = comm.recv(source=0, tag=1)
        if jobs is None:
            break  # Termination signal received

        # Execute jobs
        completed_batch = []
        for job in jobs:
            job_id, *params = job
            gerrysort_model(state, job_id, params, data, output_dir)
            completed_batch.append(job_id)

        # Send completed jobs back to Rank 0
        comm.send((rank, completed_batch), dest=0, tag=2)
