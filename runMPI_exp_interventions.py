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
batch_size = 5   # Workers will receive this many jobs at a time
output_dir = f'results/experiments/interventions/{state}_runs_{runs}_MPI'

# Master
if rank == 0:
    os.makedirs(output_dir, exist_ok=True)
    param_file_path = os.path.join(output_dir, 'parameter_space.csv')

    # Define interventions and weights
    interventions = ['Competitive', 'Compact']
    interventions_weigths = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

    # Load or create parameter space
    if os.path.exists(param_file_path):
        params_df = pd.read_csv(param_file_path)
    else:
        new_rows = []
        for intervention in interventions:
            for weight in interventions_weigths:
                for run in range(runs):
                    new_rows.append([len(new_rows), intervention, weight, run, False])
        params_df = pd.DataFrame(new_rows, columns=['job_id', 'intervention', 'intervention_weight', 'run', 'completed'])
        params_df.to_csv(param_file_path, index=False)

    # Create job queue
    job_queue = params_df[params_df['completed'] == False][['job_id', 'intervention', 'intervention_weight', 'run']].values.tolist()
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
    def gerrysort_model(state, run_id, intervention, intervention_weight, data, output_dir):
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
            tolerance=0.5,
            beta=200.0,
            ensemble_size=250,
            epsilon=0.01,
            sigma=0.01,
            n_moving_options=10,
            distance_decay=0.0,
            capacity_mul=1.0,
            intervention=intervention,
            intervention_weight=intervention_weight
        )
        model.run_model()
        model_data = model.datacollector.get_model_vars_dataframe()
        model_data.to_csv(os.path.join(output_dir, f'model_data_{intervention}_{intervention_weight}_run_{run_id}.csv'), index=False)
    
    data = gpd.read_file(f'data/processed/{state}.geojson')

    while True:
        # Request job from Rank 0
        jobs = comm.recv(source=0, tag=1)
        if jobs is None:
            break  # Termination signal received

        # Execute jobs
        completed_batch = []
        for job in jobs:
            job_id, intervention, intervention_weight, run_id = job
            gerrysort_model(state, run_id, intervention, intervention_weight, data, output_dir)
            completed_batch.append(job_id)

        # Send completed jobs back to Rank 0
        comm.send((rank, completed_batch), dest=0, tag=2)
