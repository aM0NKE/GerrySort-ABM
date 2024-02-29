import mesa
import mesa_geo as mg
from shapely.geometry import box

from .agents import PersonAgent, RegionAgent
from .model import GeoSchellingPoints


class HappyElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Happy agents: {model.happy}"


class UnhappyElement(mesa.visualization.TextElement):
    def render(self, model):
        return f"Unhappy agents: {model.unhappy}"


model_params = {
    # "red_percentage": mesa.visualization.Slider("% red", 0.5, 0.00, 1.0, 0.05),
    "similarity_threshold": mesa.visualization.Slider(
        "% similar wanted", 0.5, 0.00, 1.0, 0.05
    ),
}


def schelling_draw(agent):
    portrayal = {}
    if isinstance(agent, RegionAgent):
        portrayal["color"] = agent.color
    elif isinstance(agent, PersonAgent):
        portrayal["radius"] = 1
        portrayal["shape"] = "circle"
        portrayal["color"] = "Red" if agent.is_red else "Blue"
    return portrayal


happy_element = HappyElement()
unhappy_element = UnhappyElement()

lat, lon = 46, -94

map_element = mg.visualization.MapModule(schelling_draw, [lat, lon], 8, 1000, 1000)
happy_chart = mesa.visualization.ChartModule(
    [
        {"Label": "unhappy", "Color": "Red"},
        {"Label": "happy",   "Color": "Green",},
    ]
)
district_chart = mesa.visualization.ChartModule(
    [
        {"Label": "red_districts", "Color": "Red"},
        {"Label": "blue_districts", "Color": "Blue"},
    ]
)
server = mesa.visualization.ModularServer(
    GeoSchellingPoints,
    [map_element, happy_element, unhappy_element, happy_chart, district_chart],
    "Schelling",
    model_params,
)