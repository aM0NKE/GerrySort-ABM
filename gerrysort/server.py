import mesa
import mesa_geo as mg
from shapely.geometry import box

from .agents import PersonAgent, DistrictAgent, CountyAgent
from .model import GerrySort

class DemographicsElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Number of Dems: {model.ndems} | Reps: {model.nreps}"

class HappinessElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Happy agents: {model.happy} | Unhappy: {model.unhappy}"
    
class ControlElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Control: {model.prev_control} | Projected Winner: {model.control} | Proj. Seats: D: {model.blue_districts} | R: {model.red_districts} | T: {model.tied_districts}"

class MetricsElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"EG: {model.efficiency_gap:.2f} | M-M: {model.mean_median:.2f} | Dec: {model.declination:.2f}"
    
model_params = {
    "npop": mesa.visualization.Slider("Number of Agents", 1000, 100, 10000, 100),
    "similarity_threshold": mesa.visualization.Slider("Tolarence Threshold", 0.5, 0.00, 1.0, 0.05),
    "gerrymandering": mesa.visualization.Checkbox("Gerrymandering", True),
    "map_sample_size": mesa.visualization.Slider("Map Sample Size", 10, 10, 100, 10),
    "n_moving_options": mesa.visualization.Slider("Number of Moving Options", 10, 1, 100, 5),
    "distance_decay": mesa.visualization.Slider("Distance Decay", 0.2, 0.00, 1.0, 0.05),
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

demographics_element = DemographicsElement()
happiness_element = HappinessElement()
control_element = ControlElement()
metrics_element = MetricsElement()

lat, lon = 46.5, -93.5 # Coords for Minnesota
map_element = mg.visualization.MapModule(schelling_draw, [lat, lon], 7, 850, 850)

happy_chart = mesa.visualization.ChartModule(
    [
        {"Label": "unhappy", "Color": "Orange"},
        {"Label": "happy",   "Color": "Green",},
    ]
)
seat_share_chart = mesa.visualization.ChartModule(
    [
        {"Label": "red_districts", "Color": "Red"},
        {"Label": "blue_districts", "Color": "Blue"},
        {"Label": "tied_districts", "Color": "Grey"},
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
    [map_element, demographics_element, happy_chart, happiness_element, seat_share_chart, control_element, metrics_chart, metrics_element],
    "GerrySort",
    model_params,
)