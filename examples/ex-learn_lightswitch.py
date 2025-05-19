from maspy import *
from maspy.learning import *

class LightSwitch(Environment):
    def __init__(self):
        super().__init__()
        self.create(Percept("switch",("on","off"), listed))
    
    def switch_transition(self, state: dict, option: str):
        switch_state = state["switch"]
        if switch_state != option:
            reward = 1
            state["switch"] = option
        else:
            reward = -1

        return state, reward
        
    @action(listed, ("on","off"), switch_transition)
    def switch(self, agt, option: str):	
        switch = self.get(Percept("switch",Any))
        assert isinstance(switch, Percept)
        self.print(f'Light is {switch.args}')
        if switch.args == "on" and option == "off":
            self.print(f"{agt} Switching light off")
        elif switch.args == "off" and option == "on":
            self.print(f"{agt} Switching light on")
        else:
            self.print(f"{agt} Made no change by switching {option} - switch is {switch.args}")
    
class Flipper(Agent):
    @pl(gain, Goal("flipSwitch"))
    def flipSwitch(self, src):
        self.best_action("LightSwitch")
        self.stop_cycle()
    
if __name__ == "__main__":
    env = LightSwitch()
    model = EnvModel(env)
    print(f'actions: {model.actions_list}  space: {model.states_list}')
    model.learn(qlearning, max_steps=50, num_episodes=100)
    ag = Flipper()
    ag.add_policy(model)
    ag.add(Goal("flipSwitch"))
    Admin().start_system()