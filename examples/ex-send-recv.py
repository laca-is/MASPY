from maspy import *

class Sender(Agent):
    @pl(gain, Goal("send_info", Any))
    def send_info(self, src, msg):
        self.print(f"Sending {msg} to Receiver")
        self.send("Recv",achieve,Goal("receive_info",msg)) 
        self.stop_cycle()
  
class Receiver(Agent):
    @pl(gain, Goal("receive_info", Any), Belief("Receiver"))
    def recv_info(self, src, msg):
        self.print(f"Received: {msg} from {src}")
        self.stop_cycle()
        
if __name__ == "__main__":
    Sender(goals=Goal("send_info", "Hello"))    
    Receiver("Recv",beliefs=Belief("Receiver"))
    Admin().start_system()
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    