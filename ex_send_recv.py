from maspy.agent import Agent, Belief, Objective
from maspy.communication import Channel
from maspy.handler import Handler
import inspect 

class Sample(Agent):
    def __init__(self, agent_name, log=False):
        super().__init__(agent_name,full_log=log)
    
    @Agent.plan("send_info",[("blf","Sender")])
    def send_info(self, src, msg):
        agents_list = self.find_in("Sample","Channel")["Receiver"]
        self.print(self.search("b","Sender",(2,)))
        for agent in agents_list:
            self.send(agent,"achieve",("receive_info",msg))
        self.stop_cycle()

    @Agent.plan("receive_info",[("blf","Receiver")])
    def recv_info(self, src, msg):
        self.print(f"Information [{msg}] - Received from {src}")
        self.stop_cycle()

if __name__ == "__main__":
    sender = Sample("Sender",True)    
    sender.add(Belief("Sender"))
    sender.add(Objective("send_info","Hello"))
    receiver = Sample("Receiver",True)
    receiver.add(Belief("Receiver"))
    Handler().connect_to([sender,receiver],[Channel()])
    Handler().start_all_agents()

