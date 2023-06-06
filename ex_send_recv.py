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
         
    def send_information(self, src, msg):
        agents_list = ag1.find_in("Ch","comm","Simple_Agent")
        for agents in agents_list.values():
            for agent in agents:
                if self.my_name != agent:
                    self.send(agent,"achieve",("run_information",msg))
        self.stop_cycle()

    def run_information(self, src, info):
        self.print(f"Information [{info}] - Received from {src}!")
        self.stop_cycle()

if __name__ == "__main__":
    ag1 = Simple_Agent("Ag",True)
    ag2 = Simple_Agent("Ag",True)
    Coordinator().connect_to([ag1,ag2],[Channel()])
    # Adding initial Objective
    ag1.add("obj","send_information",(f"Hello from the other side"))
    Coordinator().start_all_agents()

