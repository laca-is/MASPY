from maspy.agent import agent, Belief, Ask, Objective

class manager(agent):
    def __init__(self, name, beliefs = [], objectives = [], plans = {}) -> None:
        super().__init__(name, beliefs, objectives, plans)