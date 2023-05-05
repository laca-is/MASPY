from maspy.environment import Environment 
from maspy.agent import Agent, Belief, Objective
from maspy.system_control import Control

class Room(Environment):
    def __init__(self, env_name='room'):
        super().__init__(env_name)
        self.full_log = False
        self._create_fact("dirt",{(0,1): False, (2,2): False})

    def add_dirt(self, position):
        print(f"{self._my_name}> Dirt created in position {position}")
        dirt_status = self.get_fact_value("dirt")
        dirt_status.update({position: False}) 
        #self._update_fact("dirt",dirt_status) # same as below
    
    def clean_position(self, agent, position):
        print(f"{self._my_name}> {agent} is cleaning position {position}")
        dirt_status = self.get_fact_value("dirt")
        print(dirt_status)
        if dirt_status[position] is False:
            dirt_status[position] = True # changes the dict inside fact
        #self._update_fact("dirt",dirt_status) # useless cause of above

class Robot(Agent):
    def __init__(self, name: str, beliefs = [], objectives = [], plans= {}, initial_env= None, full_log=False):
        super().__init__(name, beliefs, objectives, plans, full_log)
        self.add_plan({
            "decide_move": Robot.decide_move,
            "clean": Robot.clean,
            "move": Robot.move
        })

        self.add_focus_env(initial_env,"Room")
        self.add_objective(Objective("decide_move"))
        self.add_belief(Belief("room_is_dirty"))
        self.position = (0,0)
        print(f"{self.my_name}> Inicial position {self.position}")

    
    def decide_move(self,src):
        min_dist = float("inf")
        target = None

        dirt_pos = self.search_beliefs("dirt",1,"Room")
        
        x, y = self.position
        for pos, clean in dirt_pos.args[0].items():
            if not clean:
                dist = abs(pos[0]-x) + abs(pos[1]-y)
                if dist < min_dist:
                    min_dist = dist
                    target = pos
                    
        if target is None:
            print(f"{self.my_name}> All dirt is cleaned")
            print("*** Finished Cleaning ***")
            return
        
        print(f"{self.my_name}> Moving to {target}")
        self.add_objective(Objective("move",[target]))
                                 
    def clean(self,src):
        if self.has_belief(Belief("room_is_dirty")):
            self.get_env("Room").clean_position(self.my_name, self.position)
            self.add_objective(Objective("decide_move"))

    def move(self,src,target):
        x, y = self.position
        
        if x != target[0]:
            diff = target[0] - x
            direction = (int(diff/abs(diff)),0)
        else:
            diff = target[1] - y
            direction = (0,int(diff/abs(diff)))
        
        match direction:
            case (0,1): print(f"{self.my_name}> Moving Down")
            case (0,-1): print(f"{self.my_name}> Moving Up")
            case (-1,0): print(f"{self.my_name}> Moving Left")
            case (1,0): print(f"{self.my_name}> Moving Right")
        
        self.position = (x+direction[0],y+direction[1])
        print(f"{self.my_name}> New position: {self.position}")
        
        if self.position == target:
            print(f"{self.my_name}> Reached dirt position")
            self.add_objective(Objective("clean"))
            return
        else:
            self.add_objective(Objective("move",[target]))

def main():
    env = Room("Room")
    rbt = Robot('R1', initial_env=env, full_log=False)
    Control().start_agents(rbt)
    env.add_dirt((3,1))
    rbt.add_objective(Objective("decide_move"))

if __name__ == "__main__":
    main()
    
    