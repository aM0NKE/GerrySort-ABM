from ..agents.person import PersonAgent
from ..agents.geo_unit import GeoAgent
from ..model import GerrySort

import mesa_geo as mg
import mesa

class ModelParamsElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Self Sorting: {model.sorting} | Gerrymandering: {model.gerrymandering} | Max Iters: {model.max_iters} | Tolerance Threshold: {model.tolerance} | Beta: {model.beta} | Ensemble Size: {model.ensemble_size} | Epsilon: {model.epsilon} | Sigma: {model.sigma} | Number of Moving Options: {model.n_moving_options} | Distance Decay: {model.distance_decay} | Capacity Multiplier: {model.capacity_mul}"

class DemographicsElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Total # Agents: {model.npop} (Capacity: {model.total_cap}) | R: {model.nreps} ({round(model.nreps/(model.nreps+model.ndems),2)}%) / D: {model.ndems} ({round(model.ndems/(model.nreps+model.ndems),2)}%)"

class HappinessElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Happy: R: {model.happyreps} / D: {model.happydems} | Unhappy: R: {model.unhappyreps} / D: {model.unhappydems} (Total moves: {model.total_moves})"
    
class ControlElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Control: {model.control} | Control Margin: {model.projected_margin}"

model_params = {
    "vis_level": mesa.visualization.Choice("Visualization Level", value="CONGDIST", choices=["CONGDIST", "COUNTY", "PRECINCT"]),
    "state": mesa.visualization.Choice("State", value="GA", choices=["MN", "WI", "MI", "PA", "GA", "TX"]),
    # "state": mesa.visualization.Choice("State", value="MN", choices=["MA", "MN", "WI", "MI", "PA", "GA", "NC", "OH", "TX", "LA"]),
    "election": mesa.visualization.Choice("Election", value="PRES20", choices=["PRES20", "PRES16", "PRES12"]),
    "sorting": mesa.visualization.Checkbox("Self Sorting", True),
    "gerrymandering": mesa.visualization.Checkbox("Gerrymandering", True),
    "control_rule": mesa.visualization.Choice("Control Rule", value="CONGDIST", choices=["CONGDIST", "FIXED"]),
    "initial_control": mesa.visualization.Choice("Initial Control", value="Model", choices=["Model", "Democrats", "Republicans", "Fair"]),
    "max_iters": mesa.visualization.Slider("Max Iterations", 4, 1, 10, 1),
    "npop": mesa.visualization.Slider("Number of Agents", 11000, 1000, 30500, 100),
    "tolerance": mesa.visualization.Slider("Tolerance Threshold", 0.50, 0.00, 1.00, 0.05),
    "beta": mesa.visualization.Slider("Beta (Temp. Sorting)", 100.0, 0.0, 100.0, 5),
    "ensemble_size": mesa.visualization.Slider("Number of Proposed Maps", 250, 50, 1000, 50),
    "epsilon": mesa.visualization.Slider("Epsilon", 0.01, 0.01, 1.00, 0.01),
    "sigma": mesa.visualization.Slider("Sigma (Temp. Gerrymandering)", 0.01, 0.00, 0.1, 0.01),
    "n_moving_options": mesa.visualization.Slider("Number of Moving Options", 10, 1, 20, 1),
    "distance_decay": mesa.visualization.Slider("Distance Decay", 0.0, 0.0, 1.0, 0.01),
    "capacity_mul": mesa.visualization.Slider("Capacity Multiplier", 1.0, 0.9, 2.0, 0.01),
    "intervention": mesa.visualization.Choice("Intervention", value="None", choices=["None", "Competitive", "Compact"]),
    "intervention_weight": mesa.visualization.Slider("Intervention Weight", 0.0, 0.0, 1.0, 0.01),
}

def schelling_draw(agent):
    portrayal = {}
    if isinstance(agent, GeoAgent):
        portrayal["color"] = agent.color
    elif isinstance(agent, PersonAgent):
        portrayal["radius"] = .1
        portrayal["shape"] = "circle"
        portrayal["color"] = agent.color
    return portrayal

model_params_element = ModelParamsElement()
demographics_element = DemographicsElement()
happiness_element = HappinessElement()
control_element = ControlElement()

us_lat, us_lon = 39.8, -98.6 # Coords for US
map_element = mg.visualization.MapModule(schelling_draw, [us_lat, us_lon], 4, 850, 850)

happy_chart = mesa.visualization.ChartModule(
    [
        {"Label": "unhappy", "Color": "Red"},
        {"Label": "happy",   "Color": "Green",},
    ]
)
congressional_seat_share_chart = mesa.visualization.ChartModule(
    [
        {"Label": "rep_congdist_seats", "Color": "Red"},
        {"Label": "dem_congdist_seats", "Color": "Blue"},
        {"Label": "tied_congdist_seats", "Color": "Grey"},
        {"Label": "competitive_seats", "Color": "Black"},
        {"Label": "predicted_seats", "Color": "Green"},
    ]
)
gerry_metrics_chart = mesa.visualization.ChartModule(
    [
        {"Label": "declination", "Color": "Red"},
        {"Label": "efficiency_gap", "Color": "Green"},
        {"Label": "mean_median", "Color": "Blue"},
    ]
)
compactness_chart = mesa.visualization.ChartModule(
    [
        {"Label": "min_compactness", "Color": "Red"},
        {"Label": "avg_compactness", "Color": "Blue"},
        {"Label": "max_compactness", "Color": "Green"},
    ]
)
competitiveness_chart = mesa.visualization.ChartModule(
    [
        {"Label": "min_competitiveness", "Color": "Red"},
        {"Label": "avg_competitiveness", "Color": "Blue"},
        {"Label": "max_competitiveness", "Color": "Green"},
    ]
)
map_stats_chart = mesa.visualization.ChartModule(
    [
        {"Label": "map_score", "Color": "Red"},
        {"Label": "change_map", "Color": "Black"},
        {"Label": "max_popdev", "Color": "Grey"},
    ]
)
segregation_chart = mesa.visualization.ChartModule(
    [
        {"Label": "avg_county_segregation", "Color": "Black"},
        {"Label": "avg_congdist_segregation", "Color": "Grey"},
    ]
)

server = mesa.visualization.ModularServer(
    GerrySort,
    [model_params_element, map_element, demographics_element,
     happiness_element, control_element, congressional_seat_share_chart,
     gerry_metrics_chart, compactness_chart, competitiveness_chart,
     map_stats_chart, happy_chart, segregation_chart
    ],
    "GerrySort",
    model_params,
)