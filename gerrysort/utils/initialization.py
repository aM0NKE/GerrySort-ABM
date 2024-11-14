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
        data = gpd.read_file(os.path.join('gerrysort/data', state, state + '_precincts_election_results_2020.geojson'))
    model.data = data.to_crs(model.space.crs)
    assert model.data.crs == model.space.crs, f'CRS mismatch: data=({model.precincts.crs}); space=({model.fitness_landscape.crs})'

def setup_datacollector(model):
    model.unhappy = 0
    model.unhappy_rep = 0
    model.unhappy_dem = 0
    model.happy = 0
    model.happy_dem = 0
    model.happy_rep = 0
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

    model.efficiency_gap = 0
    model.mean_median = 0
    model.declination = 0

    model.projected_winner = None
    model.projected_margin = 0
    model.variance = 0
    model.change_map = 0
    model.datacollector = mesa.DataCollector(
        {'unhappy': 'unhappy', 
        'unhappy_rep': 'unhappy_rep',
        'unhappy_dem': 'unhappy_dem',
        'happy': 'happy',
        'happy_rep': 'happy_rep',
        'happy_dem': 'happy_dem',
        'rep_congdist_seats': 'rep_congdist_seats',
        'dem_congdist_seats': 'dem_congdist_seats',
        'tied_congdist_seats': 'tied_congdist_seats',
        'rep_legdist_seats': 'rep_legdist_seats',
        'dem_legdist_seats': 'dem_legdist_seats',
        'tied_legdist_seats': 'tied_legdist_seats',
        'rep_sendist_seats': 'rep_sendist_seats',
        'dem_sendist_seats': 'dem_sendist_seats',
        'tied_sendist_seats': 'tied_sendist_seats',
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
    precinct_data = model.data[['VTDID', 'PCTNAME', 'PCTCODE', 
                                'COUNTYNAME', 'COUNTYCODE', 'COUNTYFIPS', 
                                'CONGDIST', 'MNSENDIST', 'MNLEGDIST',
                                'USPRSR', 'USPRSDFL', 'USPRSTOTAL',
                                'Shape_Leng', 'Shape_Area', 'geometry']]
    
    # Create precinct agents and add to the model
    ac_precincts = mg.AgentCreator(GeoAgent, model=model, agent_kwargs={'type': 'precinct'})
    model.precincts = ac_precincts.from_GeoDataFrame(precinct_data, unique_id='VTDID')
    model.num_precincts = len(model.precincts)
    model.space.add_precincts(model.precincts)
    print(f'Number of precincts added: {model.num_precincts}')

def create_counties(model):
    # Select relevant columns
    county_data = model.data[['COUNTYNAME', 'COUNTYCODE', 'COUNTYFIPS', 
                            'USPRSR', 'USPRSDFL', 'USPRSTOTAL',
                            'RUCA', 'RUCA2', 'RUCACAT', 'HOUSEHOLDS', 
                            'HOUSING_UNITS', 'PERSONS_PER_HOUSEHOLD', 
                            'TOTPOP', 'TOTPOP_SHR', 'CAPACITY', 'CAPACITY_SHR', 
                            'POPDENS', 'REL_POPDENS', 'Shape_Leng', 'Shape_Area',
                            'geometry']]
    
    # Aggregate data by county
    agg_funcs = {
        'COUNTYCODE': 'first',
        'COUNTYFIPS': 'first',
        'USPRSR': 'sum',
        'USPRSDFL': 'sum',
        'USPRSTOTAL': 'sum',
        'RUCA': 'first',
        'RUCA2': 'first',
        'RUCACAT': 'first',
        'HOUSEHOLDS': 'first',
        'HOUSING_UNITS': 'first',
        'PERSONS_PER_HOUSEHOLD': 'first',
        'TOTPOP': 'first',
        'TOTPOP_SHR': 'first',
        'CAPACITY': 'first',
        'CAPACITY_SHR': 'first',
        'POPDENS': 'first',
        'REL_POPDENS': 'first',
        'Shape_Leng': 'sum',
        'Shape_Area': 'sum',
    }
    county_data = county_data.dissolve(by='COUNTYNAME', aggfunc=agg_funcs).reset_index()
   
   # Create county agents and add to the model
    ac_c = mg.AgentCreator(GeoAgent, model=model, agent_kwargs={'type': 'county'})
    model.counties = ac_c.from_GeoDataFrame(county_data, unique_id='COUNTYFIPS')
    model.n_counties = len(model.counties)
    model.space.add_counties(model.counties)
    print(f'Number of counties added: {model.n_counties}')

def create_state_legislatures(model):
    # Add state house districts
    legdist_data = model.data[['MNLEGDIST', 'USPRSR', 'USPRSDFL', 'USPRSTOTAL',
                            'Shape_Leng', 'Shape_Area', 'geometry']]
    legdist_data = legdist_data.dissolve(by='MNLEGDIST', aggfunc='sum').reset_index()
    ac_legdist = mg.AgentCreator(GeoAgent, model=model, agent_kwargs={'type': 'state_house'})
    model.legdists = ac_legdist.from_GeoDataFrame(legdist_data, unique_id='MNLEGDIST')
    model.num_legdists = len(model.legdists)
    model.space.add_legdists(model.legdists)
    print(f'Number of state legislative districts added: {model.num_legdists}')
    
    # Add state senate districts
    sendist_data = model.data[['MNSENDIST', 'USPRSR', 'USPRSDFL', 'USPRSTOTAL',
                            'Shape_Leng', 'Shape_Area', 'geometry']]
    sendist_data = sendist_data.dissolve(by='MNSENDIST', aggfunc='sum').reset_index()
    ac_sendist = mg.AgentCreator(GeoAgent, model=model, agent_kwargs={'type': 'state_senate'})
    model.sendists = ac_sendist.from_GeoDataFrame(sendist_data, unique_id='MNSENDIST')
    model.num_sendists = len(model.sendists)
    model.space.add_sendists(model.sendists)
    print(f'Number of state senate districts added: {model.num_sendists}')

def create_congressional_districts(model):
    # Select relevant columns and aggregate data by congressional district
    congdist_data = model.data[['CONGDIST', 'USPRSR', 'USPRSDFL', 'USPRSTOTAL',
                              'Shape_Leng', 'Shape_Area', 'geometry']]
    congdist_data = congdist_data.dissolve(by='CONGDIST', aggfunc='sum').reset_index()
    
    # Create congressional district agents and add to the model
    ac_congdist = mg.AgentCreator(GeoAgent, model=model, agent_kwargs={'type': 'congressional'})
    model.congdists = ac_congdist.from_GeoDataFrame(congdist_data, unique_id='CONGDIST')
    model.num_congdists = len(model.congdists)
    model.space.add_congdists(model.congdists)
    print(f'Number of congressional districts added: {model.num_congdists}')

def create_population(model):
    # Initialize model state variables
    model.population = []
    model.ndems = 0
    model.nreps = 0
    model.total_cap = 0
    
    # Add people to the model
    for county in model.counties:
        # Determine initial number of people in the county
        pop_county = ceil(county.TOTPOP_SHR * model.npop)
        # Set county capacity (update state total capacity)
        county.capacity = ceil((county.CAPACITY / county.TOTPOP) * pop_county * model.capacity_mul)
        model.total_cap += county.capacity
        # print(f'County {county.unique_id} has {pop_county} people and {county.capacity} capacity')
        # Make dictionary of PRECINT_ID:USPRSTOTAL for each precinct in the county
        precincts = {precinct: model.space.get_precinct_by_id(precinct).USPRSTOTAL for precinct in county.precincts}
        # Make a probability distribution of precincts based on population
        precinct_probs = {precinct: precincts[precinct] / sum(precincts.values()) for precinct in precincts}
        # Determine ratio of Republicans to Democrats in the county
        rep_v_dem_ratio = county.USPRSR / (county.USPRSDFL + county.USPRSR)
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
    