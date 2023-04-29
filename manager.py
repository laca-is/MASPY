from maspy.agent import Agent, Belief, Ask, Objective

class manager(Agent):
    def __init__(self, name, beliefs = [], objectives = [], plans = {}) -> None:
        super().__init__(name, beliefs, objectives, plans)