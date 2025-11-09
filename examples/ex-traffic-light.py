from maspy import *
from random import choice

class Cross_Manager(Agent):
    @pl(gain, Belief("traffic_light", Any, "Crossing"))
    def traffic_light(self, src, color):
        vehicles = self.list_agents("Vehicle","Env","Cross_Junction")
        for vehicle in vehicles:
            self.print(f"Detected traffic light: {color} in env {src} - sending signal to {vehicle}")
            self.send(vehicle, achieve, Goal("crossing_over"), "Crossing")
    
    @pl(gain, Belief("leaving_junction"))
    def end_watch(self,src):
        self.stop_cycle()

class Vehicle(Agent):
    @pl(gain, Goal("crossing_over"))
    def crossing(self,src):
        self.print(f"Confirmation for crossing by {src}")
        self.cross()
        self.print("Crossing Completed")
        self.send(src, tell, Belief("leaving_junction"), "Crossing")
        self.stop_cycle()

class Crossing(Environment):
    def __init__(self, env_name):
        super().__init__(env_name)
        self.colors = ["red", "yellow", "green"]
        self.create(Percept("traffic_light", choice(self.colors)))
    
    def cross(self, agt):
        self.print(f"Agent {agt} is now crossing")

if __name__ == "__main__":
    cross_channel = Channel("Crossing")
    cross_env = Crossing("Cross_Junction")
    agent_list: list = [Cross_Manager("CrossManager")]
    for _ in range(3):
        agent_list.append(Vehicle())
    Admin().report = True
    Admin().connect_to(agent_list, [cross_channel, cross_env])
    Admin().start_system()