import numpy as np
from math import pi

def unhappy_happy(model):
    counts = {"unhappy": 0, "happy": 0, "unhappyreps": 0, "unhappydems": 0, "happyreps": 0, "happydems": 0}
    for agent in model.population:
        key_prefix = "unhappy" if agent.is_unhappy else "happy"
        counts[key_prefix] += 1
        if agent.color == 'Red':
            counts[f"{key_prefix}reps"] += 1
        elif agent.color == 'Blue':
            counts[f"{key_prefix}dems"] += 1
    vars(model).update(counts)

def avg_utility(model):
    model.avg_utility = np.mean([agent.utility for agent in model.population])

def district_seats(model, district_attr, rep_attr, dem_attr, tied_attr):
    counts = {rep_attr: 0, dem_attr: 0, tied_attr: 0}
    for dist in getattr(model, district_attr):
        if dist.color == 'Red':
            counts[rep_attr] += 1
        elif dist.color == 'Blue':
            counts[dem_attr] += 1
        else:
            counts[tied_attr] += 1

    for key, value in counts.items():
        setattr(model, key, value)

def congdist_seats(model):
    district_seats(model, 'congdists', 'rep_congdist_seats', 'dem_congdist_seats', 'tied_congdist_seats')

def legdist_seats(model):
    district_seats(model, 'legdists', 'rep_legdist_seats', 'dem_legdist_seats', 'tied_legdist_seats')

def sendist_seats(model):
    district_seats(model, 'sendists', 'rep_sendist_seats', 'dem_sendist_seats', 'tied_sendist_seats')

def projected_winner(model):
    if model.control_rule == 'STATELEG':
        rep_leg_majority = model.rep_legdist_seats > model.dem_legdist_seats
        rep_sen_majority = model.rep_sendist_seats > model.dem_sendist_seats
        model.projected_winner = 'Republicans' if rep_leg_majority and rep_sen_majority else \
                                 'Democrats' if not rep_leg_majority and not rep_sen_majority else \
                                 'Fair'
    elif model.control_rule == 'CONGDIST':
        model.projected_winner = 'Republicans' if model.rep_congdist_seats > model.dem_congdist_seats else \
                                 'Democrats' if model.rep_congdist_seats < model.dem_congdist_seats else \
                                 'Fair'
    
def projected_margin(model):
    if model.projected_winner in ['Republicans', 'Democrats']:
        seat_diff = lambda x, y: abs(getattr(model, f"{x}_seats") - getattr(model, f"{y}_seats"))
        if model.control_rule == 'STATELEG':
            model.projected_margin = seat_diff('rep_legdist', 'dem_legdist') + seat_diff('rep_sendist', 'dem_sendist')
        elif model.control_rule == 'CONGDIST':
            model.projected_margin = seat_diff('rep_congdist', 'dem_congdist')
    elif model.control_rule == 'FIXED':
        model.projected_margin = 'FIXED'

def pop_deviation(model):
    ideal_population = model.npop / model.num_congdists
    pop_devs = [abs(congdist.num_people - ideal_population) / ideal_population for congdist in model.congdists]
    model.max_popdev = max(pop_devs)
    model.avg_popdev = np.mean(pop_devs)

def segregation(model):
    def calculate_majority_pct(group):
        if group.color == 'Red':
            return group.rep_cnt / group.num_people
        elif group.color == 'Blue':
            return group.dem_cnt / group.num_people
        return 0.5

    model.avg_congdist_segregation = np.mean([calculate_majority_pct(congdist) for congdist in model.congdists])
    model.avg_county_segregation = np.mean([calculate_majority_pct(county) for county in model.counties])

def compactness(model, formula='polsby_popper'):
    score_method = {
        'polsby_popper': lambda dist: dist.polsby_popper(),
        'schwartzberg': lambda dist: dist.schwartzberg()
    }
    model.avg_compactness = np.mean([score_method[formula](dist) for dist in model.congdists])

def competitiveness(model, competitive_threshold=0.10):
    competitiveness_scores = [
        1 - abs(dist.dem_cnt / dist.num_people - dist.rep_cnt / dist.num_people) for dist in model.congdists
    ]
    for dist, score in zip(model.congdists, competitiveness_scores):
        dist.competitive = abs(dist.dem_cnt / dist.num_people - dist.rep_cnt / dist.num_people) < competitive_threshold

    model.avg_competitiveness = np.mean(competitiveness_scores)
    model.competitive_seats = sum(dist.competitive for dist in model.congdists)

'''
GERRYMANDERING QUANTIFICATION METRICS
'''
def efficiency_gap(model):
    wasted_votes = [dist.calculate_wasted_votes() for dist in model.congdists]
    total_wasted_red, total_wasted_blue = map(sum, zip(*wasted_votes))
    model.efficiency_gap = (total_wasted_blue - total_wasted_red) / model.npop

def mean_median(model):
    dem_pct = sorted(dist.dem_cnt / dist.num_people for dist in model.congdists)
    median = np.median(dem_pct)
    mean = np.mean(dem_pct)
    model.mean_median = mean - median

def declination(model):
    rep_districts = [dist.dem_cnt / dist.num_people for dist in model.congdists if dist.rep_cnt / dist.num_people > 0.5]
    dem_districts = [dist.dem_cnt / dist.num_people for dist in model.congdists if dist.rep_cnt / dist.num_people < 0.5]
    theta_rep = np.arctan((1 - 2 * np.mean(rep_districts)) * len(model.congdists) / len(rep_districts))
    theta_dem = np.arctan((2 * np.mean(dem_districts) - 1) * len(model.congdists) / len(dem_districts))
    model.declination = 2 * (theta_dem - theta_rep) / pi

def update_statistics(model, statistics=[unhappy_happy, avg_utility, congdist_seats,
                                        legdist_seats, sendist_seats, pop_deviation,
                                        segregation, competitiveness, compactness,
                                        efficiency_gap, mean_median, declination,
                                        projected_winner, projected_margin]):
    for stat in statistics:
        stat(model)

def print_statistics(model):
    print(f'[ENERGY] Number of Moves: {model.total_moves}')
    print(f'[ENERGY] % Reassigned Precincts: {model.change_map}')
    print('Statistics:')
    print(f'\tControl: {model.control}')
    print(f'\tProjected Winner: {model.projected_winner}')
    print(f'\tProjected Margin: {model.projected_margin}')
    print(f'\tRed State House Seats: {model.rep_legdist_seats} | Blue State House Seats: {model.dem_legdist_seats} | Tied State House Seats: {model.tied_sendist_seats}')
    print(f'\tRed State Senate Seats: {model.rep_sendist_seats} | Blue State Senate Seats: {model.dem_sendist_seats} | Tied State Senate Seats: {model.tied_sendist_seats}')
    print(f'\tUnhappy: {model.unhappy} | Unhappy Red: {model.unhappyreps} | Unhappy Blue: {model.unhappydems}')
    print(f'\tHappy: {model.happy} | Happy Red: {model.happyreps} | Happy Blue: {model.happydems}')
    print(f'\tAverage Utility: {model.avg_utility}')
    print(f'\tRed Congressional Seats: {model.rep_congdist_seats} | Blue Congressional Seats: {model.dem_congdist_seats} | Tied Congressional Seats: {model.tied_congdist_seats}')
    print(f'\tMax Population Deviation: {model.max_popdev}')
    print(f'\tPopulation counts: {[district.num_people for district in model.congdists]}')
    print(f'\tEfficiency Gap: {model.efficiency_gap}')
    print(f'\tMean Median: {model.mean_median}')
    print(f'\tDeclination: {model.declination}')
    print(f'\tAverage County Segregation: {model.avg_county_segregation}')
    print(f'\tAverage Congressional District Segregation: {model.avg_congdist_segregation}')
    print(f'\tAverage Competitiveness: {model.avg_competitiveness}')
    print(f'\tCompetitive Seats: {model.competitive_seats}')
    print(f'\tAverage Compactness: {model.avg_compactness}')
    # print('Capacity counties:')
    # [print(f'\t{county.unique_id}: {county.num_people}/{county.capacity}') for county in model.counties]