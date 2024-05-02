from maspy import *

class HelloAgent(Agent):
    @pl(gain,Belief("hello"))
    def func(self,src):
        self.print("Hello World")
        self.stop_cycle()
        
class DummyAgent(Agent):
    pass

ag = DummyAgent()
ag2 = DummyAgent("Ag")
agent = HelloAgent()
agent.add(Belief("hello"))
Admin().start_system()