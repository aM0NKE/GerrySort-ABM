from ..agents.person import PersonAgent
from ..agents.geo_unit import GeoAgent
from ..model import GerrySort

import mesa_geo as mg
import mesa

class ModelParamsElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Self Sorting: {model.sorting} | Gerrymandering: {model.gerrymandering} | Max Iters: {model.max_iters} | Tolarence Threshold: {model.tolarence} | Beta: {model.beta} | Ensemble Size: {model.ensemble_size} | Epsilon: {model.epsilon} | Sigma: {model.sigma} | Number of Moving Options: {model.n_moving_options} | Distance Decay: {model.distance_decay} | Moving Cooldown: {model.moving_cooldown} | Capacity Multiplier: {model.capacity_mul}"

class DemographicsElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Total: {model.npop} (Capacity: {model.total_cap}) | Dems: {model.ndems} ({round(model.ndems/(model.nreps+model.ndems),2)}%) | Reps: {model.nreps} ({round(model.nreps/(model.nreps+model.ndems),2)}%)"

class HappinessElement(mesa.visualization.TextElement):
    def render(self, model):
        return f" Happy - Reps: {model.happyreps} | Dems: {model.happydems} (Total moves: {model.total_moves})"
    
class UnhappynessElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Unhappy - Reps: {model.unhappyreps} | Dems: {model.unhappydems}"
    
class CongressionalElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"US Congress: D: {model.dem_congdist_seats} | R: {model.rep_congdist_seats} | T: {model.tied_congdist_seats}"
    
class StateHouseElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"State House: D: {model.dem_legdist_seats} | R: {model.rep_legdist_seats} | T: {model.tied_legdist_seats}"
    
class StateSenateElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"State Senate: D: {model.dem_sendist_seats} | R: {model.rep_sendist_seats} | T: {model.tied_sendist_seats}"

class ControlElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Control: {model.control} | Projected Winner: {model.projected_winner} | Projected Margin: {model.projected_margin}"
    
class DistsMetricsElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"% Change Map: {model.change_map:.2f}% | Avg. Competitiveness: {model.avg_competitiveness:.2f} | Avg. Compactness: {model.avg_compactness:.2f} | Avg. Segregation: {model.avg_segregation:.2f} | Max Pop. Dev.: {model.max_popdev:.2f}"
    
class GerryMetricsElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"EG: {model.efficiency_gap:.2f} | M-M: {model.mean_median:.2f} | Dec: {model.declination:.2f}"
    
model_params = {
    "vis_level": mesa.visualization.Choice("Visualization Level", value="CONGDIST", choices=["PRECINCT", "COUNTY", "LEGDIST", "SENDIST", "CONGDIST"]),
    "state": mesa.visualization.Choice("State", value="PA", choices=["MN", "WI", "MI", "PA", "GA", "TX"]),
    # "state": mesa.visualization.Choice("State", value="MN", choices=["MA", "MN", "WI", "MI", "PA", "GA", "NC", "OH", "TX", "LA"]),
    "election": mesa.visualization.Choice("Election", value="PRES20", choices=["PRES20", "PRES16", "PRES12"]),
    "sorting": mesa.visualization.Checkbox("Self Sorting", True),
    "gerrymandering": mesa.visualization.Checkbox("Gerrymandering", True),
    "control_rule": mesa.visualization.Choice("Control Rule", value="FIXED", choices=["CONGDIST", "STATELEG", "FIXED"]),
    "initial_control": mesa.visualization.Choice("Initial Control", value="Democrats", choices=["Model", "Democrats", "Republicans", "Fair"]),
    "max_iters": mesa.visualization.Slider("Max Iterations", 10, 2, 100, 1),
    "npop": mesa.visualization.Slider("Number of Agents", 5800, 100, 10000, 100),
    "tolarence": mesa.visualization.Slider("Tolarence Threshold", 0.50, 0.00, 1.00, 0.05),
    "beta": mesa.visualization.Slider("Beta (Temp. Sorting)", 100.0, 0.0, 100.0, 10),
    "ensemble_size": mesa.visualization.Slider("Number of Proposed Maps", 100, 5, 200, 1),
    "epsilon": mesa.visualization.Slider("Epsilon", 0.10, 0.00, 1.00, 0.05),
    "sigma": mesa.visualization.Slider("Sigma (Temp. Gerrymandering)", 0.00, 0.00, 1.00, 0.01),
    "n_moving_options": mesa.visualization.Slider("Number of Moving Options", 5, 5, 20, 1),
    "distance_decay": mesa.visualization.Slider("Distance Decay", 0.0, 0.0, 1.0, 0.1),
    "moving_cooldown": mesa.visualization.Slider("Moving Cooldown", 0, 0, 10, 1),
    "capacity_mul": mesa.visualization.Slider("Capacity Multiplier", 1.0, 0.0, 5.0, 0.1),
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
unhappyness_element = UnhappynessElement()
congressional_element = CongressionalElement()
state_house_element = StateHouseElement()
state_senate_element = StateSenateElement()
control_element = ControlElement()
gerry_metrics_element = GerryMetricsElement()
dists_metrics_element = DistsMetricsElement()

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
    ]
)
state_house_seat_share_chart = mesa.visualization.ChartModule(
    [
        {"Label": "rep_legdist_seats", "Color": "Red"},
        {"Label": "dem_legdist_seats", "Color": "Blue"},
        {"Label": "tied_legdist_seats", "Color": "Grey"},
    ]
)
state_senate_seat_share_chart = mesa.visualization.ChartModule(
    [
        {"Label": "rep_sendist_seats", "Color": "Red"},
        {"Label": "dem_sendist_seats", "Color": "Blue"},
        {"Label": "tied_sendist_seats", "Color": "Grey"},
    ]
)
dists_metrics_chart = mesa.visualization.ChartModule(
    [
        {"Label": "change_map", "Color": "Red"},
        {"Label": "avg_competitiveness", "Color": "Black"},
        {"Label": "avg_compactness", "Color": "Green"},
        {"Label": "avg_segregation", "Color": "Yellow"},
        {"Label": "max_popdev", "Color": "Blue"},
    ]
)
gerry_metrics_chart = mesa.visualization.ChartModule(
    [
        {"Label": "declination", "Color": "Black"},
        {"Label": "efficiency_gap", "Color": "Green"},
        {"Label": "mean_median", "Color": "Yellow"},
    ]
)

server = mesa.visualization.ModularServer(
    GerrySort,
    [model_params_element, map_element, demographics_element, 
     happy_chart, happiness_element, unhappyness_element,
     control_element, congressional_seat_share_chart, congressional_element,
     dists_metrics_chart, dists_metrics_element,
     gerry_metrics_chart, gerry_metrics_element, 
     state_house_seat_share_chart,  state_house_element, 
     state_senate_seat_share_chart, state_senate_element],
    "GerrySort",
    model_params,
)