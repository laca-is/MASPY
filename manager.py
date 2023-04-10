from agent import agent, belief, ask, objective

class manager(agent):
    def __init__(self, name, beliefs = [], objectives = []) -> None:
        super().__init__(name, beliefs, objectives)