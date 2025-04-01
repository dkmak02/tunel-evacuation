from mesa import Agent

class Obstacle(Agent):
    def __init__(self, model, obstacle_type):
        super().__init__(model)
        self.obstacle_type = obstacle_type
