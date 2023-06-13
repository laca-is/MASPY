from maspy.agent import Agent
from maspy.communication import Channel
from maspy.handler import Handler

class Sample(Agent):
    def __init__(self, agent_name, log=False):
        super().__init__(agent_name,full_log=log)
        self.add_plan([
            ("send_info",[("blf","Sender")],Sample.send_info),
            ("receive_info",[],Sample.recv_info)
        ])
         
    def send_info(self, src, msg):
        agents_list = self.find_in("Sample","Channel")["Receiver"]
        for agent in agents_list:
            self.send(agent,"achieve",("receive_info",msg))
        self.stop_cycle()

    def recv_info(self, src, msg):
        self.print(f"Information [{msg}] - Received from {src}")
        self.stop_cycle()

if __name__ == "__main__":
    sender = Sample("Sender",True)
    sender.add("belief","Sender")
    sender.add("obj","send_info",("Hello",))
    receiver = Sample("Receiver",True)
    Handler().connect_to([sender,receiver],[Channel()])
    Handler().start_all_agents()

