from maspy.agent import Agent
from maspy.communication import Channel
from maspy.coordinator import Coordinator

class Simple_Agent(Agent):
    def __init__(self, agent_name, log=False):
        super().__init__(agent_name,full_log=log)
        self.add_plan([
            ("send_information",[],Simple_Agent.send_information),
            ("run_information",[],Simple_Agent.run_information)
        ])
         
    def send_information(self, src, target, msg):
        self.send(target,"achieve",("run_information",msg))

    def run_information(self, src, info):
        self.print(f"Information [{info}] - Received from {src}!")

if __name__ == "__main__":
    ag1 = Simple_Agent("Ag",True)
    ag2 = Simple_Agent("Ag",True)
    Coordinator().connect_to([ag1,ag2],[Channel()])
    # Adding initial Objective
    ag1.add("blf","send_information",(ag2.my_name,"Hello from Ag1"))
    Coordinator().start_all_agents()

