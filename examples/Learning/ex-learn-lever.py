from maspy import *
from maspy.learning import *

class Levers(Environment):
    def __init__(self, env_name):
        super().__init__(env_name)
        self.points = 0
        self.create(Percept("pulled_lever", (-1,0,1), listed))
        self.possible_starts = {"pulled_lever": [-1]}
    
    def lever_transition(self, state: dict, lever: int):
        pulled_lever = state['pulled_lever']
        
        if lever == 0:
            reward = -1
            state['pulled_lever'] = 0
        elif lever == 1 and pulled_lever == 1:
            reward = 5
        elif lever == 1:
            reward = 0
            state['pulled_lever'] = 1
        elif lever == 2:
            reward = 3
            state['pulled_lever'] = -1
                
        return state, reward
    
    @action(listed, (0,1,2), lever_transition)
    def lever(self, agt, lever: int):
        self.show_exec = True
        pulled_lever = self.get(Percept("pulled_lever", Any))
        self.show_exec = False
        assert isinstance(pulled_lever, Percept)
        if lever == 0:
            self.points -= 1
            pulled_lever.change(values=0)
        elif lever == 1 and pulled_lever.values == 1:
            self.points += 5
        elif lever == 1:
            pulled_lever.change(values=1)
        elif lever == 2:
            self.points += 3
            pulled_lever.change(values=-1)
        
        self.print(f"{agt} is pulling lever: {lever} - total points: {self.points}")
   
class LeverAgent(Agent):
    @pl(gain, Goal("decide_lever"))
    def decide_lever(self, src):
        old_pulled_lever = self.get(Belief("pulled_lever", Any))
        action, _ = self.get_best_action("LeverEnv")
        self.print(f"The Best Action is {old_pulled_lever.values} : {action}")
        self.lever(action)
        self.perceive("LeverEnv")
        new_pulled_lever = self.get(Belief("pulled_lever", Any))
        #self.print("old q_table: \n",self._strategies[0].print_policy())
        self.update_learning("LeverEnv", action, old_pulled_lever.values, new_pulled_lever.values)
        #self.print("new q_table: \n",self._strategies[0].print_policy())
        return False
        
if __name__ == "__main__":
    env = Levers("LeverEnv")
    model = EnvModel(env)
    print(f'actions: {model.actions_list}  space: {model.states_list}')
    model.learn(qlearning, max_steps=50, num_episodes=100)
    for i in range(2):
        ag = LeverAgent()
        ag.add_policy(model)
        ag.add(Goal("decide_lever"))
        
    Admin().start_system()