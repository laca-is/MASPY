from maspy.agent import Agent

class hello_agent(Agent):
    def __init__(self, agent_name):
        super().__init__(agent_name)
        print(f"{self.my_name}> Hello World!")

if __name__=="__main__":
    hello_agent("Agent")