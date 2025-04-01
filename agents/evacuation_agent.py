from mesa import Agent
import random

class EvacuationAgent(Agent):
    STATES = ["Normal", "Concerned", "Disoriented", "Panicked", "Injured", "Helpless"]

    def __init__(self, model):
        super().__init__(model)
        self.state = random.choice(self.STATES)

    def step(self):
        if self.state == "Helpless":
            return

        possible_moves = self.model.grid.get_neighborhood(self.pos, moore=True, include_center=False)
        new_position = self.random.choice(possible_moves)
        self.model.grid.move_agent(self, new_position)
