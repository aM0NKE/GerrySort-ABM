import numpy as np
from math import pi

def unhappy_happy(model):
    model.unhappy = 0
    model.unhappyreps = 0
    model.unhappydems = 0
    model.happy = 0
    model.happyreps = 0
    model.happydems = 0
    for agent in model.population:
        if agent.is_unhappy:
            model.unhappy += 1
            if agent.color == 'Red':
                model.unhappyreps += 1
            elif agent.color == 'Blue':
                model.unhappydems += 1
        elif not agent.is_unhappy:
            model.happy += 1
            if agent.color == 'Red':
                model.happyreps += 1
            elif agent.color == 'Blue':
                model.happydems += 1

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
    model.rep_legdist_seats = 0
    model.dem_legdist_seats = 0
    model.tied_legdist_seats = 0
    for dist in model.legdists:
        if dist.color == 'Red':
            model.rep_legdist_seats += 1
        elif dist.color == 'Blue':
            model.dem_legdist_seats += 1
        else:
            model.tied_legdist_seats += 1

def sendist_seats(model):
    model.rep_sendist_seats = 0
    model.dem_sendist_seats = 0
    model.tied_sendist_seats = 0
    for dist in model.sendists:
        if dist.color == 'Red':
            model.rep_sendist_seats += 1
        elif dist.color == 'Blue':
            model.dem_sendist_seats += 1
        else:
            model.tied_sendist_seats += 1

def projected_winner(model):
    if model.control_rule == 'STATELEG':
        if model.rep_legdist_seats > model.dem_legdist_seats:
            if model.rep_sendist_seats > model.dem_sendist_seats:
                model.projected_winner = 'Republican'
            else:
                model.projected_winner = 'Tied'
        elif model.dem_legdist_seats > model.rep_legdist_seats:
            if model.dem_sendist_seats > model.rep_sendist_seats:
                model.projected_winner = 'Democratic'
            else:
                model.projected_winner = 'Tied'
    
    elif model.control_rule == 'CONGDIST':
        # NOTE: Alternative option (only considers the US House)
        if model.rep_congdist_seats > model.dem_congdist_seats:
            model.projected_winner = 'Republican'
        elif model.rep_congdist_seats < model.dem_congdist_seats:
            model.projected_winner = 'Democratic'
        else:
            model.projected_winner = 'Tied'
    
def projected_margin(model):
    if model.control_rule == 'STATELEG':
        if model.projected_winner == 'Republican':
            model.projected_margin = (model.rep_legdist_seats - model.dem_legdist_seats) + (model.rep_sendist_seats - model.dem_sendist_seats)
        elif model.projected_winner == 'Democratic':
            model.projected_margin = (model.dem_legdist_seats - model.rep_legdist_seats) + (model.dem_sendist_seats - model.rep_sendist_seats)
        else:
            model.projected_margin = 0

    elif model.control_rule == 'CONGDIST':
        # NOTE: Alternative option (only considers the US House)
        if model.projected_winner == 'Republican':
            model.projected_margin = model.rep_congdist_seats - model.dem_congdist_seats
        elif model.projected_winner == 'Democratic':
            model.projected_margin = model.dem_congdist_seats - model.rep_congdist_seats
        else:
            model.projected_margin = 0

    elif model.control_rule == 'FIXED':
        model.projected_margin = 'FIXED'

def variance(model): # TODO: turn this into % max population deviation
    population_cnts = [district.num_people for district in model.congdists]
    mean_population = sum(population_cnts) / len(population_cnts)
    model.variance = sum((x - mean_population) ** 2 for x in population_cnts) / len(population_cnts)

def segregation(model):
    scores = []
    for precinct in model.precincts:
        precinct_population = precinct.dems + precinct.reps
        for person in precinct_population:
            same_color = []
            for person2 in precinct_population:
                if person == person2:
                    continue
                if model.space.get_person_by_id(person).color == model.space.get_person_by_id(person2).color:
                    same_color.append(person2)
            score = len(same_color) / len(precinct_population)
            scores.append(score)
    model.segregation = sum(scores) / len(scores)

def compactness(model):
    pass

def competitiveness(model, competitive_threshold=0.10):
    competitiveness_list = []
    for dist in model.congdists:
        # print(f'Calculating competitiveness of district {dist.unique_id}...')
        # Callculate competitiveness score of district
        dem_voteshare = dist.dem_cnt / dist.num_people
        rep_voteshare = dist.rep_cnt / dist.num_people
        # print(f'Dem vote share: {dem_voteshare}')
        # print(f'Rep vote share: {rep_voteshare}')
        competitiveness = 1 - abs(dem_voteshare - rep_voteshare)
        # print(f'Competitiveness score: {competitiveness}')
        competitiveness_list.append(competitiveness)
        # Set district competitiveness boolean
        margin_of_victory = abs(dem_voteshare - rep_voteshare)
        # print(f'Margin of victory: {margin_of_victory}')
        dist.competitive = margin_of_victory < competitive_threshold
        # print(f'Is Competitive: {dist.competitive}')

    # Update average model competitiveness
    model.competitiveness = sum(competitiveness_list) / len(competitiveness_list)   

    # Update total number of competitive districts
    model.competitive_seats = 0
    for dist in model.congdists:
        if dist.competitive == True:
            model.competitive_seats += 1

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

def update_statistics(model, statistics=[unhappy_happy, congdist_seats,
                                        legdist_seats, sendist_seats, variance,
                                        segregation, competitiveness, compactness,
                                        efficiency_gap, mean_median, declination,
                                        projected_winner, projected_margin]):
    for stat in statistics:
        stat(model)

def print_statistics(model):
    print('Statistics:')
    print(f'\tUnhappy: {model.unhappy} | Unhappy Red: {model.unhappyreps} | Unhappy Blue: {model.unhappydems}')
    print(f'\tHappy: {model.happy} | Happy Red: {model.happyreps} | Happy Blue: {model.happydems}')
    print(f'\tRed Congressional Seats: {model.rep_congdist_seats} | Blue Congressional Seats: {model.dem_congdist_seats} | Tied Congressional Seats: {model.tied_congdist_seats}')
    print(f'\tPopulation counts: {[district.num_people for district in model.congdists]}')
    print(f'\tVariance: {model.variance}')
    print(f'\tRed State House Seats: {model.rep_legdist_seats} | Blue State House Seats: {model.dem_legdist_seats} | Tied State House Seats: {model.tied_sendist_seats}')
    print(f'\tRed State Senate Seats: {model.rep_sendist_seats} | Blue State Senate Seats: {model.dem_sendist_seats} | Tied State Senate Seats: {model.tied_sendist_seats}')
    print(f'\tEfficiency Gap: {model.efficiency_gap}')
    print(f'\tMean Median: {model.mean_median}')
    print(f'\tDeclination: {model.declination}')
    print(f'\tControl: {model.control}')
    print(f'\tProjected Winner: {model.projected_winner}')
    print(f'\tProjected Margin: {model.projected_margin}')
    print(f'\t[ENERGY] Number of Moves: {model.total_moves}')
    print(f'\t[ENERGY] % Reassigned Precincts: {model.change_map}')
    # print('Capacity counties:')
    # [print(f'\t{county.unique_id}: {county.num_people}/{county.capacity}') for county in model.counties]