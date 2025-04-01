from mesa import Model
from mesa.space import MultiGrid
from agents.evacuation_agent import EvacuationAgent
from agents.obstacle import Obstacle

class EvacuationModel(Model):
    def __init__(self, num_agents, width, height):
        super().__init__()
        self.num_agents = num_agents
        self.grid = MultiGrid(width, height, torus=False)

        for _ in range(self.num_agents):
            agent = EvacuationAgent(self)
            x = self.random.randint(0, width - 1)
            y = self.random.randint(0, height - 1)
            self.grid.place_agent(agent, (x, y))

        for _ in range(5):
            x = self.random.randint(0, width - 1)
            y = self.random.randint(0, height - 1)
            obstacle = Obstacle(self, "Vehicle")
            self.grid.place_agent(obstacle, (x, y))

        for _ in range(3):
            x = self.random.randint(0, width - 1)
            y = self.random.randint(0, height - 1)
            fire = Obstacle(self, "Fire/Smoke")
            self.grid.place_agent(fire, (x, y))

    def step(self):
        self.schedule.step()
