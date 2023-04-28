import inspect
import random
from threading import Lock
from functools import wraps
from maspy.agent import agent, Belief

class commsMeta(type):
    _instances = {}
    _lock: Lock = Lock()
    
    def __call__(cls, __my_name='comm'):
        with cls._lock:
            if __my_name not in cls._instances:
                instance = super().__call__(__my_name)
                cls._instances[__my_name] = instance
        return cls._instances[__my_name]

class comms(metaclass=commsMeta):
    def __init__(self, env_name) -> None:
        self.__my_name = env_name
        agent.send_msg = self.function_call(agent.send_msg)
    
    def add_agents(self, agents):
        try:
            for agent in agents:
                self._add_agent(agent)
        except(TypeError):
            self._add_agent(agents)


    def _add_agent(self, agent):
        agent.my_name = f'{agent.my_name}#{random.randint(1000,9999)}' 
        if agent.my_name in self.__agents:
            aux = agent.my_name.split('#')
            while "#".join(aux) in self.__agents:
                aux[-1] = str(random.randint(1000,9999))
                
            agent.my_name = '#'.join(aux) 
        self.__agent_list[agent.my_name] = type(agent).__name__
        self.__agents[agent.my_name] = agent
        print(f'{self.__my_name}> Connecting agent {type(agent).__name__}:{agent.my_name} to channel')

    def _rm_agents(self, agents):
        try:
            for agent in agents:
                self._rm_agent(agent)
        except(TypeError):
            self._rm_agent(agents)
        self.send_agents_list()
    
    def _rm_agent(self, agent):
        if agent.my_name in self.__agents:
            del(self.__agents[agent.my_name])
            del(self.__agent_list[agent.my_name])
        print(f'{self.__my_name}> Desconnecting agent {type(agent).__name__}:{agent.my_name} from channel')

    def send_agents_list(self):
        for agent_name in self.__agents:
            self.__agents[agent_name].recieve_msg(agent_name,'env_tell',Belief('Agents',[self.__agent_list]))

         
    def function_call(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            arg_values = inspect.getcallargs(func, *args, **kwargs)
            msg = {}
            for key,value in arg_values.items():
                msg[key] = value 
            try:
                self.__agents[msg['target']].recieve_msg(msg['self']\
                                .my_name,msg['act'],msg['msg'])
            except(KeyError):
                print(f"Agent {msg['target']} doesn't exist")

        
            return func(*args, **kwargs)
        
        return wrapper

