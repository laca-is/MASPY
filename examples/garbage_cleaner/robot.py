from maspy.agent import Agent, Belief, Ask, Objective

class Robot(Agent):
    def __init__(self, name: str, beliefs = [], objectives = [], plans= {}):
        super().__init__(name, beliefs, objectives, plans)
        self.add_plan({
            "clean": Robot.clean,
            "move": Robot.move
        })
        self.add_focus("examples.garbage_cleaner.room","Room")
        
    def clean(self,src):
        ...
    
    def move(self,src,direction):
        ...