from maspy import *
from maspy.learning import *
from collections import deque
from random import randint
import random

def generate_map_with_walls(width, height, target, wall_prob=0.1, max_attempts=2000):
    def neighbors(x, y):
        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
            nx, ny = x+dx, y+dy
            if 0 <= nx < width and 0 <= ny < height:
                yield nx, ny

    for _ in range(max_attempts):
        walls = {(x, y) for x in range(width) for y in range(height)
                 if random.random() < wall_prob and (x, y) != target}

        queue = deque([target])
        reachable = {target}
        while queue:
            cx, cy = queue.popleft()
            for nx, ny in neighbors(cx, cy):
                if (nx, ny) not in walls and (nx, ny) not in reachable:
                    reachable.add((nx, ny))
                    queue.append((nx, ny))

        total_open = width * height - len(walls)
        if len(reachable) == total_open:
            available = sorted(reachable)
            return walls, available

    raise RuntimeError("Failed to generate a valid map.")

class Map(Environment):
    def __init__(self, map_size, walls_prob):
        super().__init__()
        self.moves = {
            "up": (0, -1),"down": (0, 1), 
            "right": (1, 0), "left": (-1, 0),
        }
        self.map_size = map_size
        target = (randint(0, self.map_size[0]-1), randint(0, self.map_size[1]-1))
        self.print(f"Target is at {target}")
        positions = generate_map_with_walls(map_size[0], map_size[1], target, walls_prob, 2000)

        self.create(Percept("target", target))
        for wall in positions[0]:
            self.create(Percept("wall", wall))
        self.create(Percept("position", positions[1], listed))
        self.possible_starts = "off-policy"
        
    def on_connect(self, agt):
        target = self.has(Percept("target", (Any,Any))).values
        while True:
            start_pos = (randint(0, self.map_size[0]-1), randint(0, self.map_size[1]-1))
            if not self.has(Percept("wall", start_pos)) and (abs(start_pos[0] - target[0]) + abs(start_pos[1] - target[1])) > self.map_size[0]/2:
                break
        self.create(Percept("agt_position", start_pos, agt))
        self.print(f"Agent {agt} starts at {start_pos}")
    
    def moviment(self, position, direction):
        dx, dy = self.moves[direction]
        new_x = max(0, min(position[0] + dx, self.map_size[0] - 1))
        new_y = max(0, min(position[1] + dy, self.map_size[1] - 1)) 
        return new_x, new_y
    
    def move_transition(self, position, direction):
        reward = -1
        terminated = False
        
        new_position = self.moviment(position, direction)
        target = self.get(Percept("target", (Any, Any)))
        if new_position == target.values:
            reward = 10
            terminated = True
        elif self.has(Percept("wall", new_position)) or position == new_position:
            reward = -10
        return new_position, reward, terminated
    
    @action(listed, ["up", "down", "left", "right"], move_transition)
    def move(self, agt, direction):
        position = self.get(Percept("agt_position", (Any, Any), agt), ck_group=True)
        assert isinstance(position, Percept)
        
        wall_flag = False
        pos = position.values
        if direction == "stay":
            new_pos = pos
        else:
            new_pos = self.moviment(pos, direction)
            if self.has(Percept("wall", new_pos)):
                wall_flag = True
                new_pos = pos
            else:
                position.change(values=new_pos)
        
        n_pos = self.get(Percept("agt_position", (Any, Any), agt), ck_group=True).values
        target = self.get(Percept("target", (Any, Any)))
        if isinstance(target, Percept) and n_pos == target.values:
            self.print(f"{agt} in {pos} moves {direction} and arrived at {target.values}")
            self.create(Percept("arrived_target", n_pos, agt))
        elif wall_flag:
            self.print(f"{agt} in {pos} moves {direction} but hits a wall")
        else:
            self.print(f"{agt} in {pos} moves {direction} to {n_pos}")