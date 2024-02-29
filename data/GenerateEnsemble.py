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
input_file = 'MN_precincts.geojson'
# Set population and district columns
pop_col = 'TOTPOP'; dist_col = 'CONGDIST'

# Set output file
output_file = 'MN_CONGDIST_ensemble.geojson'

# Set ensemble size 
n = 100

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
for i, partition in enumerate(recom_chain.with_progress_bar()):

    # Store district plan
    gdf['plan_{}'.format(i)] = [partition.assignment[n] for n in graph.nodes]

    # Store district data
    for district_name in partition.perimeter.keys():
        population = partition.population[district_name]
        perimeter = partition.perimeter[district_name]
        area = partition.area[district_name]
        exterior_boundaries = partition.exterior_boundaries[district_name]
        interior_boundaries = partition.interior_boundaries[district_name]
        # boundry_nodes = partition.boundry_nodes[district_name]
        # cut_edges = partition.cut_edges[district_name]
        cut_edges_by_part = partition.cut_edges_by_part[district_name]
        district_data.append((i, district_name, population, perimeter, area, exterior_boundaries, interior_boundaries, cut_edges_by_part))

df = pd.DataFrame(
    district_data,
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

# Preprocess the gdf to obtain an ensemble of district plans
print("Processing the results...")
test_gdf = gdf.copy()
# Select plans and geometries
plans = test_gdf[[f'plan_{i}' for i in range(n)] + ['geometry']]
# Transform df into plan|district|geometry format
plans = plans.melt(id_vars='geometry', var_name='plan', value_vars=[f'plan_{i}' for i in range(n)], value_name='district')
# Remove the 'plan_' prefix from the plan names
plans['plan'] = plans['plan'].str.replace('plan_', '')
# Dissolve the geometries by plan and district
dissolved = plans.dissolve(by=['plan', 'district']).reset_index()

# Save the ensemble to geojson
print("Saving the results...")
dissolved.to_file(output_file, driver='GeoJSON')