from maspy import *

class SimpleEnv(Environment):
    def env_act(self, agent1, agent2):
        self.print(f"Contact between {agent1} and {agent2}")

class SimpleAgent(Agent):
    @pl(gain,Goal("say_hello","Agent"))
    def send_hello(self,src,agent):
        self.send(agent,tell,Belief("Hello"),"SimpleChannel")

    @pl(gain,Belief("Hello"))
    def recieve_hello(self,src):
        self.print(f"Hello received from {src}")
        self.action("SimpleEnv").env_act(self.my_name,src)

if __name__ == "__main__":
    Admin().set_logging(full_log=True)
    agent1 = SimpleAgent()
    agent2 = SimpleAgent()
    env = SimpleEnv()
    ch = Channel("SimpleChannel")
    Admin().connect_to([agent1,agent2],[env,ch])
    agent1.add(Goal("say_hello",(agent2.my_name,)))
    Admin().start_system()