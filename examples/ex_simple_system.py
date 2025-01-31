from maspy import * 

class SimpleEnv(Environment):
    def env_act(self, agent1, agent2):
        self.print(f"Contact between {agent1} and {agent2}")

class SimpleAgent(Agent):
    @pl(gain,Goal("say_hello","Agent"))
    def send_hello(self,src,agent):
        self.send(broadcast,tell,Belief("Hello",42),"SimpleChannel")
        self.stop_cycle()

    @pl(gain,Belief("Hello","Value"))
    def recieve_hello(self,src,value):
        self.print(f"Hello and {value} received from {src}")
        self.env_act(src)
        self.stop_cycle()

if __name__ == "__main__":
    agent1 = SimpleAgent()
    agent2 = SimpleAgent()
    env = SimpleEnv()
    Change = Channel("SimpleChannel")
    Admin().connect_to([agent1,agent2],[env,Change])
    agent1.add(Goal("say_hello",(agent2.tuple_name,)))
    Admin().start_system()
    