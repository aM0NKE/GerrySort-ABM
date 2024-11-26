from .statistics import *

from gerrychain import (Partition, Graph, MarkovChain,
                        updaters, constraints, accept,
                        GeographicPartition)
from gerrychain.proposals import recom
from gerrychain.tree import bipartition_tree
from gerrychain.constraints import contiguous
from functools import partial

import geopandas as gpd
import pandas as pd
import random

def extract_demographics_current_map(model):
    # Collect rows in a list of dictionaries
    rows = []
    for unit in model.precincts:
        rows.append({
            'geometry': unit.geometry,
            'NREPS': unit.rep_cnt,
            'NDEMS': unit.dem_cnt,
            'TOTPOP': unit.num_people,
            'VTDID': unit.unique_id,
            'COUNTYFP': unit.COUNTYFP,
            'CONGDIST': unit.CONGDIST,
            'area': unit.geometry.area,
        })
    # Save the current map as a GeoDataFrame (used for gerrychain)
    model.current_map = gpd.GeoDataFrame(rows, crs=model.space.crs)

def setup_gerrychain(model):
    extract_demographics_current_map(model)
    if model.current_map.crs != "EPSG:26915":
        model.current_map = model.current_map.to_crs(epsg=26915)    
    model.current_map['geometry'] = model.current_map['geometry'].buffer(0)
    model.graph = Graph.from_geodataframe(model.current_map)
    model.updaters = {
        'population': updaters.Tally('TOTPOP', alias='population'),
        'n_reps': updaters.Tally('NREPS', alias='n_reps'),
        'n_dems': updaters.Tally('NDEMS', alias='n_dems'),
        'cut_edges': updaters.cut_edges,
        'perimeter': updaters.perimeter,
        'area': updaters.Tally('area', alias='area'),
        'geometry': updaters.boundary_nodes,
    }
    model.initial_partition = GeographicPartition(
        model.graph,
        assignment='CONGDIST',
        updaters=model.updaters
    )
    model.ideal_population = sum(model.initial_partition['population'].values()) / len(model.initial_partition)
    # print("Total population: ", sum(model.initial_partition["population"].values()))
    # print("Number of congdistss: ", len(model.initial_partition))
    # print("Ideal population: ", model.ideal_population)    
    model.proposal = partial(
        recom,
        pop_col='TOTPOP',
        pop_target=model.ideal_population,
        epsilon=model.epsilon,
        node_repeats=100,
        method = partial(
            bipartition_tree,
            max_attempts=100,
            allow_pair_reselection=True
        )
    )
    if model.state in ['WI', 'MI', 'MA']:
        state_constraints = []
    else:
        state_constraints = [contiguous]
    model.recom_chain = MarkovChain(
        proposal=model.proposal,
        constraints=state_constraints,
        accept=accept.always_accept,
        initial_state=model.initial_partition,
        total_steps=model.ensemble_size,
    )

def generate_ensemble(model):
    setup_gerrychain(model)
    # Generate ensemble of plans
    congdist_data = {}  # Dictionary to store data for each plan
    plans_list = {}
    for i, partition in enumerate(model.recom_chain.with_progress_bar()):
        # Store plan and congdist data
        plan_name = f'plan_{i}'
        plans_list[plan_name] = pd.Series([partition.assignment[n] for n in model.graph.nodes], name=plan_name)        
        congdist_data[plan_name] = {
            congdist_name: {
                'population': partition['population'][congdist_name],
                'nreps': partition['n_reps'][congdist_name],
                'ndems': partition['n_dems'][congdist_name]
            }
            for congdist_name in partition['population'].keys()
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
            if congdist_data[plan][congdist]['nreps'] > congdist_data[plan][congdist]['ndems']:
                rep_seats += 1
            elif congdist_data[plan][congdist]['nreps'] < congdist_data[plan][congdist]['ndems']:
                dem_seats += 1
        eval_results[plan] = {
            'rep_congressional_seats': rep_seats,
            'dem_congressional_seats': dem_seats,
            'dem_seatshare': dem_seats / (dem_seats + rep_seats),
            'rep_seatshare': rep_seats / (dem_seats + rep_seats),
        }
        # Score the plans based on control
        e = random.gauss(0, model.sigma)
        # NOTE: Add noise to fractions or total seats?
        print(f'Dem seatshare: {dem_seats / (dem_seats + rep_seats)}, Rep seatshare: {rep_seats / (dem_seats + rep_seats)}, Noise: {e}')
        if model.control == 'Republican':
            eval_results[plan]['partisan_utility'] = eval_results[plan]['rep_seatshare'] + e
        elif model.control == 'Democratic':
            eval_results[plan]['partisan_utility'] = eval_results[plan]['dem_seatshare'] + e
        # Evaluate fairness of each plan
        eval_results[plan]['fairness_score'] = abs(eval_results[plan]['dem_seatshare'] - model_dems_frac) + e # NOTE: Noise on fair map?

    # Find best plan based on control
    if model.control == 'Republican':
        best_plan = max(eval_results, key=lambda x: eval_results[x]['partisan_utility'])
    elif model.control == 'Democratic':
        best_plan = max(eval_results, key=lambda x: eval_results[x]['partisan_utility'])
    # In case of tie, pick a fair map (closest to actual fraction dems/reps)
    elif model.control == 'Tied':
        best_plan = min(eval_results, key=lambda x: eval_results[x]['fairness_score'])
    return best_plan
        
def redistrict(model, plans_list, best_plan):
    # Store current congdist assignments
    initial_congdists = model.current_map.set_index('VTDID')['CONGDIST'].copy()
    # Update mapping of precinct to congressional district with the best plan
    model.current_map['CONGDIST'] = plans_list[best_plan]
    # Create a dictionary to store precincts that changed districts
    reassigned_precincts = {
        vtdid: new_congdist 
        for vtdid, new_congdist in model.current_map[['VTDID', 'CONGDIST']].itertuples(index=False)
        if initial_congdists[vtdid] != new_congdist
    }
    model.change_map = len(reassigned_precincts) / len(model.precincts) # % of precincts that changed congdists
    # Update geometry based on new congdist assignments
    new_map = model.current_map.dissolve(by='CONGDIST', aggfunc='sum').reset_index().to_crs(model.space.crs) # Convert crs
    # Update geometry of each congdist
    new_geometries = new_map.set_index('CONGDIST')['geometry'].to_dict()
    for congdist in model.congdists:
        congdist.geometry = new_geometries[congdist.unique_id]
    return reassigned_precincts

def update_mapping(model, reassigned_precincts):
    for precinct_id, congdist_id in reassigned_precincts.items():
        # Update precinct to congdist map
        model.space.precinct_congdist_map[precinct_id] = congdist_id
        # Remove precinct from old congdist
        old_congdist = model.space.get_congdist_by_id(model.space.get_precinct_by_id(precinct_id).CONGDIST)
        old_congdist.precincts.remove(precinct_id)
        # Add precinct to new congdist
        new_congdist = model.space.get_congdist_by_id(congdist_id)
        new_congdist.precincts.append(precinct_id)        
        # Update precinct.CONGDIST attribute
        precinct = model.space.get_precinct_by_id(precinct_id)
        precinct.CONGDIST = congdist_id
        # Update congdist.rep_cnt and congdist.dem_cnt
        new_congdist.rep_cnt += precinct.rep_cnt
        new_congdist.dem_cnt += precinct.dem_cnt
        new_congdist.num_people += precinct.num_people
        old_congdist.rep_cnt -= precinct.rep_cnt
        old_congdist.dem_cnt -= precinct.dem_cnt
        old_congdist.num_people -= precinct.num_people
        # Update person congdist_id attribute
        for rep in precinct.reps:
            person = model.space.get_person_by_id(rep)
            person.congdist_id = congdist_id
        for dem in precinct.dems:
            person = model.space.get_person_by_id(dem)
            person.congdist_id = congdist_id
