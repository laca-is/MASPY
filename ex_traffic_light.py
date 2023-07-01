from maspy.environment import Environment
from maspy.communication import Channel

from maspy.handler import Handler
from maspy.agent import Agent

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
        super().__init__(mg_name,full_log=False)
        
    @Agent.plan("traffic_light")
    def traffic_light(self,src,color):
        vehicles = self.find_in("Vehicle","Env","Cross_Junction")
        for vehicle in vehicles["Vehicle"]:
            self.print(f"Detected traffic light: {color} in env {src} - sending signal to {vehicle}")
            self.send(vehicle,"achieve",("crossing_over",),"Crossing")
    
class Vehicle(Agent):
    def __init__(self, vh_name):
        super().__init__(vh_name,full_log=False)
    
    @Agent.plan("crossing_over")
    def crossing(self,src):
        self.print(f"Confirmation for crossing by {src}")
        self.execute_in("Cross_Junction").cross(self)


if __name__ == "__main__":
    cross_channel = Channel("Crossing")
    cross_env = Crossing("Cross_Junction")
    cross_manager = Cross_Manager("Cross_Manager")
    vehicle = Vehicle("Vehicle")
    Handler().connect_to([(cross_manager,"Manager"),vehicle],
                             [cross_channel,cross_env])
    Handler().start_all_agents()