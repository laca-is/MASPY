from maspy.agent import Agent
from maspy.environment import Environment
from maspy.communication import Channel
from maspy.coordinator import Coordinator
import sys

class Crossing(Environment):
    def __init__(self, env_name):
        super().__init__(env_name)
        self.create_fact("traffic_light","Green","Manager")
    
    def cross(self, src):
        self.print(f"Agent {src.my_name} is now crossing")
        for agent in self._agents:
            self._agents[agent].stop_cycle()

class Cross_Manager(Agent):
    def __init__(self, mg_name):
        super().__init__(mg_name)
        self.add_plan([("traffic_light",[],Cross_Manager.traffic_light)])
    
    def traffic_light(self,src,color):
        vehicle = self.find_in("Env","Crossing","Vehicle")
        self.print(f"Detected traffic light: {color} in env {src} - sending signal to {vehicle}")
        self.send(vehicle,"achieve",("crossing_over",),"Crossing")
    
class Vehicle(Agent):
    def __init__(self, vh_name):
        super().__init__(vh_name)
        self.add_plan([("crossing_over",[],Vehicle.crossing_over)])
    
    def crossing_over(self,src):
        self.print(f"Confirmation for crossing by {src}")
        self.execute("Crossing").cross(self)
    
if __name__ == "__main__":
    #Channel
    cross_channel = Channel("Crossing")
    #Environment
    cross_env = Crossing("Crossing")
    #Agents
    cross_manager = Cross_Manager("Cross_Manager")
    vehicle = Vehicle("Vehicle") 
    #Connections
    Coordinator().connect_to([(cross_manager,"Manager"),vehicle],
                             [cross_channel,cross_env])
    Coordinator().start_all_agents()