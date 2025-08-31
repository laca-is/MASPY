from maspy import *

class Sample(Agent):
    @pl(gain, Goal("ask",Any), 
        ~Belief("Test1",Any) & Belief("Test2", Any) > 10 
        )
    def asking(self,src,name,test2):
        self.print(f"asking {name} for value - test2={test2}")    
        value = self.send(name, askOneReply, Belief("value", Any))
        self.print(f"Got {value} from {value.source}")
        
    
    @pl(gain,Belief("value", (Any,Any,Any)), 
        (Belief("value2", (Any,Any,Any)) > (0,6,0)) | 
        (Belief("value2", (Any,Any,Any)) | (Belief("value3", (Any,Any,Any)) > (0,9,0)))
        )
    def got_value(self,src,value, value1, value2, value3):
        self.print(f"Got {value} and {value1} or ({value2} or {value3}) from {src}")
        self.stop_cycle()

if __name__ == '__main__':
    ag = Sample("Ag")
    ag.add(Belief("value", (1,2,3)))
    ag.add(Belief("value2", (4,5,6)))
    ag.add(Belief("value3", (7,8,9)))
    Admin().start_system()

    
