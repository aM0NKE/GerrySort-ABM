import mesa_geo as mg

from ..agents.person import PersonAgent
from ..agents.district import DistrictAgent
from ..agents.county import CountyAgent

from math import ceil
import random
import uuid

def check_crs_consistency(model):
    '''
    Checks if the CRS of all GeoDataFrames are consistent.
    '''
    # TODO: add other GeoDataFrames
    assert model.fitness_landscape.crs == model.initial_plan.crs == model.state_leg_map.crs == model.state_sen_map.crs, f'CRS mismatch: fitness_landscape=({model.fitness_landscape.crs}); initial_plan=({model.initial_plan.crs}); state_leg_map=({model.state_leg_map.crs}); state_sen_map=({model.state_sen_map.crs})'
    # print('All CRS are consistent.')

def create_population(model):
    '''
    Create and add Person agents for the model.
    '''
    # Initialize population list
    model.population = []

    # Initialize party counts
    model.ndems = 0
    model.nreps = 0

    # Initialize total state capacity
    model.total_cap = 0

    # Add agents to the space per county
    for county in model.counties:

        # Determine initial number of people in the county
        pop_county = ceil(county.TOTPOP_SHR * model.npop)
        # Set county capacity (update state total capacity)
        county.capacity = ceil((county.CAPACITY / county.TOTPOP) * pop_county * model.capacity_mul)
        model.total_cap += county.capacity
        # print(f'County {county.unique_id} (District: {model.space.county_district_map[county.unique_id]}) has {pop_county} people and {county.capacity} capacity')
        rep_v_dem_ratio = county.PRES_R_2020 / (county.PRES_D_2020 + county.PRES_R_2020)
        # Add people to the county
        for _ in range(pop_county):
            person = PersonAgent(
                unique_id=uuid.uuid4().int,
                model=model,
                crs=model.space.crs,
                geometry=county.random_point(),
                is_red=rep_v_dem_ratio > random.random(),
                district_id=model.space.county_district_map[county.unique_id],
                county_id=county.unique_id,
            )
            model.space.add_person_to_county(person, new_county_id=county.unique_id)
            model.schedule.add(person)
            model.population.append(person)

            # Update party counts
            if person.is_red: 
                model.nreps += 1
            else: 
                model.ndems += 1

        # Add county to the scheduler
        model.schedule.add(county)

    # Update the number of people in the model
    model.npop = len(model.population)
    # model.update_utilities()
    # print('People created.')

def create_counties_districts(model):
    '''
    Create counties and US House districts agents for the model.

    county_id: column name for county names of dataframe consisting initial plan data
    district_id: column name for electoral district names of dataframe consisting initial plan data
    '''
    # Set up congressional electoral districts for simulating gerrymandering/electoral processes
    ac_cong = mg.AgentCreator(DistrictAgent, model=model, agent_kwargs={'type': 'congressional'})
    model.USHouseDistricts = ac_cong.from_GeoDataFrame(model.initial_plan, unique_id='CONGDIST')
    model.num_USHouseDistricts = len(model.USHouseDistricts)
    # print('# of electoral districts/counties:')
    # print('\tCongressional: ', model.num_USHouseDistricts)

    # Set up state house electoral districts for simulating state house elections
    ac_leg = mg.AgentCreator(DistrictAgent, model=model, agent_kwargs={'type': 'state-house'})
    model.StateHouseDistricts = ac_leg.from_GeoDataFrame(model.state_leg_map, unique_id='LEGDIST')
    model.num_StateHouseDistricts = len(model.StateHouseDistricts)
    # print('\tState House: ', model.num_StateHouseDistricts)
    # model.space.add_districts(model.StateHouseDistricts)

    # Set up state senate electoral districts for simulating state senate elections
    ac_sen = mg.AgentCreator(DistrictAgent, model=model, agent_kwargs={'type': 'state-senate'})
    model.StateSenateDistricts = ac_sen.from_GeoDataFrame(model.state_sen_map, unique_id='SENDIST')
    model.num_StateSenateDistricts = len(model.StateSenateDistricts)
    # print('\tState Senate: ', model.num_StateSenateDistricts)
    # model.space.add_districts(model.StateSenateDistricts)

    # Set up counties for simulating population shifts
    ac_c = mg.AgentCreator(CountyAgent, model=model)
    model.counties = ac_c.from_GeoDataFrame(model.fitness_landscape, unique_id='COUNTY')
    model.n_counties = len(model.counties)
    model.space.add_counties(model.counties)
    # print('\tCounties: ', model.n_counties)

    for district in model.USHouseDistricts:
        # Rename unique_id
        setattr(district, 'unique_id', f'{district.type}-{district.unique_id}')
        # Add districts to the scheduler
        model.schedule.add(district)

    for district in model.StateHouseDistricts:
        setattr(district, 'unique_id', f'{district.type}-{district.unique_id}')
        model.schedule.add(district)

    for district in model.StateSenateDistricts:
        setattr(district, 'unique_id', f'{district.type}-{district.unique_id}')
        model.schedule.add(district)

    # Add districts to visualization map
    model.space.add_districts(model.USHouseDistricts)

    # Update the county to congressional district map
    model.space.update_county_to_district_map(model.counties, model.USHouseDistricts)

    # print('Counties and districts created.')