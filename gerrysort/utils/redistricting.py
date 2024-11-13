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
            'NREPS': len(unit.reps),
            'NDEMS': len(unit.dems),
            'TOTPOP': unit.num_people,
            'VTDID': unit.unique_id,
            'COUNTYFIPS': unit.COUNTYFIPS,
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
    # print("Number of districts: ", len(model.initial_partition))
    # print("Ideal population: ", model.ideal_population)    
    model.proposal = partial(
        recom,
        pop_col='TOTPOP',
        pop_target=model.ideal_population,
        epsilon=0.1,
        node_repeats=100,
        method = partial(
            bipartition_tree,
            max_attempts=100,
            allow_pair_reselection=True
        )
    )
    model.recom_chain = MarkovChain(
        proposal=model.proposal,
        constraints=[contiguous],
        accept=accept.always_accept,
        initial_state=model.initial_partition,
        total_steps=model.ensemble_size,
    )

def generate_ensemble(model):
    # Set up chain
    setup_gerrychain(model)
    # Generate ensemble of plans
    district_data = {}  # Dictionary to store data for each plan
    plans_list = {}
    for i, partition in enumerate(model.recom_chain.with_progress_bar()):
        # Store plan and district data
        plan_name = f'plan_{i}'
        plans_list[plan_name] = pd.Series([partition.assignment[n] for n in model.graph.nodes], name=plan_name)        
        district_data[plan_name] = {
            district_name: {
                'population': partition['population'][district_name],
                'nreps': partition['n_reps'][district_name],
                'ndems': partition['n_dems'][district_name]
            }
            for district_name in partition['population'].keys()
        }
    return plans_list, district_data

def find_best_plan(model, district_data):
    eval_results = {}
    # Evaluate each plan
    for plan in district_data.keys():
        rep_seats = 0
        dem_seats = 0
        for district in district_data[plan].keys():
            if district_data[plan][district]['nreps'] > district_data[plan][district]['ndems']:
                rep_seats += 1
            elif district_data[plan][district]['nreps'] < district_data[plan][district]['ndems']:
                dem_seats += 1
        eval_results[plan] = {
            'red_congressional_seats': rep_seats,
            'blue_congressional_seats': dem_seats,
        }
    # Find best plan based on control
    if model.control == 'Republican':
        best_plan = max(eval_results, key=lambda x: eval_results[x]['red_congressional_seats'])
    elif model.control == 'Democratic':
        best_plan = max(eval_results, key=lambda x: eval_results[x]['blue_congressional_seats'])
    elif model.control == 'Tied':
        best_plan = f'plan_{random.randint(0, model.ensemble_size - 1)}'
    return best_plan
        
def redistrict(model, plans_list, best_plan):
    # Store current district assignments
    initial_districts = model.current_map.set_index('VTDID')['CONGDIST'].copy()
    # Update mapping of precinct to congressional district with the best plan
    model.current_map['CONGDIST'] = plans_list[best_plan]
    # Create a dictionary to store precincts that changed districts
    reassigned_precincts = {
        vtdid: new_district 
        for vtdid, new_district in model.current_map[['VTDID', 'CONGDIST']].itertuples(index=False)
        if initial_districts[vtdid] != new_district
    }
    model.change_map = len(reassigned_precincts) / len(model.precincts) # % of precincts that changed districts
    # Update geometry based on new district assignments
    new_map = model.current_map.dissolve(by='CONGDIST', aggfunc='sum').reset_index().to_crs(model.space.crs) # Convert crs
    # Update geometry of each district
    new_geometries = new_map.set_index('CONGDIST')['geometry'].to_dict()
    for district in model.congdists:
        district.geometry = new_geometries[district.unique_id]
    return reassigned_precincts

def update_mapping(model, reassigned_precincts):
    for precinct_id, district_id in reassigned_precincts.items():
        # Update precinct to congdist map
        model.space.precinct_congdist_map[precinct_id] = district_id
        # Add precinct to new district
        new_district = model.space.get_district_by_id(district_id)
        new_district.precincts.append(precinct_id)        
        # Remove precinct from old district
        old_district = model.space.get_district_by_id(model.space.get_precinct_by_id(precinct_id).CONGDIST)
        old_district.precincts.remove(precinct_id)
        # Update precinct.CONGDIST attribute
        precinct = model.space.get_precinct_by_id(precinct_id)
        precinct.CONGDIST = district_id
        # Update district.rep_cnt and district.dem_cnt
        new_district.rep_cnt += len(precinct.reps)
        new_district.dem_cnt += len(precinct.dems)
        new_district.num_people += precinct.num_people
        old_district.rep_cnt -= len(precinct.reps)
        old_district.dem_cnt -= len(precinct.dems)
        old_district.num_people -= precinct.num_people
        # Update person district_id attribute
        for rep in precinct.reps:
            person = model.space.get_person_by_id(rep)
            person.district_id = district_id
        for dem in precinct.dems:
            person = model.space.get_person_by_id(dem)
            person.district_id = district_id
