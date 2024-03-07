from gerrychain import (Partition, Graph, MarkovChain,
                        updaters, constraints, accept,
                        GeographicPartition)
from gerrychain.proposals import recom
from gerrychain.tree import bipartition_tree
from gerrychain.constraints import contiguous

import matplotlib.pyplot as plt
import pandas as pd
import geopandas as gpd
from functools import partial
from tqdm import tqdm

# Set the random seed so that the results are reproducible!
import random
random.seed(42)

# Select MGGG States file
input_file = 'MN_test/MN_precincts.geojson'
# Set population and district columns
pop_col = 'TOTPOP'; dist_col = 'CONGDIST'

# Set output file
output_file = 'MN_CONGDIST_ensemble.geojson'

# Set ensemble size 
n = 1000

batch_size = 50

print("Setting up the Markov chain...")

# Set up the graph
gdf = gpd.read_file(input_file)
graph = Graph.from_geodataframe(gdf)

# Set up the updaters
my_updaters = {
    "population": updaters.Tally(pop_col, alias="population"),
    "cut_edges": updaters.cut_edges,
    "perimeter": updaters.perimeter,
    "area": updaters.Tally("area", alias="area"),
    "geometry": updaters.boundary_nodes,
}

# Set up the initial partition
initial_partition = GeographicPartition(
    graph,
    assignment=dist_col,
    updaters=my_updaters
)

# TEST: Plot the initial partition
# fig, ax = plt.subplots(figsize=(8,8))
# ax.set_yticks([])
# ax.set_xticks([])
# ax.set_title("Initial Partition in MN")
# initial_partition.plot(ax=ax, cmap='tab20c')
# plt.show()

# Calculate the ideal population for each district
ideal_population = sum(initial_partition["population"].values()) / len(initial_partition)

# Set up proposal
proposal = partial(
    recom,
    pop_col=pop_col,
    pop_target=ideal_population,
    epsilon=0.01,
    node_repeats=2,
)

# Set up Markov chain
recom_chain = MarkovChain(
    proposal=proposal,
    constraints=[contiguous],
    accept=accept.always_accept,
    initial_state=initial_partition,
    total_steps=n,
)

district_data = []

# Run the Markov chain
print("Running the Markov chain...")
batch_results = []

for i, partition in enumerate(recom_chain.with_progress_bar()):
    
    # Store district plan
    gdf[f'plan_{i}'] = [partition.assignment[n] for n in graph.nodes]

    # Store district data
    for district_name in partition.perimeter.keys():
        population = partition.population[district_name]
        perimeter = partition.perimeter[district_name]
        area = partition.area[district_name]
        exterior_boundaries = partition.exterior_boundaries[district_name]
        interior_boundaries = partition.interior_boundaries[district_name]
        cut_edges_by_part = partition.cut_edges_by_part[district_name]
        batch_results.append((i, district_name, population, perimeter, area, exterior_boundaries, interior_boundaries, cut_edges_by_part))

    # Process and save results per batch
    if (i + 1) % batch_size == 0:
        # Create DataFrame for the batch results
        batch_df = pd.DataFrame(
            batch_results,
            columns=[
                'step',
                'district_name',
                'population',
                'perimeter',
                'area',
                'exterior_boundaries',
                'interior_boundaries',
                'cut_edges_by_part'
            ]
        )

        # Save the batch results to GeoJSON
        batch_gdf = gdf[[f'plan_{j}' for j in range(i + 1)] + ['geometry']]
        batch_plans = batch_gdf.melt(id_vars='geometry', var_name='plan', value_vars=[f'plan_{j}' for j in range(i + 1)], value_name='district')
        batch_plans['plan'] = batch_plans['plan'].str.replace('plan_', '')
        batch_dissolved = batch_plans.dissolve(by=['plan', 'district']).reset_index()
        batch_dissolved.to_file(output_file, driver='GeoJSON')

        # Clear batch results
        batch_results = []

# Process and save any remaining results
if batch_results:
    final_batch_df = pd.DataFrame(
        batch_results,
        columns=[
            'step',
            'district_name',
            'population',
            'perimeter',
            'area',
            'exterior_boundaries',
            'interior_boundaries',
            'cut_edges_by_part'
        ]
    )
    
    final_batch_gdf = gdf[[f'plan_{j}' for j in range(i + 1)] + ['geometry']]
    final_batch_plans = final_batch_gdf.melt(id_vars='geometry', var_name='plan', value_vars=[f'plan_{j}' for j in range(i + 1)], value_name='district')
    final_batch_plans['plan'] = final_batch_plans['plan'].str.replace('plan_', '')
    final_batch_dissolved = final_batch_plans.dissolve(by=['plan', 'district']).reset_index()
    final_batch_dissolved.to_file(output_file, driver='GeoJSON')