from maspy import *

class Shelf(Environment):
    def __init__(self, env_name=None):
        super().__init__(env_name)
        self.create(Percept("object"))

    def take(self, agt):
        self.print(f"Agent {agt} is taking object")
        object = self.get(Percept("object"))
        self.delete(object)

class Taker(Agent):
    def __init__(self):
        super().__init__()
        self.add(Goal("take_object"))

    @pl(gain, Goal("take_object"))
    def take_obj(self, src):
        self.print(f"[{self.cycle_counter}] Takin object")
        self.take()
        self.stop_cycle()

class Inserter(Agent):
    @pl(lose, Belief("object"))
    def insert_obj(self,src):
        self.print(f"[{self.cycle_counter}] Need to ressuply a new object")
        self.stop_cycle()

if __name__ == "__main__":
    Admin().connect_to([Taker(),Inserter()], Shelf())
    Admin().start_system()