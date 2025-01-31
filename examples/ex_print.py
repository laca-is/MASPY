from maspy import *

class dummy_agent(Agent):
    def __init__(self, name):
        super().__init__(name)
    
    @pl(gain, Belief("make_action",Any))
    def action_on_env(self, src, env_name):
        self.env_action()
        self.stop_cycle()
        
class simple_env(Environment):
    def  __init__(self, env_name=None):
        super().__init__(env_name)
        
    def env_action(self, src):
        self.print(f"Action by {src}")

if __name__=="__main__":
    ag1 = dummy_agent("Ag1")
    ag1.connect_to(simple_env("s_env"))
    ag1.add(Belief("make_action","s_env"))
    Admin().start_system()
    
    


    
    
    