import mesa
import mesa_geo as mg
from shapely.geometry import box

from .agents import PersonAgent, DistrictAgent, CountyAgent
from .model import GeoSchellingPoints


class HappyElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Happy agents: {model.happy}"

class UnhappyElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Unhappy agents: {model.unhappy}"
    
class ControlElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Control: {model.control}"


model_params = {
    # "red_percentage": mesa.visualization.Slider("% red", 0.5, 0.00, 1.0, 0.05),
    "npop": mesa.visualization.Slider("Number of Agents", 1000, 100, 10000, 100),
    "similarity_threshold": mesa.visualization.Slider("Tolarence Threshold", 0.5, 0.00, 1.0, 0.05),
    "gerrymandering": mesa.visualization.Checkbox("Gerrymandering", True),
    "map_sample_size": mesa.visualization.Slider("Map Sample Size", 10, 10, 100, 10),
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


happy_element = HappyElement()
unhappy_element = UnhappyElement()
control_element = ControlElement()

lat, lon = 46.5, -93.5
map_element = mg.visualization.MapModule(schelling_draw, [lat, lon], 7, 850, 850)
happy_chart = mesa.visualization.ChartModule(
    [
        {"Label": "unhappy", "Color": "Red"},
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
efficiency_gap_chart = mesa.visualization.ChartModule(
    [
        {"Label": "efficiency_gap", "Color": "Black"},
    ]
)
server = mesa.visualization.ModularServer(
    GeoSchellingPoints,
    [map_element, control_element, happy_element, unhappy_element, efficiency_gap_chart, seat_share_chart, happy_chart],
    "Schelling",
    model_params,
)