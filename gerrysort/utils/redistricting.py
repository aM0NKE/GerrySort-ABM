from .statistics import *

import geopandas as gpd
from gerrychain import Graph, GeographicPartition
from gerrychain.optimization import SingleMetricOptimizer
from gerrychain.proposals import recom
from gerrychain.tree import bipartition_tree
from gerrychain.constraints import contiguous
from gerrychain.updaters import Tally
from functools import partial

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
            'perimeter': unit.geometry.length,
        }
        for unit in model.precincts
    ], crs=model.space.crs)

def setup_gerrychain(model):
    # Extract demographics from current map
    extract_demographics_current_map(model)

    # Check if current map is in the correct crs
    if model.current_map.crs != model.space.crs:
        model.current_map = model.current_map.to_crs(model.space.crs)
    # Fix invalid geometries
    if len(model.current_map[model.current_map.is_valid == False]) > 0:
        model.current_map['geometry'] = model.current_map['geometry'].buffer(0)

    # Setup gerrychain
    model.graph = Graph.from_geodataframe(model.current_map) 
    updaters = {
        'TOTPOP': Tally('TOTPOP'),
        'NREPS': Tally('NREPS'),
        'NDEMS': Tally('NDEMS'),
    }
    if model.max_popdev < model.epsilon:
        if model.print: print('Starting from current assignment')
        initial_partition = GeographicPartition(
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
        node_repeats=100,
        method = partial(
            bipartition_tree,
            max_attempts=100,
            allow_pair_reselection=True
        )
    )
    state_constraints = [] if model.state in ['WI', 'MI'] else [contiguous]
    if model.control == "Republicans":
        if model.intervention == 'Competitive':
            w1, w2 = model.intervention_weight, 1 - model.intervention_weight
            model.opt_metric = lambda x: w1 * (1 - (sum([abs(x["NDEMS"][node] - x["NREPS"][node]) / (x["NDEMS"][node] + x["NREPS"][node] + 1e-9) for node in x.parts]) / len(x))) + w2 * (sum([1 for node in x.parts if x["NREPS"][node] > x["NDEMS"][node]]) / len(x)) + np.random.normal(0,  model.sigma)
        elif model.intervention == 'Compact':
            w1, w2 = model.intervention_weight, 1 - model.intervention_weight
            model.opt_metric = lambda x: w1 * (sum([4 * np.pi * (x["area"][node] / (x["perimeter"][node] ** 2 + 1e-9)) for node in x.parts]) / len(x)) + w2 * (sum([1 for node in x.parts if x["NREPS"][node] > x["NDEMS"][node]]) / len(x)) + np.random.normal(0,  model.sigma)
        else:
            model.opt_metric = lambda x: (sum([1 for node in x.parts if x["NREPS"][node] > x["NDEMS"][node]]) / len(x)) + np.random.normal(0,  model.sigma)

    elif model.control == "Democrats":
        if model.intervention == 'Competitive':
            w1, w2 = model.intervention_weight, 1 - model.intervention_weight
            model.opt_metric = lambda x: w1 * (1 - (sum([abs(x["NDEMS"][node] - x["NREPS"][node]) / (x["NDEMS"][node] + x["NREPS"][node] + 1e-9) for node in x.parts]) / len(x))) + w2 * (sum([1 for node in x.parts if x["NDEMS"][node] > x["NREPS"][node]]) / len(x)) + np.random.normal(0,  model.sigma)
        elif model.intervention == 'Compact':
            w1, w2 = model.intervention_weight, 1 - model.intervention_weight
            model.opt_metric = lambda x: w1 * (sum([4 * np.pi * (x["area"][node] / (x["perimeter"][node] ** 2 + 1e-9)) for node in x.parts]) / len(x)) + w2 * (sum([1 for node in x.parts if x["NDEMS"][node] > x["NREPS"][node]]) / len(x)) + np.random.normal(0,  model.sigma)
        else:
            model.opt_metric = lambda x: (sum([1 for node in x.parts if x["NDEMS"][node] > x["NREPS"][node]]) / len(x)) + np.random.normal(0,  model.sigma)

    elif model.control == "Fair":
        if model.intervention == 'Competitive':
            model.opt_metric = lambda x: (1 - (sum([abs(x["NDEMS"][node] - x["NREPS"][node]) / (x["NDEMS"][node] + x["NREPS"][node] + 1e-9) for node in x.parts]) / len(x))) + np.random.normal(0, model.sigma)
            # model.opt_metric = lambda x: sum([1 for node in x.parts if abs(x["NDEMS"][node] - x["NREPS"][node]) / (x["NDEMS"][node] + x["NREPS"][node] + 1e-9) < 0.1]) / len(x) + np.random.normal(0, model.sigma)
        elif model.intervention == 'Compact':
            model.opt_metric = lambda x: (sum([4 * np.pi * (x["area"][node] / (x["perimeter"][node] ** 2 + 1e-9)) for node in x.parts]) / len(x))
        else:
            model.opt_metric = lambda x: (abs((sum([1 for node in x.parts if x["NDEMS"][node] > x["NREPS"][node]]) / len(x)) - (model.ndems / (model.ndems + model.nreps)))) + np.random.normal(0,  model.sigma)
    
    if model.control == "Fair" and model.intervention == "None":
        maximize = False # Minimize the difference between the number of Democrats and Republicans
    else:
        maximize = True

    model.map_generator = SingleMetricOptimizer(
        initial_state=initial_partition,
        proposal=proposal,
        constraints=state_constraints,
        optimization_metric=model.opt_metric,
        maximize=maximize,
    )

def find_best_plan(model):
    setup_gerrychain(model)
    best_score = -1
    best_step = 0 # Keep track at which step the best plan was found
    change_cnt = 0
    for i, part in enumerate(model.map_generator.tilted_run(model.ensemble_size, 0.1, with_progress_bar=False)):
    # ALTERNATIVE GENERATION ALGORITHMS
    # for i, part in enumerate(model.map_generator.short_bursts(10, 100, with_progress_bar=True)):
    # for i, part in enumerate(model.map_generator.simulated_annealing(model.ensemble_size, model.map_generator.jumpcycle_beta_function(200, 800), beta_magnitude=1, with_progress_bar=True)):
        new_score = model.opt_metric(part)
        if new_score > best_score:
            best_score = new_score
            if model.control == "Fair":
                model.predicted_seats = 0
            elif model.control == "Republicans":
                model.predicted_seats = sum([1 for node in part.parts if part["NREPS"][node] > part["NDEMS"][node]])
            elif model.control == "Democrats":
                model.predicted_seats = sum([1 for node in part.parts if part["NDEMS"][node] > part["NREPS"][node]])
            print(f'Found new best plan at step {i} with a score of {best_score} and {model.predicted_seats} seats in favor of {model.control}')
            best_step = i
            change_cnt += 1
    if model.print: print(f'The {model.control} have found the best plan at step {best_step} with a score of {model.map_score} after {change_cnt} changes')
    model.current_map['NEW_CONGDIST'] = model.map_generator.best_part.assignment
    model.current_map['NEW_CONGDIST'] = model.current_map['NEW_CONGDIST'].apply(lambda x: str(int(x) + 1).zfill(2))
    model.map_score = best_score

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
