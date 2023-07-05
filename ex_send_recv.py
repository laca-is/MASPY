from maspy.agent import Agent, Belief, Objective
from maspy.communication import Channel
from maspy.handler import Handler
import inspect 

class Sample(Agent):
    def __init__(self, agent_name, log=False):
        super().__init__(agent_name,full_log=log)
    
    @Agent.plan("print")
    def Sample_plan(self, src):
        self.print("Running Another Agent Plan")
        self.stop_cycle()
    
    @Agent.plan("send_info",("blf","Sender"))
    def send_info(self, src, msg):
        agents_list = self.find_in("Sample","Channel")["Receiver"]
        self.print(self.search("b","Sender",(2,)))
        for agent in agents_list:
            self.print(f"Sending> {agent}")
            self.send(agent,"achieve",("receive_info",msg))
            
        agents_list = self.find_in("test","Channel")["Test"]
        for agent in agents_list:
            pl = self.search("p","print")
            self.print(f"Sending> {pl} to {agent}")
            self.send(agent,"tellHow",pl)
        self.stop_cycle()

    @Agent.plan("receive_info",[("blf","Receiver")])
    def recv_info(self, src, msg):
        self.print(f"Information [{msg}] - Received from {src}")
        self.stop_cycle()

class test(Agent):
    def __init__(self, name):
        super().__init__(name,full_log=True)
    

if __name__ == "__main__":
    t = test("Test")
    t.add(Objective("print"))
    sender = Sample("Sender",False)    
    sender.add(Belief("Sender"))
    sender.add(Objective("send_info","Hello"))
    receiver = Sample("Receiver",False)
    receiver.add(Belief("Receiver"))
    Handler().connect_to([sender,receiver,t],[Channel()])
    Handler().start_all_agents()

