from maspy import *

class HelloAgent(Agent):
    @pl(gain,Belief("hello"))
    def func(self,src):
        self.print("Hello World")
        self.stop_cycle()
    
agent = HelloAgent()
agent.add(Belief("hello"))
Admin().start_system()