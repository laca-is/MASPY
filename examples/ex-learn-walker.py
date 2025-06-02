from maspy import *
from maspy.learning import *

from random import randint
from threading import Lock

NUM_WALKERS = 5
DIRECTIONS = [
    "up", "down",
    "left", "right"
]
MAP_SIZE = (10, 10)
steps: dict[str, int] = {}

def generate_targets():
    m, n = MAP_SIZE
    cx, cy = m // 2, n // 2 
    offsets = [(-1, 2), (3, -2), (-2, -3), (1, 4), (2, 1)]
    targets = []
    for dx,dy in offsets:
        x = min(max(cx + dx, 0), m - 1)
        y = min(max(cy + dy, 0), n - 1)
        targets.append((x,y))
    return targets

class Map(Environment):
    def __init__(self):
        self.pos_lock = Lock()
        super().__init__()
        
        self.moves = {
            "up": (1, 0),"down": (-1, 0), 
            "right": (0, 1), "left": (0, -1),
        }

        targets = generate_targets()
        self.create(Percept("target", targets, listed))
        self.create(Percept("position", MAP_SIZE, cartesian))
    
    def on_connect(self, agt):
        start_pos = (randint(0, MAP_SIZE[0]-4), randint(0, MAP_SIZE[1]-1))
        self.create(Percept("agt_position", start_pos, agt))
        self.print(f"Agent {agt} starts at {start_pos}")
    
    def moviment(self, position, direction):
        dx, dy = self.moves[direction]
        new_x = max(0, min(position[0] + dx, MAP_SIZE[0] - 1))
        new_y = max(0, min(position[1] + dy, MAP_SIZE[1] - 1)) 
        return new_x, new_y
    
    def move_transition(self, state: dict, direction: str):
        position = state["position"]
        
        state["position"] = self.moviment(position, direction)
         
        if state["position"] == state["target"]:
            reward = 10
            terminated = True
        else:
            reward = -1
            terminated = False

        return state, reward, terminated
    
    @action(listed, DIRECTIONS, move_transition)
    def move(self, agt, direction):
        global steps
        steps[agt] += 1
        position = self.get(Percept("agt_position", (Any, Any), agt), ck_group=True)
        assert isinstance(position, Percept)
        
        pos = position.args
        new_pos = self.moviment(pos, direction)
        self.change(position, new_pos)
        
        target = self.get(Percept("target", (Any, Any)))
        if isinstance(target, Percept) and new_pos == target.args:
            self.print(f"{agt} in {pos} moves {direction} and arrived at {target.args}")
            self.create(Percept("arrived_target", new_pos, agt))
        else:
            self.print(f"{agt} in {pos} moves {direction} to {new_pos}")
        
        
class Walker(Agent):
    def __init__(self):
        super().__init__()
        self.filter_perceptions(add, focus, self.my_name)
        
    @pl(gain, Goal("move"), Belief("target", (Any,Any)) & Belief("agt_position", (Any,Any)))
    def make_move(self, src, target, position):
        dx, dy = target[0] - position[0], target[1] - position[1]
        if dx != 0:
            direction = "up" if dx > 0 else "down"
        elif dy != 0:
            direction = "right" if dy > 0 else "left"
        else:
            direction = "stay"
            
        self.print(f'Knowing target {target} and my position {position}  - moving {direction}')
        self.move(direction)
        
        self.perceive("Map")
        if not self.has(Belief("arrived_target", (Any,Any), "Map")):
            return False
        else:
            global steps
            print("All Steps Taken: \n",steps)
            self.stop_cycle()
    
    @pl(gain, Goal("move"), Belief("agt_position", (Any, Any)))
    def best_move(self, src, position):
        self.print(f"Choosing best move in {position}")
        self.best_action('Map', (Any, position))
        self.perceive('Map')
        if not self.has(Belief("arrived_target", (Any,Any), "Map")):
            return False
        else:
            walkers = self.list_agents("Walker")
            for walker in walkers:
                if walker == self.my_name:
                    continue
                self.print(f"Sending target to {walker}")
                self.send(walker, tell, Belief("target", target))
            self.stop_cycle()
        
if __name__ == "__main__":
    map = Map()
    
    walkers: list[Walker] = []
    for i in range(NUM_WALKERS):
        walkers.append(Walker())
        steps[walkers[i].my_name] = 0
    Admin().connect_to(walkers, map)
    
    model = EnvModel(map)
    print(f'Actions: {model.actions_list}  Space: {model.observation_space}')
    #model.load_learning("Map_qlearning_0.05_0.8_1_0.1_5000_None.pkl")
    model.learn(qlearning, num_episodes=5000)
    model.reset_percepts()
    
    for walker in walkers:
        walker.add_policy(model)
        walker.add(Goal("move"))

    target = map.get(Percept("target", (Any, Any)))
    if isinstance(target, Percept):
        target = target.args
    Admin().print(f'Map size: {MAP_SIZE} - Target: {target}')
    
    Admin().start_system()