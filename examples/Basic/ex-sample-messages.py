from maspy import *

class Sample(Agent):
    @pl(gain, Goal("print"))
    def Sample_plan(self, src):
        self.print(f"Running the Agent {src} Plan")
        self.stop_cycle()
    
    @pl(gain, Goal("send_info", Any), Belief("sender"))
    def send_info(self, src, msg):
        agents_list = self.list_agents("Sample")
        for agent in agents_list:
            if agent == self.my_name:
                continue
            self.print(f"Sending> {msg} to {agent}")
            self.send(agent, achieve, Goal("receive_info", msg))
        
        self.wait(5, Event(gain, Belief("info_received")))
        self.print("Receiver got the message")
        
        agents_list = self.list_agents("Test")
        for agent in agents_list:
            plan = self.get(Plan, Goal("print"))
            self.send(agent, tellHow, plan)
            self.send(agent, achieve, Goal("print"))

        self.stop_cycle()

    @pl(gain, Goal("receive_info", Any), Belief("receiver"))
    def recv_info(self, src, msg):
        self.print(f"Information [{msg}] - Received from {src}")
        blf = self.send(src, askOneReply, Belief("value", Any))
        if blf:
            self.print(f"Got {blf.values} from {blf.source}")
        self.send(src, tell, Belief("info_received"))
        self.stop_cycle()

class Test(Agent):
    ...
    
if __name__ == "__main__":
    Channel(show_exec=True)
    Test()
    sender = Sample("Sender", beliefs=[Belief("sender"), Belief("value",42)], goals=Goal("send_info","Hello"))    
    
    receiver = Sample("Receiver", Belief("receiver"))
    Admin().start_system()
