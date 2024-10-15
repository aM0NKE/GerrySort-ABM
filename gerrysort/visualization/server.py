import mesa
import mesa_geo as mg
from shapely.geometry import box

from ..agents.person import PersonAgent
from ..agents.district import DistrictAgent
from ..agents.county import CountyAgent
from ..model import GerrySort

class ModelParamsElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Sorting: {model.sorting} | Gerrymandering: {model.gerrymandering} | Number of Agents: {model.npop} | Tolarence: {model.tolarence} | Beta: {model.beta} | Capacity Multiplier: {model.capacity_mul} | Number of Proposed Maps: {model.n_proposed_maps} | Number of Moving Options: {model.n_moving_options} | Moving Cooldown: {model.moving_cooldown}"

class DemographicsElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Number of Dems: {model.ndems} | Reps: {model.nreps} | Total: {model.npop} (State Capacity: {model.total_cap})"

class HappinessElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Happy agents: {model.happy} | Unhappy: {model.unhappy} (Total moves: {model.n_moves})"
    
class CongressionalElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Projected Congressional Seats: D: {model.blue_congressional_seats} | R: {model.red_congressional_seats} | T: {model.tied_congressional_seats}"
    
class StateHouseElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Projected State House Seats: D: {model.blue_state_house_seats} | R: {model.red_state_house_seats} | T: {model.tied_state_house_seats}"
    
class StateSenateElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Projected State Senate Seats: D: {model.blue_state_senate_seats} | R: {model.red_state_senate_seats} | T: {model.tied_state_senate_seats}"

class ControlElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Control: {model.control} | Projected Winner: {model.projected_winner} | Projected Margin: {model.projected_margin}"
    
class MetricsElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"EG: {model.efficiency_gap:.2f} | M-M: {model.mean_median:.2f} | Dec: {model.declination:.2f}"
    
model_params = {
    "state": mesa.visualization.Choice("State", value="MN", choices=["MN", "GA", "TX"]),
    "sorting": mesa.visualization.Checkbox("Self Sorting", True),
    "gerrymandering": mesa.visualization.Checkbox("Gerrymandering", True),
    "npop": mesa.visualization.Slider("Number of Agents", 1000, 100, 10000, 100),
    "tolarence": mesa.visualization.Slider("Tolarence Threshold", 0.50, 0.00, 1.00, 0.05),
    "beta": mesa.visualization.Slider("Beta (Temperature)", 2.0, 0.0, 10.0, 1),
    "capacity_mul": mesa.visualization.Slider("Capacity Multiplier", 1.0, 0.0, 5.0, 0.1),
    "n_proposed_maps": mesa.visualization.Slider("Number of Proposed Maps", 5, 5, 25, 5),
    "n_moving_options": mesa.visualization.Slider("Number of Moving Options", 10, 5, 35, 5),
    "moving_cooldown": mesa.visualization.Slider("Moving Cooldown", 0, 0, 10, 1),
    # "distance_decay": mesa.visualization.Slider("Distance Decay", 0.2, 0.00, 1.0, 0.05), TODO: Part of the discounted utility
}

def schelling_draw(agent):
    portrayal = {}
    if isinstance(agent, DistrictAgent):
        portrayal["color"] = agent.color
    elif isinstance(agent, CountyAgent):
        portrayal["color"] = agent.color
    elif isinstance(agent, PersonAgent):
        portrayal["radius"] = 1
        portrayal["shape"] = "circle"
        portrayal["color"] = "Red" if agent.is_red else "Blue"
    return portrayal

model_params_element = ModelParamsElement()
demographics_element = DemographicsElement()
happiness_element = HappinessElement()
congressional_element = CongressionalElement()
state_house_element = StateHouseElement()
state_senate_element = StateSenateElement()
control_element = ControlElement()
metrics_element = MetricsElement()

ga_lat, ga_lon = 32.2, -82.9 # Coords for GA #TODO: Make this dynamic
mn_lat, mn_lon = 46.3, -94.2 # Coords for MN
map_element = mg.visualization.MapModule(schelling_draw, [mn_lat, mn_lon], 7, 850, 850)

happy_chart = mesa.visualization.ChartModule(
    [
        {"Label": "unhappy", "Color": "Red"},
        {"Label": "happy",   "Color": "Green",},
    ]
)
congressional_seat_share_chart = mesa.visualization.ChartModule(
    [
        {"Label": "red_congressional_seats", "Color": "Red"},
        {"Label": "blue_congressional_seats", "Color": "Blue"},
        {"Label": "tied_congressional_seats", "Color": "Grey"},
    ]
)
state_house_seat_share_chart = mesa.visualization.ChartModule(
    [
        {"Label": "red_state_house_seats", "Color": "Red"},
        {"Label": "blue_state_house_seats", "Color": "Blue"},
        {"Label": "tied_state_house_seats", "Color": "Grey"},
    ]
)
state_senate_seat_share_chart = mesa.visualization.ChartModule(
    [
        {"Label": "red_state_senate_seats", "Color": "Red"},
        {"Label": "blue_state_senate_seats", "Color": "Blue"},
        {"Label": "tied_state_senate_seats", "Color": "Grey"},
    ]
)
metrics_chart = mesa.visualization.ChartModule(
    [
        {"Label": "efficiency_gap", "Color": "Black"},
        {"Label": "mean_median", "Color": "Pink"},
        {"Label": "declination", "Color": "Yellow"},
    ]
)

server = mesa.visualization.ModularServer(
    GerrySort,
    [model_params_element, map_element, demographics_element, happy_chart, happiness_element, 
     congressional_seat_share_chart, congressional_element, 
     state_house_seat_share_chart,  state_house_element, 
     state_senate_seat_share_chart, state_senate_element, control_element, 
     metrics_chart, metrics_element],
    "GerrySort",
    model_params,
)