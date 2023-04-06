import inspect
import random
from functools import wraps
from agent import agent

class env:
    def __init__(self) -> None:
        self.agents = {}
        agent.send_msg = self.function_call(agent.send_msg)

    def add_agents(self, agent_list):
        for agent in agent_list:
            self.add_agent(agent)

    def add_agent(self, agent):
        #agent.my_name = f'{agent.my_name}#{random.randint(1000,9999)}' 
        if agent.my_name in self.agents:
            aux = agent.my_name.split('#')
            while "#".join(aux) in self.agents:
                aux[-1] = str(random.randint(1000,9999))
                
            agent.my_name = '#'.join(aux) 

        self.agents[agent.my_name] = agent
        print(f'Env> Adding agent {agent.my_name} to list')

    def start_all_agents(self):
        for agent_name in self.agents:
            self.start_agent(agent_name)
    
    def start_agents(self, agents):
        for agent_name in agents:
            self.start_agent(agent_name)

    def start_agent(self,agent_name):
        agent = self.agents[agent_name]
        agent.plans['reasoning'](agent)

    def get_connected_agents():
        pass

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

