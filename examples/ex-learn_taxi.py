
# ruff : noqa: F403, F405
from maspy import *
from maspy.learning import *
import numpy as np
from time import sleep

MAP = [
    "+---------+",
    "|R: | : :G|",
    "| : | : : |",
    "| : : : : |",
    "| | : | : |",
    "|Y| : |B: |",
    "+---------+",
]

class Taxi(Environment):
    def __init__(self, env_name) -> None:
        super().__init__(env_name)
        self.desc: np.ndarray = np.asarray(MAP, dtype="c")
        
        self.destinations = {"R":(1,2), "G":(4,4), "Y":(3,4), "B":(1,3)}
        
        self.create(Percept("taxi_location", (5,5), cartesian)) # 25 possibilites
        self.create(Percept("Passenger_loc",["R","G","Y","B","T"], listed)) # 5 possibilites
        self.create(Percept("Destination", list(self.destinations.values()), listed)) # 4 possibilites
        
        self.possible_starts = {"taxi_location": [(0,0),(2,2)], "Passenger_loc": ["R","G","Y","B"], "Destination": [(1,2),(4,4),(3,4),(1,3)]}
        
        self.max_row = 4
        self.max_col = 4
    
    def move_transition(self, state: dict, direction: str):
        taxi = state["taxi_location"]

        position = self.moviment(taxi, direction)
        
        passgenger = state["Passenger_loc"]
        if passgenger == "T":
            reward = 1
        else:
            reward = -1

        state["taxi_location"] = position
        
        return state, reward
    
    def moviment(self, position, direction):
        new_row, new_col = position
        if direction == "down": 
            new_row = min(new_row + 1, self.max_row)
        if direction == "up":
            new_row = max(new_row - 1, 0)
        if direction == "right" and self.desc[1 + new_row, 2 * new_col + 2] == b":":
            new_col = min(new_col + 1, self.max_col)
        if direction == "left" and self.desc[1 + new_row, 2 * new_col] == b":":
            new_col = max(new_col - 1, 0)
        return (new_col, new_row)

    def pickup_transition(self, state: dict):
        taxi = state["taxi_location"]
        passgenger = state["Passenger_loc"]
        if passgenger == "T":
            reward = -10
        elif self.destinations[passgenger] == taxi:
            state["Passenger_loc"] = "T"
            reward = 1
        else:
            reward = -10
            
        return state, reward
    
    def drop_off_transition(self,state: dict):
        terminated = False
        taxi = state["taxi_location"]
        passager = state["Passenger_loc"]
        destination = state["Destination"]
        if passager == "T" and destination == taxi:
            reward = 100
            terminated = True
            state["Passenger_loc"] = "D"
        else:
            reward = -10
        
        return state, reward, terminated
    
    @action(listed, ["down","up","right","left"], move_transition)
    def move(self, agt, direction: str):
        self.print(f"{agt} is Moving {direction}")
        percept = self.get(Percept("taxi_location", (Any,Any)))
        assert isinstance(percept, Percept)
        position = self.moviment(percept.args, direction)
        self.change(percept, position)
        self.print_percepts

    @action(listed, "pickup", pickup_transition)
    def pickup(self, agt):
        pass_loc = self.get(Percept("Passenger_loc",Any))
        taxi_loc = self.get(Percept("taxi_location", (Any,Any)))
        if pass_loc.args == "T":
            self.print("Passanger already on Taxi")
        elif taxi_loc.args == self.destinations[pass_loc.args]:
            self.change(pass_loc, "T")
            self.print(f"{agt} is picking up a passenger at {taxi_loc.args} position")
        else:
            self.print(f"No passanger at {taxi_loc.args} position")
        self.print_percepts

    @action(listed, "dropoff", drop_off_transition)
    def drop_off(self, agt):
        pass_loc = self.get(Percept("Passenger_loc",Any))
        taxi_loc = self.get(Percept("taxi_location", (Any,Any)))
        dest_loc = self.get(Percept("Destination", (Any,Any)))
        if pass_loc.args == "T":
            if taxi_loc.args == dest_loc.args:
                self.print(f'{agt} is dropping off passenger at destination {dest_loc.args}')
                self.change(pass_loc, "D")
            else:
                self.print(f'{agt} is trying to drop passenger at {taxi_loc.args} position')
        else:
            self.print(f"{agt} is dropping off without a passenger")
        self.print_percepts

class Sample(Agent):
    @pl(gain,Goal("aquire_learning", Any))
    def aquire_learning(self,src, model):
        self.print("Aquiring learning model")
        self.add_policy(model[0])
        self.auto_action = True

if __name__ == "__main__":
    env = Taxi("Grid")
    model = EnvModel(env)
    print(f'actions: {model.actions_list}  space: {model.observation_space}')
    model.learn(qlearning)
    Sample("Ag").add(Goal("aquire_learning",[model]))
    Admin().start_system()