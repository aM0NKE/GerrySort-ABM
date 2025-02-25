from .statistics import *

from gerrychain import Graph, Partition, GeographicPartition, MarkovChain
from gerrychain.updaters import Tally
from gerrychain.metrics.compactness import polsby_popper
from gerrychain.proposals import recom
from gerrychain.tree import bipartition_tree
from gerrychain.constraints import contiguous, no_vanishing_districts
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
    if model.current_map.crs != model.space.crs:
        model.current_map = model.current_map.to_crs(model.space.crs)
    model.current_map['geometry'] = model.current_map['geometry'].buffer(0) # Fix invalid geometries
   
    # Setup gerrychain
    model.graph = Graph.from_geodataframe(model.current_map)
    updaters = {
        'TOTPOP': Tally('TOTPOP'),
        'NREPS': Tally('NREPS'),
        'NDEMS': Tally('NDEMS'),
        'polsby-popper': polsby_popper,
    }
    if model.max_popdev < model.epsilon:
        if model.print: print('Starting from current assignment')
        initial_partition = Partition(
            model.graph,
            assignment='CONGDIST',
            updaters=updaters
        )
    else:
        if model.print: print('Starting from random assignment')
        initial_partition = GeographicPartition.from_random_assignment(
            model.graph,
            n_parts=len(model.current_map['CONGDIST'].unique()),
            epsilon=model.epsilon,
            pop_col="TOTPOP",
            updaters=updaters
        )
    
    model.ideal_population = sum(initial_partition['TOTPOP'].values()) / len(initial_partition)
    if model.print: print("Ideal population:", model.ideal_population)
    
    proposal = partial(
        recom,
        pop_col='TOTPOP',
        pop_target=model.ideal_population,
        epsilon=model.epsilon,
        node_repeats=1,
        method = partial(
            bipartition_tree,
            max_attempts=100,
            allow_pair_reselection=True
        )
    )
    state_constraints = [] if model.state in ['WI', 'MI', 'MA'] else [contiguous]
    model.recom_chain = MarkovChain(
        proposal=proposal,
        constraints=state_constraints,
        accept=always_accept,
        initial_state=initial_partition,
        total_steps=model.ensemble_size,
    )

def generate_ensemble(model):
    setup_gerrychain(model)

    plans_list = {} # Dictionary to store plans
    congdist_data = {}  # Dictionary to store data for each plan

    # Generate ensemble of plans
    for i, partition in enumerate(model.recom_chain.with_progress_bar()):
        # Store plan and congdist data
        plan_name = f'plan_{i}'
        plans_list[plan_name] = pd.Series([partition.assignment[n] for n in model.graph.nodes], name=plan_name)        
        congdist_data[plan_name] = {
            congdist_name: {
                'TOTPOP': partition['TOTPOP'][congdist_name],
                'NREPS': partition['NREPS'][congdist_name],
                'NDEMS': partition['NDEMS'][congdist_name]
            }
            for congdist_name in partition['TOTPOP'].keys()
        }
    return plans_list, congdist_data

def find_best_plan(model, congdist_data):
    model_dems_frac = model.ndems / (model.ndems + model.nreps)
    eval_results = {}

    # Evaluate each plan
    for plan in congdist_data.keys():
        rep_seats = 0
        dem_seats = 0
        for congdist in congdist_data[plan].keys():
            if congdist_data[plan][congdist]['NREPS'] > congdist_data[plan][congdist]['NDEMS']:
                rep_seats += 1
            elif congdist_data[plan][congdist]['NREPS'] < congdist_data[plan][congdist]['NDEMS']:
                dem_seats += 1
        eval_results[plan] = {
            'rep_congressional_seats': rep_seats,
            'dem_congressional_seats': dem_seats,
            'dem_seatshare': dem_seats / (dem_seats + rep_seats),
            'rep_seatshare': rep_seats / (dem_seats + rep_seats),
        }
        # Score the plans
        if model.print: print(f'Dem seatshare: {dem_seats / (dem_seats + rep_seats)}, Rep seatshare: {rep_seats / (dem_seats + rep_seats)}')
        if model.control == 'Republicans':
            eval_results[plan]['partisan_utility'] = eval_results[plan]['rep_seatshare'] + random.gauss(0, model.sigma)
        elif model.control == 'Democrats':
            eval_results[plan]['partisan_utility'] = eval_results[plan]['dem_seatshare'] + random.gauss(0, model.sigma)
        # Evaluate fairness of each plan
        eval_results[plan]['fairness_score'] = abs(eval_results[plan]['dem_seatshare'] - model_dems_frac) + random.gauss(0, model.sigma)

    # Find best plan based on control
    if model.control == 'Republicans':
        best_plan = max(eval_results, key=lambda x: eval_results[x]['partisan_utility'])
        model.predicted_seats = eval_results[best_plan]['rep_congressional_seats']
    elif model.control == 'Democrats':
        best_plan = max(eval_results, key=lambda x: eval_results[x]['partisan_utility'])
        model.predicted_seats = eval_results[best_plan]['dem_congressional_seats']
    # In case of tie, pick a fair map (closest to actual fraction dems/reps)
    elif model.control == 'Fair':
        best_plan = min(eval_results, key=lambda x: eval_results[x]['fairness_score'])
        model.predicted_seats = 0
   
    return best_plan
        
def mapping_congdist_ids(model):
    # Dissolve geometries by CONGDIST and NEW_CONGDIST, converting to EPSG:4326 in one step
    dissolved_congdist = model.current_map.to_crs(model.space.crs).dissolve(by='CONGDIST', aggfunc='sum')
    dissolved_new_congdist = model.current_map.to_crs(model.space.crs).dissolve(by='NEW_CONGDIST', aggfunc='sum')
    
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

def redistrict(model, plans_list, best_plan):
    # Update the model with the best plan
    model.current_map['NEW_CONGDIST'] = plans_list[best_plan]

    # Generate the mapping for new congdists
    new_congdists_mapping = mapping_congdist_ids(model)

    # Update model.current_map['CONGDIST'] with the new mapping
    model.current_map['NEW_CONGDIST'] = model.current_map['NEW_CONGDIST'].map(new_congdists_mapping)

    # Create a dictionary to store precincts that changed districts
    initial_congdists = model.current_map.set_index('VTDID')['CONGDIST'].copy()
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