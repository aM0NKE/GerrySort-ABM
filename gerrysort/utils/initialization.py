from ..agents.person import PersonAgent
from ..agents.geo_unit import GeoAgent

import mesa_geo as mg
import mesa

import geopandas as gpd
import os
from math import ceil
import random
import uuid

def load_data(model, state, data):
    model.state = state
    if data is None:
        data = gpd.read_file(os.path.join('gerrysort/data/processed', state + '.geojson'))
    if len(data[~data.geometry.is_valid]) != 0:
        data['geometry'] = data.geometry.buffer(0)
    model.data = data.to_crs(model.space.crs)
    assert model.data.crs == model.space.crs, f'CRS mismatch: data=({model.precincts.crs}); space=({model.fitness_landscape.crs})'

def setup_datacollector(model):
    model.unhappy = 0
    model.unhappyreps = 0
    model.unhappydems = 0
    model.happy = 0
    model.happydems = 0
    model.happyreps = 0
    model.total_moves = 0
    
    model.rep_congdist_seats = 0
    model.dem_congdist_seats = 0
    model.tied_congdist_seats = 0

    model.rep_legdist_seats = 0
    model.dem_legdist_seats = 0
    model.tied_legdist_seats = 0

    model.rep_sendist_seats = 0
    model.dem_sendist_seats = 0
    model.tied_sendist_seats = 0

    model.segregation = 0
    model.competitiveness = 0
    model.competitive_seats = 0
    model.compactness = 0

    model.efficiency_gap = 0
    model.mean_median = 0
    model.declination = 0

    model.projected_winner = None
    model.projected_margin = 0
    model.variance = 0
    model.change_map = 0
    model.datacollector = mesa.DataCollector(
        {'unhappy': 'unhappy', 
        'unhappyreps': 'unhappyreps',
        'unhappydems': 'unhappydems',
        'happy': 'happy',
        'happyreps': 'happyreps',
        'happydems': 'happydems',
        'rep_congdist_seats': 'rep_congdist_seats',
        'dem_congdist_seats': 'dem_congdist_seats',
        'tied_congdist_seats': 'tied_congdist_seats',
        'rep_legdist_seats': 'rep_legdist_seats',
        'dem_legdist_seats': 'dem_legdist_seats',
        'tied_legdist_seats': 'tied_legdist_seats',
        'rep_sendist_seats': 'rep_sendist_seats',
        'dem_sendist_seats': 'dem_sendist_seats',
        'tied_sendist_seats': 'tied_sendist_seats',
        'segregation': 'segregation',
        'competitiveness': 'competitiveness',
        'competitive_seats': 'competitive_seats',
        'compactness': 'compactness',
        'efficiency_gap': 'efficiency_gap',
        'mean_median': 'mean_median',
        'declination': 'declination',
        'projected_winner': 'projected_winner',
        'projected_margin': 'projected_margin',
        'control': 'control',
        'total_moves': 'total_moves',
        'variance': 'variance',
        'change_map': 'change_map'
        })

def create_precincts(model):
    # Select relevant columns
    precinct_data = model.data[['VTDID', 'COUNTY_NAME', 'COUNTYFP',
                                'CONGDIST', 'SENDIST', 'LEGDIST', 'TOTPOP', 
                                f'{model.election}R', f'{model.election}D', f'{model.election}TOT', 'geometry']]
    
    # Create precinct agents and add to the model
    ac_precincts = mg.AgentCreator(GeoAgent, model=model, agent_kwargs={'type': 'precinct'})
    model.precincts = ac_precincts.from_GeoDataFrame(precinct_data, unique_id='VTDID')
    model.num_precincts = len(model.precincts)
    model.space.add_precincts(model.precincts)
    print(f'{model.num_precincts} precincts added.')

def create_counties(model):
    # Select relevant columns
    county_data = model.data[['COUNTY_NAME', 'COUNTYFP', 
                            f'{model.election}R', f'{model.election}D', f'{model.election}TOT',
                            'COUNTY_RUCACAT', 'COUNTY_HOUSEHOLDS', 'COUNTY_HOUSING_UNITS', 
                            'COUNTY_TOTPOP', 'COUNTY_TOTPOP_SHARE', 'COUNTY_CAPACITY', 'geometry']]
    
    # Aggregate data by county
    agg_funcs = {
        'COUNTY_NAME': 'first',
        f'{model.election}R': 'sum',
        f'{model.election}D': 'sum',
        f'{model.election}TOT': 'sum',
        'COUNTY_RUCACAT': 'first',
        'COUNTY_HOUSEHOLDS': 'first',
        'COUNTY_HOUSING_UNITS': 'first',
        'COUNTY_TOTPOP': 'first',
        'COUNTY_TOTPOP_SHARE': 'first',
        'COUNTY_CAPACITY': 'first',
    }
    county_data = county_data.dissolve(by='COUNTYFP', aggfunc=agg_funcs).reset_index()
   
   # Create county agents and add to the model
    ac_c = mg.AgentCreator(GeoAgent, model=model, agent_kwargs={'type': 'county'})
    model.counties = ac_c.from_GeoDataFrame(county_data, unique_id='COUNTY_NAME')
    model.n_counties = len(model.counties)
    model.space.add_counties(model.counties)
    print(f'{model.n_counties} counties added.')

def create_state_legislatures(model):
    # Add state house districts
    legdist_data = model.data[['LEGDIST', f'{model.election}R', f'{model.election}D', f'{model.election}TOT', 'geometry']]
    legdist_data = legdist_data.dissolve(by='LEGDIST', aggfunc='sum').reset_index()
    ac_legdist = mg.AgentCreator(GeoAgent, model=model, agent_kwargs={'type': 'state_house'})
    model.legdists = ac_legdist.from_GeoDataFrame(legdist_data, unique_id='LEGDIST')
    model.num_legdists = len(model.legdists)
    model.space.add_legdists(model.legdists)
    print(f'{model.num_legdists} state legislative districts added.')
    
    # Add state senate districts
    sendist_data = model.data[['SENDIST', f'{model.election}R', f'{model.election}D', f'{model.election}TOT', 'geometry']]
    sendist_data = sendist_data.dissolve(by='SENDIST', aggfunc='sum').reset_index()
    ac_sendist = mg.AgentCreator(GeoAgent, model=model, agent_kwargs={'type': 'state_senate'})
    model.sendists = ac_sendist.from_GeoDataFrame(sendist_data, unique_id='SENDIST')
    model.num_sendists = len(model.sendists)
    model.space.add_sendists(model.sendists)
    print(f'{model.num_sendists} state senate districts added.')

def create_congressional_districts(model):
    # Select relevant columns and aggregate data by congressional district
    congdist_data = model.data[['CONGDIST', f'{model.election}R', f'{model.election}D', f'{model.election}TOT', 'geometry']]
    congdist_data = congdist_data.dissolve(by='CONGDIST', aggfunc='sum').reset_index()
    
    # Create congressional district agents and add to the model
    ac_congdist = mg.AgentCreator(GeoAgent, model=model, agent_kwargs={'type': 'congressional'})
    model.congdists = ac_congdist.from_GeoDataFrame(congdist_data, unique_id='CONGDIST')
    model.num_congdists = len(model.congdists)
    model.space.add_congdists(model.congdists)
    print(f'{model.num_congdists} congressional districts added')

def create_population(model):
    # Initialize model state variables
    model.population = []
    model.ndems = 0
    model.nreps = 0
    model.total_cap = 0
    
    # Add people to the model
    for county in model.counties:
        # Determine initial number of people in the county
        pop_county = ceil(county.COUNTY_TOTPOP_SHARE * model.npop)
        # Set county capacity (update state total capacity)
        county.capacity = ceil((county.COUNTY_CAPACITY / county.COUNTY_TOTPOP) * pop_county * model.capacity_mul)
        model.total_cap += county.capacity
        # print(f'{county.unique_id} County has {pop_county} people and {county.capacity} capacity')
        # Make dictionary of PRECINT_ID:USPRSTOTAL for each precinct in the county
        precincts = {precinct: model.space.get_precinct_by_id(precinct).TOTPOP for precinct in county.precincts}
        # Set all TOTPOP values of nan to 0
        precincts = {k: v if v == v else 0 for k, v in precincts.items()}
        # Make a probability distribution of precincts based on population
        precinct_probs = {precinct: precincts[precinct] / sum(precincts.values()) for precinct in precincts}
        # Determine ratio of Republicans to Democrats in the county
        rep_v_dem_ratio = getattr(county, f"{model.election}R") / (getattr(county, f"{model.election}D") + getattr(county, f"{model.election}R"))
        for _ in range(pop_county):
            # Select precinct based on population distribution
            random_precinct_id = random.choices(list(precinct_probs.keys()), weights=list(precinct_probs.values()))[0]
            random_precinct = model.space.get_precinct_by_id(random_precinct_id)
            person = PersonAgent(
                unique_id=uuid.uuid4().int,
                model=model,
                crs=model.space.crs,
                geometry=random_precinct.random_point(), # put in precinct
                is_red=rep_v_dem_ratio > random.random(),
                precinct_id=random_precinct.unique_id,
                county_id=model.space.precinct_county_map[random_precinct.unique_id],
                congdist_id=model.space.precinct_congdist_map[random_precinct.unique_id],
                legdist_id=model.space.precinct_legdist_map[random_precinct.unique_id],
                sendist_id=model.space.precinct_sendist_map[random_precinct.unique_id]
            )
            model.space.add_person_to_space(person, new_precinct_id=random_precinct_id)
            model.schedule.add(person)
            model.population.append(person)
            # Update party counts
            if person.color == 'Red':
                model.nreps += 1
            elif person.color == 'Blue':
                model.ndems += 1
    
    # Add people to the space
    model.space.add_agents(model.population)
    model.npop = len(model.population)
    print(f'Number of people added: {model.npop}')
    