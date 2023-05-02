from maspy.environment import Environment 
from maspy.agent import Agent, Belief, Objective
from maspy.system_control import Control

class Room(Environment):
    def __init__(self, env_name='room'):
        super().__init__(env_name)
        self._create_fact("dirt",{(0,1): True, (3,4): True})
        self._create_fact("room_size",(5,5))

    def clean_position(agent, position):
        print(f"Cleaning position {position}")

class Robot(Agent):
    def __init__(self, name: str, beliefs = [], objectives = [], plans= {}, initial_env= None):
        super().__init__(name, beliefs, objectives, plans)
        self.add_plan({
            "clean": Robot.clean,
            "move": Robot.move
        })
        self.add_focus_env(initial_env,"Room")
        self.add_objective(Objective("clean"))
        self.add_belief([Belief("position",(0,0)),Belief("room_is_dirty")])

    def clean(self,src):
        if self.has_belief(Belief("room_is_dirty")):
            pos = self.search_beliefs("position",2)
            self.get_env("Room").clean_position(self,pos.args)

    def move(self,src,direction):
        ...

def main():
    env = Room("Room")
    rbt = Robot('R1', initial_env=env)
    Control().start_agents(rbt)
    
    rbt.print_beliefs( )


if __name__ == "__main__":
    main()