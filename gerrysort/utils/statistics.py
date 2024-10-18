import numpy as np
from math import pi

def unhappy_happy(model):
    '''
    Return the number of unhappy agents in the model.
    '''
    model.unhappy = 0
    model.unhappy_red = 0
    model.unhappy_blue = 0
    model.happy = 0
    model.happy_red = 0
    model.happy_blue = 0
    for agent in model.population:
        if agent.is_unhappy:
            model.unhappy += 1
            if agent.is_red:
                model.unhappy_red += 1
            else:
                model.unhappy_blue += 1
        elif not agent.is_unhappy:
            model.happy += 1
            if agent.is_red:
                model.happy_red += 1
            else:
                model.happy_blue += 1

def n_moves(model):
    '''
    Return the number of agents that have moved in the current step.
    '''
    n_moves = 0
    for agent in model.population:
        if agent.last_moved == 0:
            n_moves += 1
    model.n_moves = n_moves

def red_congressional_seats(model):
    '''
    Return the number of US House electoral districts that favor the Republican party.
    '''
    num_red = 0
    for agent in model.USHouseDistricts:
        if agent.red_pct > 0.5:
            num_red += 1
    model.red_congressional_seats = num_red

def blue_congressional_seats(model):
    '''
    Return the number of US House electoral districts that favor the Democratic party.
    '''
    num_blue = 0
    for agent in model.USHouseDistricts:
        if agent.red_pct < 0.5:
            num_blue += 1
    model.blue_congressional_seats = num_blue

def tied_congressional_seats(model):
    '''
    Return the number of US House electoral districts that are tied.
    '''
    model.tied_congressional_seats = model.num_USHouseDistricts - model.red_congressional_seats - model.blue_congressional_seats

def red_state_house_seats(model):
    '''
    Return the number of state house seats that favor the Republican party.
    '''
    num_red = 0
    for agent in model.StateHouseDistricts:
        if agent.red_pct > 0.5:
            num_red += 1
    model.red_state_house_seats = num_red

def blue_state_house_seats(model):
    '''
    Return the number of state house seats that favor the Democratic party.
    '''
    num_blue = 0
    for agent in model.StateHouseDistricts:
        if agent.red_pct < 0.5:
            num_blue += 1
    model.blue_state_house_seats = num_blue

def tied_state_house_seats(model):
    '''
    Return the number of state house seats that are tied.
    '''
    model.tied_state_house_seats = model.num_StateHouseDistricts - model.red_state_house_seats - model.blue_state_house_seats

def red_state_senate_seats(model):
    '''
    Return the number of state senate seats that favor the Republican party.
    '''
    num_red = 0
    for agent in model.StateSenateDistricts:
        if agent.red_pct > 0.5:
            num_red += 1
    model.red_state_senate_seats = num_red

def blue_state_senate_seats(model):
    '''
    Return the number of state senate seats that favor the Democratic party.
    '''
    num_blue = 0
    for agent in model.StateSenateDistricts:
        if agent.red_pct < 0.5:
            num_blue += 1
    model.blue_state_senate_seats = num_blue

def tied_state_senate_seats(model):
    '''
    Return the number of state senate seats that are tied.
    '''
    model.tied_state_senate_seats = model.num_StateSenateDistricts - model.red_state_senate_seats - model.blue_state_senate_seats

def projected_winner(model):
    '''
    Returns the party that has both a majority in state house and senate.
    (Returns 'Tied' if no party has a majority in both chambers)
    '''
    if model.red_state_house_seats > model.blue_state_house_seats:
        if model.red_state_senate_seats > model.blue_state_senate_seats:
            model.projected_winner = 'Republican'
    elif model.red_state_house_seats < model.blue_state_house_seats:
        if model.red_state_senate_seats < model.blue_state_senate_seats:
            model.projected_winner = 'Democratic'
    else:
        model.projected_winner = 'Tied'

def projected_margin(model):
    '''
    Returns the margin of the projected winner in the state.
    '''
    if model.projected_winner == 'Republican':
        model.projected_margin = (model.red_state_house_seats - model.blue_state_house_seats) + (model.red_state_senate_seats - model.blue_state_senate_seats)
    elif model.projected_winner == 'Democratic':
        model.projected_margin = (model.blue_state_house_seats - model.red_state_house_seats) + (model.blue_state_senate_seats - model.red_state_senate_seats)
    else:
        model.projected_margin = 0

# Three common gerrymandering quantifications: efficiency gap, mean-median difference, and declination
def efficiency_gap(model):
    '''
    Return the efficiency gap of the plan and population distribution at the current step.
    '''
    # Sum wasted votes for every district for each party
    total_wasted_votes_red = 0
    total_wasted_votes_blue = 0
    for agent in model.USHouseDistricts:
        red_wasted_votes, blue_wasted_votes = agent.calculate_wasted_votes()
        total_wasted_votes_red += red_wasted_votes
        total_wasted_votes_blue += blue_wasted_votes

    # Calculate efficiency gap
    model.efficiency_gap = (total_wasted_votes_blue - total_wasted_votes_red) / model.npop

def mean_median(model):
    '''
    Return the mean-median difference of the plan and population distribution at the current step.
    '''
    # Get dem vote shares (1 - red_pct) for each district
    dem_pct = [1 - agent.red_pct for agent in model.USHouseDistricts]

    # Sort dem vote shares over all districts
    dem_pct.sort()

    # Calculate median
    n = len(dem_pct)
    if n % 2 == 1:
        # Odd number of districts, take the middle one
        median = dem_pct[n // 2]
    else:
        # Even number of districts, take the average of the two middle ones
        median = (dem_pct[n // 2 - 1] + dem_pct[n // 2]) / 2

    # Calculate mean
    mean = sum(dem_pct) / n

    # Store and return the mean-median difference
    model.mean_median = mean - median

def declination(model):
    '''
    Return the declination of the plan and population distribution at the current step.
    '''
    # Get democratic vote share for each republican and democrat districts
    rep_districts_dem_pct = [1 - district.red_pct for district in model.USHouseDistricts if district.red_pct > 0.5] # NOTE: Tied districts are not included
    dem_districts_dem_pct = [1 - district.red_pct for district in model.USHouseDistricts if district.red_pct < 0.5]

    # Sort districts by democratic vote share (1 - red_pct)
    rep_districts_dem_pct.sort()
    dem_districts_dem_pct.sort()

    # Find the number of rep and dem districts
    n_rep = len(rep_districts_dem_pct)
    n_dem = len(dem_districts_dem_pct)
    
    theta_rep = np.arctan((1 - 2 * np.mean(rep_districts_dem_pct)) * (n_rep + n_dem) / len(rep_districts_dem_pct))
    theta_dem = np.arctan((2 * np.mean(dem_districts_dem_pct) - 1) * (n_rep + n_dem) / len(dem_districts_dem_pct))

    # Calculate declination
    model.declination = 2 * (theta_dem - theta_rep) / pi

def variance(model):
    '''
    Calculate the variance of the population distribution across electoral districts.
    '''
    # Calculate the population variance
    population_cnts = [district.num_people for district in model.USHouseDistricts]
    mean_population = sum(population_cnts) / len(population_cnts)
    model.variance = sum((x - mean_population) ** 2 for x in population_cnts) / len(population_cnts)

def change_map(model, old_map, new_map):
    '''
    Calculate the change in map square kilometers per district (energy) between two maps.
    '''
    model.change_map = 0
    for i in range(model.num_USHouseDistricts):
        old_map_district_area = old_map['geometry'][i].area # TODO: Check the units of the area
        new_map_district_area = new_map['geometry'][i].area
        district_change = abs(new_map_district_area - old_map_district_area)
        model.change_map += district_change