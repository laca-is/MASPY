#ruff: noqa
from maspy import *

class Sample(Agent):
    @pl(gain,Belief("print"))
    def Sample_plan(self, src):
        self.print("Running Another Agent's Plan")
        self.stop_cycle()
    
    @pl(gain,Goal("send_info","Msg"),Belief("sender"))
    def send_info(self, src, msg):
        agents_list = self.find_in(["Sample","Receiver"],"Channel")
        for agent in agents_list:
            self.print(f"Sending> {msg} to {agent[0]}")
            self.send(agent[0],achieve,Goal("receive_info",msg))
            
        agents_list = self.find_in("Test")["Test"]
        for agent in agents_list:
            plan = self.get(Plan,Belief("print"))
            self.send(agent[0],tellHow,plan)
            self.send(agent[0],tell,Belief("print"))
            
        self.stop_cycle()

    @pl(gain,Goal("receive_info","Msg"),Belief("receiver"))
    def recv_info(self, src, msg):
        self.print(f"Information [{msg}] - Received from {src}")
        self.stop_cycle()

class Test(Agent):
    def __init__(self, name):
        super().__init__(name)
    

if __name__ == "__main__":
    Channel().show_exec = True
    t = Test("Test")
    t.add(Goal("print"))
    sender = Sample("Sender")    
    sender.add(Belief("sender"))
    sender.add(Goal("send_info","Hello"))
    receiver = Sample("Receiver")
    receiver.add(Belief("receiver"))
    Admin().start_system()

