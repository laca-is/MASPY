from maspy import *

class SimpleEnv(Environment):
    def env_act(self, agt, agent2):
        self.print(f"Contact between {agt} and {agent2} (Ctrl+C to End Program)")

class SimpleAgent(Agent):
    @pl(gain,Goal("say_hello", Any))
    def send_hello(self,src,agent):
        self.send(agent,tell,Belief("Hello"),"SimpleChannel")

    @pl(gain,Belief("Hello"))
    def recieve_hello(self,src):
        self.print(f"Hello received from {src}")
        self.env_act(src)

if __name__ == "__main__":
    Admin().console_settings(show_exec=True)
    agent1 = SimpleAgent()
    agent2 = SimpleAgent()
    env = SimpleEnv()
    ch = Channel("SimpleChannel")
    Admin().connect_to([agent1,agent2],[env,ch])
    agent1.add(Goal("say_hello",(agent2.my_name,)))

    Admin().start_system()
