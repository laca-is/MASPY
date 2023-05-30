from maspy.agent import Agent, Plan, Objective
from maspy.communication import Comms

class Simple_Agent(Agent):
    def __init__(self, agent_name, log=False):
        super().__init__(agent_name,full_log=log)
        self.add_plan([
            Plan("send_information",[],Simple_Agent.send_information),
            Plan("run_information",[],Simple_Agent.run_information)
        ])

    def send_information(self, src, target, msg):
        self.send(target,"achieve",Objective("run_information",msg))

    def run_information(self, src, info):
        print(f"{self.my_name}> Information [{info}] - Received from {src}!")

if __name__ == "__main__":
    ag1 = Simple_Agent("Ag",True)
    ag2 = Simple_Agent("Ag")
    Comms().add_agents([ag1,ag2])
    ag1.add("o","send_information",(ag2.my_name,"Hello from Ag1"))
    ag1.reasoning_cycle()
    ag2.reasoning_cycle()
