from maspy import *

class Room(Environment):
    def add_dirt(self, agent, position):
        self.print(f"Dirt created in position {position}")
        dirt_status = self.get(Percept("dirt","Statuses"))
        dirt_status.args[position] = False # changes the dict inside percept
    
    def clean_position(self, agent, position):
        self.print(f"{agent} is cleaning position {position}")
        dirt_status = self.get(Percept("dirt","Statuses"))
        if dirt_status.args[position] is False:
            dirt_status.args[position] = True # changes the dict inside percept

class Robot(Agent):
    def __init__(self, name, initial_env=None, full_log=False):
        super().__init__(name, show_exec=full_log)
        self.connect_to(initial_env)
        self.add(Goal("decide_move"))
        self.add(Belief("room_is_dirty"))
        self.position = (0,0)
        self.print(f"Inicial position {self.position}")

    @pl(gain,Goal("decide_move"))
    def decide_move(self,src):
        min_dist = float("inf")
        target = None
 
        dirt_pos = self.get(Belief("dirt","Pos","Room"))
        print(f"{dirt_pos.args}")
        x, y = self.position
        for pos, clean in dirt_pos.args.items():
            if not clean:
                dist = abs(pos[0]-x) + abs(pos[1]-y)
                if dist < min_dist:
                    min_dist = dist
                    target = pos
                    
        if target is None:
            self.print(f"All dirt is cleaned")
            self.rm(Belief("room_is_dirty"))
            self.add(Belief("room_is_clean"))
            print("*** Finished Cleaning ***")
            Admin().stop_all_agents()
        else:
            self.print(f"Moving to {target}")
            self.add(Goal("move",target))
    
    @pl(gain,Goal("clean_dirt"))                            
    def clean(self,src):
        if self.has(Belief("room_is_dirty")):
            self.clean_position(self.position)
            self.add(Goal("decide_move"))
    
    @pl(gain,Goal("move",("X","Y")))
    def move(self,src,target):
        tgX,tgY = target
        x, y = self.position

        self.print(tgX,tgY," - ",x,y)
        if x != tgX:
            diff = tgX - x
            direction = (int(diff/abs(diff)),0)
        elif y != tgY:
            diff = tgY - y
            direction = (0,int(diff/abs(diff)))
        
        match direction:
            case (0,1): self.print(f"Moving Down")
            case (0,-1): self.print(f"Moving Up")
            case (-1,0): self.print(f"Moving Left")
            case (1,0): self.print(f"Moving Right")
        
        self.position = (x+direction[0],y+direction[1])
        self.print(f"New position: {self.position}")
        
        if self.position == (tgX,tgY):
            self.print(f"Reached dirt position")
            self.add(Goal("clean_dirt"))
            return
        else:
            self.add(Goal("move",(tgX,tgY)))

if __name__ == "__main__":
    env = Room()
    env.create(Percept("dirt",{(0,1): False, (2,2): False}))
    rbt = Robot('R1', initial_env=env, full_log=False)
    Admin().start_system()
