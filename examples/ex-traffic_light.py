from maspy import *

class Crossing(Environment):
    def __init__(self, env_name):
        super().__init__(env_name)
        self.create(Percept("traffic_light","green"))
    
    def cross(self, src):
        self.print(f"Agent {src} is now crossing")

class Cross_Manager(Agent):
    @pl(gain, Belief("traffic_light", Any))
    def traffic_light(self,src,color):
        vehicles = self.list_agents("Vehicle","Env","Cross_Junction")
        for vehicle in vehicles:
            self.print(f"Detected traffic light: {color} in env {src} - sending signal to {vehicle}")
            self.send(vehicle,achieve,Goal("crossing_over"),"Crossing")
    
    @pl(gain,Belief("leaving_junction"))
    def end_watch(self,src):
        self.stop_cycle()

class Vehicle(Agent):
    def __init__(self, vh_name): 
        super().__init__(vh_name)
    
    @pl(gain,Goal("crossing_over"))
    def crossing(self,src):
        self.print(f"Confirmation for crossing by {src}")
        self.cross()
        self.print("Crossing Completed")
        self.send(src,tell,Belief("leaving_junction"),"Crossing")
        self.stop_cycle()


if __name__ == "__main__":
    cross_channel = Channel("Crossing")
    cross_env = Crossing("Cross_Junction")
    cross_manager = Cross_Manager("CrossManager")
    vehicle = Vehicle("Vehicle")
    Admin().connect_to([cross_manager,vehicle],[cross_channel,cross_env])
    Admin().start_system()
