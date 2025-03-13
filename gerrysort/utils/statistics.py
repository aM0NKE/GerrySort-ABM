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

def projected_winner(model):
    model.projected_winner = 'Republicans' if model.rep_congdist_seats > model.dem_congdist_seats else \
                             'Democrats' if model.rep_congdist_seats < model.dem_congdist_seats else \
                             'Fair'
    
def projected_margin(model):
    if model.projected_winner in ['Republicans', 'Democrats']:
        model.projected_margin = abs(model.rep_congdist_seats - model.dem_congdist_seats)
    elif model.projected_winner == 'Fair':
        model.projected_margin = 0
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
    compactness_scores = [score_method[formula](dist) for dist in model.congdists]
    for dist, score in zip(model.congdists, compactness_scores):
        dist.compactness = score
    model.min_compactness = min(compactness_scores)
    model.avg_compactness = np.mean(compactness_scores)
    model.max_compactness = max(compactness_scores)

def competitiveness(model, competitive_threshold=0.10):
    competitiveness_scores = [dist.competitiveness() for dist in model.congdists]
    for dist, score in zip(model.congdists, competitiveness_scores):
        dist.competitive = score < competitive_threshold
        dist.competitiveness_score = score
    model.min_competitiveness = min(competitiveness_scores)
    model.avg_competitiveness = np.mean(competitiveness_scores)
    model.max_competitiveness = max(competitiveness_scores)
    model.competitive_seats = sum(dist.competitive for dist in model.congdists)

'''
GERRYMANDERING QUANTIFICATION METRICS
'''
def efficiency_gap(model):
    """
        • Wasted Votes = Votes for losing candidate + Excess votes for winning candidate
        • Efficiency Gap = (Total Wasted Votes for Blue - Total Wasted Votes for Red) / Total Population
    """
    wasted_votes = [dist.calculate_wasted_votes() for dist in model.congdists]
    total_wasted_red, total_wasted_blue = map(sum, zip(*wasted_votes))
    model.efficiency_gap = (total_wasted_blue - total_wasted_red) / model.npop

def mean_median(model):
    """ 
        • Mean = average party vote share across all districts
        • Median = party vote share in the median district when districts are sorted on share of party vote 
        • Mean-Median = Mean - Median
    """
    dem_pct = sorted(dist.dem_cnt / dist.num_people for dist in model.congdists)
    median = np.median(dem_pct)
    mean = np.mean(dem_pct)
    model.mean_median = mean - median

def declination(model):
    """
        • Theta_dem = Angle between horizontally halfway and the average dem_pct in democratic districts
        • Theta_rep = Angle between horizontally halfway and the average dem_pct in republican districts
        • Declination = 2 * (Theta_dem - Theta_rep) / pi
    """
    dem_districts = [dist.dem_cnt / dist.num_people for dist in model.congdists if dist.rep_cnt / dist.num_people < 0.5]
    theta_dem = np.arctan((2 * np.mean(dem_districts) - 1) / (len(dem_districts) / len(model.congdists)))
    rep_districts = [dist.dem_cnt / dist.num_people for dist in model.congdists if dist.rep_cnt / dist.num_people > 0.5]
    theta_rep = np.arctan((1 - 2 * np.mean(rep_districts)) / (len(rep_districts) / len(model.congdists)))
    model.declination = 2 * (theta_dem - theta_rep) / pi

def update_statistics(model, statistics=[unhappy_happy, avg_utility, segregation,
                                         congdist_seats, pop_deviation,
                                         competitiveness, compactness,
                                         efficiency_gap, mean_median, declination,
                                         projected_winner, projected_margin]):
    for stat in statistics:
        stat(model)

def print_statistics(model):
    print(f'[ENERGY] Step: {model.steps}')
    print(f'\tNumber of Moves: {model.total_moves}')
    print(f'\t% Reassigned Precincts: {model.change_map}')
    
    print(f'[CONTROL] Control: {model.control}')
    print(f'\tRep. Congressional Seats: {model.rep_congdist_seats} | Dem. Congressional Seats: {model.dem_congdist_seats} | Tied Congressional Seats: {model.tied_congdist_seats}')
    print(f'\tProjected Winner: {model.projected_winner}')
    print(f'\tProjected Margin: {model.projected_margin}')
    
    print(f'[POPULATION STATS]')
    print(f'\tUnhappy: {model.unhappy} | R: {model.unhappyreps} | D: {model.unhappydems}')
    print(f'\tHappy: {model.happy} | R: {model.happyreps} | D: {model.happydems}')
    print(f'\tAverage Utility: {model.avg_utility}')
    print(f'\tAverage County Segregation: {model.avg_county_segregation}')
    print(f'\tAverage Congressional District Segregation: {model.avg_congdist_segregation}')
    
    print(f'[MAP STATS] Map Score: {model.map_score}')
    print(f'\tEfficiency Gap: {model.efficiency_gap}')
    print(f'\tMean Median: {model.mean_median}')
    print(f'\tDeclination: {model.declination}')
    print(f'\tCompetitive Seats: {model.competitive_seats}')
    print(f'\tCompetitiveness: Avg.: {model.avg_competitiveness} | Min: {model.min_competitiveness} | Max: {model.max_competitiveness}')
    print(f'\tCompactness: Avg.: {model.avg_compactness} | Min: {model.min_compactness} | Max: {model.max_compactness}')
    print(f'\tMax Population Deviation: {model.max_popdev}')
    
    print(f'[END]')
    print('------------------------------------')