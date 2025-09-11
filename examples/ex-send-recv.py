from maspy import *

class Sender(Agent):
    @pl(gain, Goal("send_info", Any))
    def send_info(self, src, msg):
        self.print(f"[{self.cycle_counter}] Sending> {msg} to Receiver")
        self.send("Recv",achieve,Goal("recv_info",msg)) 
        self.stop_cycle()
  
class Receiver(Agent):
    @pl(gain, Goal("recv_info", Any))
    def recv_info(self, src, msg):
        self.print(f"[{self.cycle_counter}] Received: {msg} from {src}")
        self.stop_cycle()

if __name__ == "__main__":
    Sender(goals=Goal("send_info", "Hello"))    
    Receiver("Recv")
    Admin().start_system()