from maspy import *
from maspy.learning import *
from random import choice

class Map(Environment):
    def __init__(self, env_name=None):
        super().__init__(env_name)

        self.targets = [(2,1),(1,2)]
        self.max_row = 2
        self.max_col = 3
        size = (self.max_row+1,self.max_col+1)
        self.create(Percept("location", size, cartesian))
        self.possible_starts = {"location": [(0,0),(0,3)]}
    
    def move_transition(self, state: dict, direction: str):
        location = state["location"]
        
        location =self.moviment(location, direction)

        state["location"] = location
        
        if location in self.targets:
            reward = 10
            terminated = True
        else:
            reward = -1
            terminated = False
        return state, reward, terminated

    @action(listed, ("up","down","left","right"), move_transition)
    def move(self, agt, direction: str):
        percept = self.get(Percept("location", (Any,Any)))
        assert isinstance(percept, Percept)
        self.print(f"{agt} in {percept.args} is Moving {direction}")
        new_location = self.moviment(percept.args, direction)
        self.change(percept, new_location)
        self.print_percepts
        if new_location in self.targets:
            self.print(f"{agt} reached a target")
    
    def moviment(self, location, direction):
        if direction == "up" and location[0] > 0:
            location = (location[0]-1, location[1])
        elif direction == "down" and location[0] < self.max_row:
            location = (location[0]+1, location[1])
        elif direction == "left" and location[1] > 0:
            location = (location[0], location[1]-1)
        elif direction == "right" and location[1] < self.max_col:
            location = (location[0], location[1]+1)
        return location
    
class Mover(Agent):
    def __init__(self, my_name=None):
        super().__init__(my_name)
        self.add(Goal("ask_for_guide"))

    @pl(gain,Goal("ask_for_guide"))
    def move_guide(self,src) -> None:
        self.print("Asking for guide")
        belief_model = self.send("Instructor", askOneReply, Belief("Model",("Map", Any)))
        if isinstance(belief_model, Belief):
            model: EnvModel = belief_model.args[1][0]
            model.reset_percepts()
            self.add_policy(model)
            self.auto_action = True
        else:
            self.print("No model available for Map")
            self.wait(3)
            self.add(Goal("ask_for_guide"))

class Instructor(Agent):
    def __init__(self, my_name=None, env=None):
        super().__init__(my_name)
        self.add(Goal("make_model",[env]))
    
    @pl(gain,Goal("make_model",Any))
    def make_model(self,src,env: list[Environment]):
        self.print(f"Making model for {env[0].my_name}")
        model = EnvModel(env[0])
        print(f'actions: {model.actions_list}  space: {model.states_list}')
        model.learn(qlearning, num_episodes=5000)
        self.print(f"Finished training {env[0].my_name} Model")
        self.add(Belief("Model",(env[0].my_name, [model])))
            
if __name__ == "__main__":
    mv = Mover()
    map = Map()
    it = Instructor(env=map)
    Admin().start_system()
    