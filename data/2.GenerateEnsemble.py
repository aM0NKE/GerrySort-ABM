from gerrychain import (Partition, Graph, MarkovChain,
                        updaters, constraints, accept,
                        GeographicPartition)
from gerrychain.proposals import recom
from gerrychain.tree import bipartition_tree
from gerrychain.constraints import contiguous

import os
import matplotlib.pyplot as plt
import pandas as pd
import geopandas as gpd
from functools import partial
from tqdm import tqdm

# Set the random seed so that the results are reproducible!
import random
random.seed(69)

state = 'WI'

# Select MGGG States file
input_file = os.path.join('processed_states', f'{state}_counties_MODEL_TEST.geojson')
# Set population and district columns
pop_col = 'TOTPOP'; dist_col = 'CONGDIST'

# Set output file
output_file = os.path.join('processed_states', f'{state}_CONGDIST_ensemble_MODEL_TEST.geojson')

# Set ensemble and batch size 
n = 50
batch_size = 50

print("Setting up the Markov chain...")

# Set up the graph
gdf = gpd.read_file(input_file).to_crs(epsg=26915) # covert to 26915
# Rename district values to 'congressional-' + district number
gdf['CONGDIST'] = 'congressional-' + gdf['CONGDIST'].astype(str)
# Attempt to repair invalid geometries using buffer(0)
gdf['geometry'] = gdf['geometry'].buffer(0)

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
print("Total population: ", sum(initial_partition["population"].values()))
print("Number of districts: ", len(initial_partition))
print("Ideal population: ", ideal_population)

# Set up proposal
proposal = partial(
    recom,
    pop_col=pop_col,
    pop_target=ideal_population,
    epsilon=0.25,
    node_repeats=100,
    method = partial(
        bipartition_tree,
        max_attempts=100,
        allow_pair_reselection=True  # <-- This is the only change
    )
)

# Set up Markov chain
recom_chain = MarkovChain(
    proposal=proposal,
    # constraints=[],
    constraints=[contiguous],
    accept=accept.always_accept,
    initial_state=initial_partition,
    total_steps=n,
)

district_data = []
plans_list = []  # List to collect all plans

# Run the Markov chain
print("Running the Markov chain...")
for i, partition in enumerate(recom_chain.with_progress_bar()):
    # Collect district assignments for each partition
    plan = pd.Series([partition.assignment[n] for n in graph.nodes], name=f'plan_{i}')
    plans_list.append(plan)

    # Store district data
    for district_name in partition.perimeter.keys():
        population = partition.population[district_name]
        perimeter = partition.perimeter[district_name]
        area = partition.area[district_name]
        exterior_boundaries = partition.exterior_boundaries[district_name]
        interior_boundaries = partition.interior_boundaries[district_name]
        cut_edges_by_part = partition.cut_edges_by_part[district_name]
        district_data.append((i, district_name, population, perimeter, area, exterior_boundaries, interior_boundaries, cut_edges_by_part))

    # Process and save results per batch
    if (i + 1) % batch_size == 0:
        # Concatenate plans for this batch
        plans_df = pd.concat(plans_list, axis=1)
        gdf = gdf.join(plans_df)

        # Save the batch results to GeoJSON
        batch_gdf = gdf[[f'plan_{j}' for j in range(i + 1)] + ['geometry']]
        batch_plans = batch_gdf.melt(id_vars='geometry', var_name='plan', value_vars=[f'plan_{j}' for j in range(i + 1)], value_name='district')
        batch_plans['plan'] = batch_plans['plan'].str.replace('plan_', '')
        batch_dissolved = batch_plans.dissolve(by=['plan', 'district']).reset_index()
        batch_dissolved.to_file(output_file, driver='GeoJSON')

        # Clear the plans list after saving
        plans_list = []

# Handle any remaining plans after the loop
if plans_list:
    final_plans_df = pd.concat(plans_list, axis=1)
    gdf = gdf.join(final_plans_df)

    final_batch_gdf = gdf[[f'plan_{j}' for j in range(i + 1)] + ['geometry']]
    final_batch_plans = final_batch_gdf.melt(id_vars='geometry', var_name='plan', value_vars=[f'plan_{j}' for j in range(i + 1)], value_name='district')
    final_batch_plans['plan'] = final_batch_plans['plan'].str.replace('plan_', '')
    final_batch_dissolved = final_batch_plans.dissolve(by=['plan', 'district']).reset_index()
    final_batch_dissolved.to_file(output_file, driver='GeoJSON')