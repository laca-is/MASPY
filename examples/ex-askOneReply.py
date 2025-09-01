from maspy import *

class Sample(Agent):
    @pl(gain, Goal("ask",Any), 
        ~Belief("Test1",Any) & (Belief("Test2", Any) > 10) 
        )
    def asking(self,src,name,test2):
        self.print(f"asking {name} for value - test2={test2}")    
        value = self.send(name, askOneReply, Belief("value", Any))
        if value:
            self.print(f"Got {value} from {value.source}")
        
        Admin().stop_all_agents()
        
    
    @pl(gain,Belief("value1", (Any,Any,Any)), 
        (Belief("value2", (Any,Any,Any)) > (0,6,0)) | 
        (Belief("value2", (Any,Any,Any)) | (Belief("value3", (Any,Any,Any)) > (0,9,0)))
        )
    def got_value(self,src,value, value1, value2, value3):
        self.print(f"Got {value} and {value1} or ({value2} or {value3}) from {src}")

if __name__ == '__main__':
    ag = Sample("Ag")
    ag.add(Belief("value1", (1,2,3)))
    ag.add(Belief("value2", (4,5,6)))
    ag.add(Belief("value3", (7,8,9)))
    
    ag1 = Sample("asking")
    ag2 = Sample("informant")
    ag1.add(Goal("ask","informant"))
    #ag1.add(Belief("Test1","hello")) # uncomment to break
    ag1.add(Belief("Test2",50))
    ag2.add(Belief("value",42))
    Admin().start_system()
    
