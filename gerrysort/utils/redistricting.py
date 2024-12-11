from .statistics import *

from gerrychain import Graph, GeographicPartition, MarkovChain
from gerrychain.updaters import Tally
from gerrychain.metrics.compactness import polsby_popper
from gerrychain.proposals import recom
from gerrychain.tree import bipartition_tree
from gerrychain.constraints import contiguous
from gerrychain.accept import always_accept
from gerrychain.optimization import SingleMetricOptimizer
from functools import partial

import geopandas as gpd
import pandas as pd
import random

def extract_demographics_current_map(model):
    # Save the current map as a GeoDataFrame (used for gerrychain)
    model.current_map = gpd.GeoDataFrame([
        {
            'geometry': unit.geometry,
            'NREPS': unit.rep_cnt,
            'NDEMS': unit.dem_cnt,
            'TOTPOP': unit.num_people,
            'VTDID': unit.unique_id,
            'COUNTYFP': unit.COUNTYFP,
            'CONGDIST': unit.CONGDIST,
            'area': unit.geometry.area,
        }
        for unit in model.precincts
    ], crs=model.space.crs)

def setup_gerrychain(model):
    # Extract demographics from current map
    extract_demographics_current_map(model)

    # Check if current map is in the correct crs
    if model.current_map.crs != "EPSG:26915":
        model.current_map = model.current_map.to_crs(epsg=26915)  
    model.current_map['geometry'] = model.current_map['geometry'].buffer(0) # Fix invalid geometries

    # Setup gerrychain
    model.graph = Graph.from_geodataframe(model.current_map) 
    updaters = {
        'TOTPOP': Tally('TOTPOP'),
        'NREPS': Tally('NREPS'),
        'NDEMS': Tally('NDEMS'),
        'polsby-popper': polsby_popper,
    }
    initial_partition = GeographicPartition.from_random_assignment(
        model.graph,
        n_parts=len(model.current_map['CONGDIST'].unique()),
        epsilon=model.epsilon,
        pop_col="TOTPOP",
        updaters=updaters
    )
    model.ideal_population = sum(initial_partition['TOTPOP'].values()) / len(initial_partition)
    if model.print:
        print("Ideal population:", model.ideal_population)

    proposal = partial(
        recom,
        pop_col='TOTPOP',
        pop_target=model.ideal_population,
        epsilon=model.epsilon,
    )
    state_constraints = [] if model.state in ['WI', 'MI', 'MA'] else [contiguous]
    if model.control == "Republicans":
        model.opt_metric = lambda x: sum([1 for node in x.parts if x["NREPS"][node] > x["NDEMS"][node]])/len(x)
    elif model.control == "Democrats":
        model.opt_metric = lambda x: sum([1 for node in x.parts if x["NDEMS"][node] > x["NREPS"][node]])/len(x)
    elif model.control == "Fair":
        model.opt_metric = lambda x: abs(sum([1 for node in x.parts if x["NDEMS"][node] > x["NREPS"][node]])/len(x) - model.ndems / (model.ndems + model.nreps))
    maximize = True if model.control in ["Republicans", "Democrats"] else False
    model.map_generator = SingleMetricOptimizer(
        initial_state=initial_partition,
        proposal=proposal,
        constraints=state_constraints,
        optimization_metric=model.opt_metric,
        maximize=maximize, # NOTE: Set to false when Fair
    )

def find_best_plan(model):
    setup_gerrychain(model)
    best_map = -1
    for i, part in enumerate(model.map_generator.tilted_run(model.ensemble_size, model.sigma, with_progress_bar=True)):
        best_map = max(best_map, model.opt_metric(part))
    print(f'The {model.control} have found the best plan with a score of {best_map}')
    model.current_map['NEW_CONGDIST'] = model.map_generator.best_part.assignment
    model.current_map['NEW_CONGDIST'] = model.current_map['NEW_CONGDIST'].apply(lambda x: str(int(x) + 1).zfill(2))

def mapping_congdist_ids(model):
    # Dissolve geometries by CONGDIST and NEW_CONGDIST, converting to EPSG:4326 in one step
    dissolved_congdist = model.current_map.to_crs(epsg=4326).dissolve(by='CONGDIST', aggfunc='sum')
    dissolved_new_congdist = model.current_map.to_crs(epsg=4326).dissolve(by='NEW_CONGDIST', aggfunc='sum')
    
    # Calculate overlaps in a vectorized manner
    overlap_data = (
        dissolved_new_congdist.geometry.apply(lambda geom_new: 
            dissolved_congdist.geometry.apply(lambda geom_old: geom_new.intersection(geom_old).area))
        .stack()
        .reset_index()
    )
    overlap_data.columns = ['NEW_CONGDIST', 'CONGDIST', 'overlap_area']

    # Sort overlaps by area in descending order
    overlap_data = overlap_data.sort_values(by='overlap_area', ascending=False)

    # Create one-to-one mapping based on largest overlap
    assigned_partitions = {}
    for _, row in overlap_data.iterrows():
        if row['NEW_CONGDIST'] not in assigned_partitions and row['CONGDIST'] not in assigned_partitions.values():
            assigned_partitions[row['NEW_CONGDIST']] = row['CONGDIST']

    # Update dissolved_new_congdist with the mapped CONGDIST values
    dissolved_new_congdist['CONGDIST'] = dissolved_new_congdist.index.map(assigned_partitions)

    # Return the mapping dictionary
    return dissolved_new_congdist['CONGDIST'].to_dict()

def redistrict(model):
    # Store current congdist assignments
    initial_congdists = model.current_map.set_index('VTDID')['CONGDIST'].copy()

    # Generate the mapping for new congdists
    new_congdists_mapping = mapping_congdist_ids(model)

    # Update model.current_map['CONGDIST'] with the new mapping
    model.current_map['NEW_CONGDIST'] = model.current_map['NEW_CONGDIST'].map(new_congdists_mapping)

    # Create a dictionary to store precincts that changed districts
    reassigned_precincts = {
        vtdid: new_congdist 
        for vtdid, new_congdist in model.current_map[['VTDID', 'NEW_CONGDIST']].itertuples(index=False)
        if initial_congdists[vtdid] != new_congdist
    }
    
    # Calculate the percentage of precincts that changed districts
    model.change_map = len(reassigned_precincts) / len(model.precincts)

    # Set the new congdist assignments
    model.current_map['CONGDIST'] = model.current_map['NEW_CONGDIST']

    # Update the geometry of each district
    new_map = model.current_map.dissolve(by='CONGDIST', aggfunc='sum').reset_index().to_crs(model.space.crs)
    new_geometries = new_map.set_index('CONGDIST')['geometry'].to_dict()
    for congdist in model.congdists:
        congdist.geometry = new_geometries[congdist.unique_id]

    return reassigned_precincts

def update_mapping(model, reassigned_precincts):
    for precinct_id, congdist_id in reassigned_precincts.items():
        precinct = model.space.get_precinct_by_id(precinct_id)
        old_congdist = model.space.get_congdist_by_id(precinct.CONGDIST)
        new_congdist = model.space.get_congdist_by_id(congdist_id)

        # Update precinct-to-congdist map and precinct attributes
        model.space.precinct_congdist_map[precinct_id] = congdist_id
        precinct.CONGDIST = congdist_id

        # Update precinct lists and district totals
        old_congdist.precincts.remove(precinct_id)
        new_congdist.precincts.append(precinct_id)

        for attr in ['rep_cnt', 'dem_cnt', 'num_people']:
            value = getattr(precinct, attr)
            setattr(old_congdist, attr, getattr(old_congdist, attr) - value)
            setattr(new_congdist, attr, getattr(new_congdist, attr) + value)

        # Update person congdist_id attribute
        for person_id in precinct.reps + precinct.dems:
            person = model.space.get_person_by_id(person_id)
            person.congdist_id = congdist_id
