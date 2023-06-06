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
        super().__init__(mg_name,full_log=True)
        self.add_plan([("traffic_light",[],Cross_Manager.traffic_light)])
    
    def traffic_light(self,src,color):
        vehicles = self.find_in("Env",src,"Vehicle")["Vehicle"]
        for vehicle in vehicles:
            self.print(vehicle,vehicles)
            self.print(f"Detected traffic light: {color} in env {src} - sending signal to {vehicle}")
            self.send(vehicle,"achieve",("crossing_over",),"Crossing")
    
class Vehicle(Agent):
    def __init__(self, vh_name):
        super().__init__(vh_name,full_log=True)
        self.add_plan([("crossing_over",[],Vehicle.crossing)])
    
    def crossing(self,src):
        self.print(f"Confirmation for crossing by {src}")
        self.execute("Cross_Junction").cross(self)
    

class HelloAgent(Agent):
    def __init__(self, name="AG"):
        super().__init__(name)
        self.print("Hello")


if __name__ == "__main__":
    ag = HelloAgent()

    sys.exit()
    #Channel
    cross_channel = Channel("Crossing")
    #Environment
    cross_env = Crossing("Cross_Junction")
    #Agents
    cross_manager = Cross_Manager("Cross_Manager")
    vehicle = Vehicle("Vehicle") 
    #Connections
    Coordinator().connect_to([(cross_manager,"Manager"),vehicle],
                             [cross_channel,cross_env])
    Coordinator().start_all_agents()