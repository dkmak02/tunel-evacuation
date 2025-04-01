from mesa.visualization import SolaraViz, make_space_component, make_plot_component
from agents.evacuation_agent import EvacuationAgent
from agents.obstacle import Obstacle
from models.evacuation_model import EvacuationModel


def agent_portrayal(agent):
    portrayal = {}


    if isinstance(agent, EvacuationAgent):
        portrayal["Shape"] = "circle"
        portrayal["r"] = 1
        portrayal["Color"] = "blue"
        portrayal["Layer"] = 0


    elif isinstance(agent, Obstacle):
        portrayal["Shape"] = "rect"
        portrayal["w"] = 1
        portrayal["h"] = 1
        portrayal["Color"] = "red"
        portrayal["Layer"] = 1

    return portrayal



space_component = make_space_component(agent_portrayal, draw_grid=True)


model_params = {
    "num_agents": 10,
    "width": 10,
    "height": 10
}

model = EvacuationModel(**model_params)


page = SolaraViz(
    model,
    components=[space_component],
    model_params=model_params,
    name="Evacuation Model"
)

page
