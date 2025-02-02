from maspy import *

class Sample(Agent):
    @pl(gain, Goal("ask",Any), 
        ~Belief("Test1",Any) & Belief("Test2", Any) > 10 )
    def asking(self,src,name,test2):
        self.print(f"asking {name} for value - test2={test2}")    
        value = self.send(name, askOneReply, Belief("value", Any))
        self.print(f"Got {value} from {value.source}")
    
    @pl(gain,Belief("value", Any))
    def got_value(self,src,value):
        self.print(f"Got {value} from {src}")

if __name__ == '__main__':
    ag1 = Sample("asking")
    ag2 = Sample("informant")
    ag1.add(Goal("ask","informant"))
    #ag1.add(Belief("Test1","hello")) 
    ag1.add(Belief("Test2",50))
    ag2.add(Belief("value",42))
    #Admin().report = True
    Admin().start_system()
    