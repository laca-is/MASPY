from maspy import *

class HelloAgent(Agent):
    @pl(gain,Belief("hello"))
    def func(self, src):
        self.print(f"Hello World!")
        self.stop_cycle()
 
if __name__ == "__main__":
    ag = HelloAgent(beliefs=Belief("hello"))
    Admin().start_system()
    
    
    
    
    
    
    
    
    
    
    
    
    