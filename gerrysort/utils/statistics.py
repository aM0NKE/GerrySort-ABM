import numpy as np
from math import pi

def unhappy_happy(model):
    model.unhappy = 0
    model.unhappy_rep = 0
    model.unhappy_dem = 0
    model.happy = 0
    model.happy_rep = 0
    model.happy_dem = 0
    for agent in model.population:
        if agent.is_unhappy:
            model.unhappy += 1
            if agent.color == 'Red':
                model.unhappy_rep += 1
            elif agent.color == 'Blue':
                model.unhappy_dem += 1
        elif not agent.is_unhappy:
            model.happy += 1
            if agent.color == 'Red':
                model.happy_rep += 1
            elif agent.color == 'Blue':
                model.happy_dem += 1

def congdist_seats(model):
    model.rep_congdist_seats = 0
    model.dem_congdist_seats = 0
    model.tied_congdist_seats = 0
    for dist in model.congdists:
        if dist.color == 'Red':
            model.rep_congdist_seats += 1
        elif dist.color == 'Blue':
            model.dem_congdist_seats += 1
        else:
            model.tied_congdist_seats += 1

def legdist_seats(model):
    model.red_legdist_seats = 0
    model.blue_legdist_seats = 0
    model.tied_legdist_seats = 0
    for dist in model.legdists:
        if dist.color == 'Red':
            model.red_legdist_seats += 1
        elif dist.color == 'Blue':
            model.blue_legdist_seats += 1
        else:
            model.tied_legdist_seats += 1

def sendist_seats(model):
    model.red_sendist_seats = 0
    model.blue_sendist_seats = 0
    model.tied_sendist_seats = 0
    for dist in model.sendists:
        if dist.color == 'Red':
            model.red_sendist_seats += 1
        elif dist.color == 'Blue':
            model.blue_sendist_seats += 1
        else:
            model.tied_sendist_seats += 1

def projected_winner(model):
    # if model.rep_legdist_seats > model.dem_legdist_seats:
    #     if model.rep_sendist_seats > model.dem_sendist_seats:
    #         model.projected_winner = 'Republican'
    # elif model.rep_legdist_seats < model.dem_legdist_seats:
    #     if model.rep_sendist_seats < model.dem_sendist_seats:
    #         model.projected_winner = 'Democratic'
    # else:
    #     model.projected_winner = 'Tied'

    # NOTE: Alternative option (only considers the US House)
    if model.rep_congdist_seats > model.dem_congdist_seats:
        model.projected_winner = 'Republican'
    elif model.rep_congdist_seats < model.dem_congdist_seats:
        model.projected_winner = 'Democratic'
    else:
        model.projected_winner = 'Tied'
    
def projected_margin(model):
    # if model.projected_winner == 'Republican':
    #     model.projected_margin = (model.rep_legdist_seats - model.dem_legdist_seats) + (model.rep_sendist_seats - model.dem_sendist_seats)
    # elif model.projected_winner == 'Democratic':
    #     model.projected_margin = (model.dem_legdist_seats - model.rep_legdist_seats) + (model.dem_sendist_seats - model.rep_sendist_seats)
    # else:
    #     model.projected_margin = 0

    # NOTE: Alternative option (only considers the US House)
    if model.projected_winner == 'Republican':
        model.projected_margin = model.rep_congdist_seats - model.dem_congdist_seats
    elif model.projected_winner == 'Democratic':
        model.projected_margin = model.dem_congdist_seats - model.rep_congdist_seats
    else:
        model.projected_margin = 0

def variance(model):
    population_cnts = [district.num_people for district in model.congdists]
    mean_population = sum(population_cnts) / len(population_cnts)
    model.variance = sum((x - mean_population) ** 2 for x in population_cnts) / len(population_cnts)

'''
GERRYMANDERING QUANTIFICATION METRICS
'''
def efficiency_gap(model):
    # Sum wasted votes for every district for each party
    total_wasted_votes_red = 0
    total_wasted_votes_blue = 0
    for dist in model.congdists:
        red_wasted_votes, blue_wasted_votes = dist.calculate_wasted_votes()
        total_wasted_votes_red += red_wasted_votes
        total_wasted_votes_blue += blue_wasted_votes
    # Calculate efficiency gap
    model.efficiency_gap = (total_wasted_votes_blue - total_wasted_votes_red) / model.npop

def mean_median(model):
    # Get dem vote shares (1 - red_pct) for each district
    dem_pct = [1 - (dist.rep_cnt / dist.num_people) for dist in model.congdists]
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
    # Get democratic vote share for each republican and democrat districts
    rep_districts_dem_pct = [1 - (dist.rep_cnt / dist.num_people) for dist in model.congdists if (dist.rep_cnt / dist.num_people) > 0.5] # NOTE: Tied districts are not included
    dem_districts_dem_pct = [1 - (dist.rep_cnt / dist.num_people) for dist in model.congdists if (dist.rep_cnt / dist.num_people) < 0.5]
    # Sort districts by democratic vote share (1 - red_pct)
    rep_districts_dem_pct.sort()
    dem_districts_dem_pct.sort()
    # Find the number of rep and dem districts
    n_rep = len(rep_districts_dem_pct)
    n_dem = len(dem_districts_dem_pct)
    # Calculate angles
    theta_rep = np.arctan((1 - 2 * np.mean(rep_districts_dem_pct)) * (n_rep + n_dem) / len(rep_districts_dem_pct))
    theta_dem = np.arctan((2 * np.mean(dem_districts_dem_pct) - 1) * (n_rep + n_dem) / len(dem_districts_dem_pct))
    # Calculate declination
    model.declination = 2 * (theta_dem - theta_rep) / pi
