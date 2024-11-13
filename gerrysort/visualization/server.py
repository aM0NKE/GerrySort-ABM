from ..agents.person import PersonAgent
from ..agents.geo_unit import GeoAgent
from ..model import GerrySort

import mesa_geo as mg
import mesa

class ModelParamsElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Sorting: {model.sorting} | Gerrymandering: {model.gerrymandering} | Number of Agents: {model.npop} | Tolarence: {model.tolarence} | Beta: {model.beta} | Capacity Multiplier: {model.capacity_mul} | Number of Proposed Maps: {model.ensemble_size} | Number of Moving Options: {model.n_moving_options} | Moving Cooldown: {model.moving_cooldown}"

class DemographicsElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Number of Dems: {model.ndems} | Reps: {model.nreps} | Total: {model.npop} (State Capacity: {model.total_cap})"

class HappinessElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Happy agents: {model.happy} | Unhappy: {model.unhappy} (Total moves: {model.total_moves})"
    
class CongressionalElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Projected Congressional Seats: D: {model.dem_congdist_seats} | R: {model.rep_congdist_seats} | T: {model.tied_congdist_seats} (Change Map: {model.change_map})"
    
class StateHouseElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Projected State House Seats: D: {model.dem_legdist_seats} | R: {model.rep_legdist_seats} | T: {model.tied_legdist_seats}"
    
class StateSenateElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Projected State Senate Seats: D: {model.dem_sendist_seats} | R: {model.rep_sendist_seats} | T: {model.tied_sendist_seats}"

class ControlElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Control: {model.control} | Projected Winner: {model.projected_winner} | Projected Margin: {model.projected_margin}"
    
class MetricsElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"EG: {model.efficiency_gap:.2f} | M-M: {model.mean_median:.2f} | Dec: {model.declination:.2f}"
    
model_params = {
    "state": mesa.visualization.Choice("State", value="MN", choices=["MN"]),
    "sorting": mesa.visualization.Checkbox("Self Sorting", True),
    "gerrymandering": mesa.visualization.Checkbox("Gerrymandering", True),
    "initial_control": mesa.visualization.Choice("Initial Control", value="Data", choices=["Data", "Democratic", "Republican", "Tied"]),
    "max_iters": mesa.visualization.Slider("Max Iterations", 10, 2, 100, 1),
    "npop": mesa.visualization.Slider("Number of Agents", 5800, 100, 10000, 100),
    "tolarence": mesa.visualization.Slider("Tolarence Threshold", 0.50, 0.00, 1.00, 0.05),
    "beta": mesa.visualization.Slider("Beta (Temperature)", 100.0, 0.0, 100.0, 10),
    "ensemble_size": mesa.visualization.Slider("Number of Proposed Maps", 100, 5, 200, 1),
    "epsilon": mesa.visualization.Slider("Epsilon", 0.10, 0.00, 1.00, 0.05),
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
        portrayal["radius"] = 1
        portrayal["shape"] = "circle"
        portrayal["color"] = agent.color
    return portrayal

model_params_element = ModelParamsElement()
demographics_element = DemographicsElement()
happiness_element = HappinessElement()
congressional_element = CongressionalElement()
state_house_element = StateHouseElement()
state_senate_element = StateSenateElement()
control_element = ControlElement()
metrics_element = MetricsElement()

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
metrics_chart = mesa.visualization.ChartModule(
    [
        {"Label": "change_map", "Color": "Red"},
        {"Label": "efficiency_gap", "Color": "Black"},
        {"Label": "mean_median", "Color": "Yellow"},
        {"Label": "declination", "Color": "Green"},
    ]
)

server = mesa.visualization.ModularServer(
    GerrySort,
    [model_params_element, map_element, demographics_element, happy_chart, happiness_element, 
     metrics_chart, metrics_element, control_element,
     congressional_seat_share_chart, congressional_element,
     state_house_seat_share_chart,  state_house_element, 
     state_senate_seat_share_chart, state_senate_element],
    "GerrySort",
    model_params,
)