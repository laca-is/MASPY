
from maspy import *

class DummyAgent(Agent):
    def __init__(self, name,  beliefs, goals):
        super().__init__(name, beliefs, goals, show_exec=False)
        self.add(Belief("Box",(5,10)))
        
    @pl(gain,Goal("move_boxes"),Belief("Box",('X','Y')))
    def move_to_pos(self, src, x, y):
        my_pos = self.get(Belief("my_pos",('My_X','My_Y')))
        self.move(my_pos.args, (x,y))
        self.print(f"Picking up Box in {x,y}")
        target_pos = self.get(Belief("target_pos",('Tg_X','Tg_Y')))
        self.move((x,y), target_pos.args)
        self.print(f"Putting Box in {target_pos.args}")
        self.stop_cycle()
        
    # Does not have a decorate, therefore not a plan
    def move(self, my_pos, target_pos):
        self.print(f"Moving from {my_pos} to target {target_pos} position")

if __name__ == "__main__":
    agent_1 = DummyAgent("Dummy_1", [Belief("my_pos",(0,0)),Belief("target_pos",(7,7))], Goal("move_boxes"))

    agent_2 = DummyAgent("Dummy_2", [Belief("my_pos",(3,3)),Belief("target_pos",(3,3))], Goal("move_boxes"))

    Admin().start_system()