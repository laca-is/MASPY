from maspy.agent import Agent

class hello_agent(Agent):
    def __init__(self, agent_name):
        super().__init__(agent_name,full_log=True)

if __name__=="__main__":
    ag1 = hello_agent("Agent1")
    ag2 = hello_agent("Agent2")
    ag1.send(ag2.my_name,"tell",("b","a"))