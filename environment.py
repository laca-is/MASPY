import inspect
import random
from functools import wraps
from agent import agent, Belief, Ask, Objective

class env:
    def __init__(self, env_name='Env') -> None:
        self.env_name = env_name
        self.agent_list = {}
        self.agents = {}
        agent.send_msg = self.function_call(agent.send_msg)

    def add_agents(self, agent_list):
        for agent in agent_list:
            self.add_agent(agent)

    def add_agent(self, agent):
        agent.my_name = f'{agent.my_name}#{random.randint(1000,9999)}' 
        if agent.my_name in self.agents:
            aux = agent.my_name.split('#')
            while "#".join(aux) in self.agents:
                aux[-1] = str(random.randint(1000,9999))
                
            agent.my_name = '#'.join(aux) 
        self.agent_list[agent.my_name] = type(agent).__name__
        self.agents[agent.my_name] = agent
        print(f'{self.env_name}> Connecting agent {type(agent).__name__}:{agent.my_name} to environment')

    def start_all_agents(self):
        self.send_agents_list()
        print(f'{self.env_name}> Starting all connected agents')
        for agent_name in self.agents:
            self._start_agent(agent_name)
    
    def start_agents(self, agents):
        self.send_agents_list()
        print(f'{self.env_name}> Starting listed agents')
        for agent_name in agents:
            self._start_agent(agent_name)

    def _start_agent(self,agent_name):
        agent = self.agents[agent_name]
        agent.reasoning()

    def send_agents_list(self):
        for agent_name in self.agents:
            self.agents[agent_name].recieve_msg(agent_name,'env_tell',Belief('Agents',[self.agent_list]))
            
    def function_call(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            arg_values = inspect.getcallargs(func, *args, **kwargs)
            #print(arg_values)
            msg = {}
            for key,value in arg_values.items():
                msg[key] = value
            try:
                self.agents[msg['target']].recieve_msg(msg['self']\
                                .my_name,msg['act'],msg['msg'])
            except(KeyError):
                print(f"Agent {msg['target']} doesn't exist")

        
            return func(*args, **kwargs)
        
        return wrapper

