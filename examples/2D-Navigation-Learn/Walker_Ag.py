from maspy import *
from maspy.learning import *
from collections import deque
from random import choice
import heapq

def draw_ascii_map(graph, walls=None, target=None):
    if not graph:
        print("(empty graph)")
        return
    ys = [x for x, _ in graph.keys()]
    xs = [y for _, y in graph.keys()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    print("  ", end="")
    for x in range(min_y, max_y + 1):
        print(f"{x} ", end="")
    print()
    for y in range(min_x, max_x + 1):
        row = f"{y} "
        for x in range(min_y, max_y + 1):
            pos = (x, y)

            if pos == target:
                row += "X "
            elif pos in walls:
                row += "# "
            elif pos in graph:
                row += "o "   
            else:
                row += ". "      
        print(row)

def reconstruct_path(came_from, current):
    path = []
    while current is not None:
        path.append(current)
        current = came_from[current]
    return path[::-1]

def reconstruct_path_known(start, target, known):
    q = deque([start])
    prev = {start: None}

    while q:
        cur = q.popleft()
        if cur == target:
            return reconstruct_path(prev, cur)
        if cur not in known:
            continue
        for nxt in known[cur]:
            if nxt not in prev:
                prev[nxt] = cur
                q.append(nxt)
    return None

def astar_explore(start, goal, known, walls):
    walls = set(walls)       
    start = tuple(start)
    goal = tuple(goal)

    open_set = []
    heapq.heappush(open_set, (0, start))

    came_from = {}
    g = {start: 0}

    def h(p):
        return abs(goal[0] - p[0]) + abs(goal[1] - p[1])

    def neighbors(node):
        x, y = node
        all_nbrs = [
            (x+1, y),
            (x-1, y),
            (x, y+1),
            (x, y-1),
        ]

        valid = []
        for nxt in all_nbrs:
            if nxt in walls:
                continue
            valid.append(nxt)
        return valid

    while open_set:
        _, current = heapq.heappop(open_set)

        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            path.reverse()
            return path

        known_neighbors = known.get(current, set())
        unknown_neighbors = [n for n in neighbors(current) if n not in known_neighbors]
        
        for nxt in known_neighbors:
            new_cost = g[current] + 1
            if nxt not in g or new_cost < g[nxt]:
                g[nxt] = new_cost
                came_from[nxt] = current
                heapq.heappush(open_set, (new_cost + h(nxt), nxt))

        for nxt in unknown_neighbors:
            new_cost = g[current] + 1.25
            if nxt not in g or new_cost < g[nxt]:
                g[nxt] = new_cost
                came_from[nxt] = current
                heapq.heappush(open_set, (new_cost + h(nxt), nxt))

    return None 

def astar_direction(ag, position, target):
    map_graph = ag.get(Belief("Path_Graph", Any))
    wall_set = ag.get(Belief("Wall_Set", Any))
    path = astar_explore(position, target, map_graph.values, wall_set.values)
    if path is None:
        path = []
    if len(path) > 1:
        target = path[1]
        
    dx, dy = target[0] - position[0], target[1] - position[1]
    if dx == 0 and dy == 0:
        direction = "stay"
    elif abs(dy) >= abs(dx):
        direction = "down" if dy > 0 else "up"
    else:
        direction = "right" if dx > 0 else "left"
    return direction

class Walker(Agent):
    def __init__(self, name, map: Environment, episodes: int):
        super().__init__(name, max_intentions=1)
        self.filter_perceptions(add, focus, self.my_name)
        #self.show_slct = True
        #self.show_cycle = True
        model = EnvModel(map, self, True)
        self.add_policy(model)
        state = model.env.get(Percept("agt_position", (Any, Any), self.my_name), ck_group=True)
        assert isinstance(state, Percept)
        model.initial_states = {"position": [state.values]}
        #print(f"Agent {self.my_name} starts at {state.values}")
        model.learn(qlearning, num_episodes=episodes)
        self.reset_knowledge()
    
    def reset_knowledge(self):
        self.rm(Belief("Path_Graph", Any))
        self.add(Belief("Path_Graph", dict()))
        self.rm(Belief("Wall_Set", Any))
        self.add(Belief("Wall_Set", []))
        self.add(Goal("move"))
    
    def update_map(self, position, direction):
        map_graph = self.get(Belief("Path_Graph", Any))
        wall_list = self.get(Belief("Wall_Set", Any))
        new_pos = self.get(Belief("agt_position", (Any,Any), "Map"))
        assert (map_graph and wall_list and new_pos), f"{map_graph} | {wall_list} | {new_pos}"
        if new_pos.values not in map_graph.values:
            old_graph = map_graph.values
            old_graph.setdefault(position, set()).add(new_pos.values)
            old_graph.setdefault(new_pos.values, set()).add(position)
            map_graph.change(values=old_graph)
            self.send(broadcast, tell, Belief("Sent_Graph", old_graph))
        if new_pos.values == position and direction != "stay":
            match direction:
                case "up": wall_pos = (position[0],position[1]-1)
                case "down": wall_pos = (position[0],position[1]+1)
                case "left": wall_pos = (position[0]-1,position[1])
                case "right": wall_pos = (position[0]+1,position[1])
            walls = wall_list.values
            if wall_pos not in walls:
                walls.append(wall_pos)
                self.print(f"Driver {self.my_name} found a wall at {wall_pos} added to {walls}")
                self.send(broadcast, tell, Belief("Sent_Walls", walls))

    @pl(gain, Goal("move"), Belief("target", (Any,Any)) & Belief("agt_position", (Any,Any), "Map"))
    def best_move(self, src, target, position):
        direction = astar_direction(self, position, target) 
        self.print(f'Knowing target {target} and my position {position}  - moving {direction}')
        if direction != "stay": self.move(direction)
        
        self.perceive("Map") # Manual Perception of Map
        self.update_map(position, direction) # Update of Map/Wall Beliefs
        
        if not self.has(Belief("arrived_target", (Any,Any), "Map")):
            return False # Retries current event
        else:
            self.print(f"Driver {self.my_name} arrived at {target}")
            self.stop_cycle()
            
    @pl(gain, Goal("move"), Belief("agt_position", (Any,Any), "Map"))
    def make_move(self, src, position):
        if self.has(Belief("use_learn")):
            direction, _ = self.get_best_action("Map",(position,))
            self.print(f"From {position} Moving on a Learned Direction ({direction})")
        else:
            direction = choice(["up", "down", "left", "right"])
            self.print(f"From {position} Moving on a Random Direction ({direction})")
        self.move(direction) # Move Action

        self.perceive("Map") # Manual Perception of Map
        self.update_map(position, direction) # Update of Map/Wall Beliefs
            
        if not self.has(Belief("arrived_target", (Any,Any), "Map")):
            return False # Retries current event 
        
        target = self.get(Belief("arrived_target", (Any,Any), "Map"))
        self.print(f"Driver {self.my_name} arrived at {target} first, sending target")
        self.send(broadcast, tell, Belief("target", target.values))
        self.print(f"Driver {self.my_name} finished broadcast")
        self.stop_cycle()
    
    @pl(gain, Belief("Sent_Graph", Any), plan_type=atomic)
    def update_graph(self, src, sent_graph):
        map_graph = self.get(Belief("Path_Graph", Any))
        old_graph = map_graph.values
        for node, neighbors in sent_graph.items():
            if node not in old_graph:
                old_graph[node] = set(neighbors)
            else:
                old_graph[node] |= neighbors
        map_graph.change(values=old_graph)
    
    @pl(gain, Belief("Sent_Walls", Any), plan_type=atomic)
    def update_walls(self, src, sent_graph):
        wall_set = self.get(Belief("Wall_Set", Any))
        old_set = wall_set.values
        if sent_graph[0] not in old_set:
            old_set.append(sent_graph[0])
            wall_set.change(values=old_set)
