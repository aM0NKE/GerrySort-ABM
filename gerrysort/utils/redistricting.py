from ..agents.district import DistrictAgent
from .statistics import *

import random

def redistrict(model, new_geometry):
    '''
    Update the boundaries of the districts based on new_districts GeoDataFrame.

    new_geometry: list of new geometries for each district (in the same order as the districts)
    '''
    for i, district in enumerate(model.USHouseDistricts):
        district.update_district_geometry(new_geometry[i])
        district.update_district_data()
        district.update_district_color()

def evaluate_plans(model):
    '''
    Evaluate the ensemble of plans by all possible metrics.

    ensemble: GeoDataFrame of all the potential plans generated for the current redistricting step
    '''
    # Update statistics for the current plan after self-sorting
    model.update_statistics(statistics=[red_congressional_seats, blue_congressional_seats, tied_congressional_seats, 
                                             efficiency_gap, mean_median, declination])
    results = {}
    results['-1'] = {
            'district': [district.unique_id for district in model.USHouseDistricts],
            'geometry': [district.geometry for district in model.USHouseDistricts],
            'red_congressional_seats': model.red_congressional_seats,
            'blue_congressional_seats': model.blue_congressional_seats,
            'tied_congressional_seats': model.tied_congressional_seats,
            'efficiency_gap': model.efficiency_gap,
            'mean_median': model.mean_median,
            'declination': model.declination
        }
    
    plans = []
    plan_n = random.choice(model.ensemble['plan'].unique())
    while len(plans) < model.n_proposed_maps:
        # Select a random plan
        while plan_n in plans:
            plan_n = random.choice(model.ensemble['plan'].unique())
        plans.append(plan_n)

        # Evaluate the plan
        new_geometry = model.ensemble[model.ensemble['plan'] == plan_n]['geometry'].values
        redistrict(model, new_geometry)
        model.update_statistics(statistics=[red_congressional_seats, blue_congressional_seats, tied_congressional_seats, 
                                            efficiency_gap, mean_median, declination])
        # Save the results
        results[f'{plan_n}'] = {
            'district': [district.unique_id for district in model.USHouseDistricts],
            'geometry': [district.geometry for district in model.USHouseDistricts],
            'red_congressional_seats': model.red_congressional_seats,
            'blue_congressional_seats': model.blue_congressional_seats,
            'tied_congressional_seats': model.tied_congressional_seats,
            'efficiency_gap': model.efficiency_gap,
            'mean_median': model.mean_median,
            'declination': model.declination
        }
    return results

def random_redistricting(model):
    '''
    Draws a random plan from the ensemble and sets it as new plan.
    '''
    plan_n = random.choice(model.ensemble['plan'].unique())
    new_geometry = model.ensemble[model.ensemble['plan'] == plan_n]['geometry'].values
    redistrict(model, new_geometry)
