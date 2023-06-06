import inspect
import random
from threading import Lock
from functools import wraps
from typing import List, Optional, Union, Dict, Set, Tuple, Any

class CommsMultiton(type):
    _instances: Dict[str, "Channel"] = {}
    _lock: Lock = Lock()

    def __call__(cls, __my_name="comm"):
        with cls._lock:
            if __my_name not in cls._instances:
                instance = super().__call__(__my_name)
                cls._instances[__my_name] = instance
        return cls._instances[__my_name]


class Channel(metaclass=CommsMultiton):
    def __init__(self, env_name) -> None:
        self._my_name = env_name
        self.agent_list = {}
        self._agents = {}
        self._name = f"{type(self).__name__}:{self._my_name}"
        #Agent.send_msg = self.function_call(Agent.send_msg)
        
    def print(self,*args, **kwargs):
        return print(f"{self._name}>",*args,**kwargs)
    
    def add_agents(self, agents):
        try:
            for agent in agents:
                self._add_agent(agent)
            #self.send_agents_list()
        except TypeError:
            self._add_agent(agents)

    '''
    self.print(f"Adding {data_type}") if self.full_log else ...
        for key, value in data_type.items():
            if key in type_base and isinstance(value, dict):
                for inner_key, inner_value in value.items():
                    if inner_key in type_base[key] and isinstance(inner_value, set):
                        type_base[key][inner_key].update(inner_value)
                    else:
                        type_base[key][inner_key] = inner_value 
            else:
                type_base[key] = value
    '''
    def _add_agent(self, agent):
        if type(agent).__name__ in self.agent_list:
            if agent.my_name[0] in self.agent_list[type(agent).__name__]:
                self.agent_list[type(agent).__name__][agent.my_name[0]].update({agent.my_name})
                self._agents[agent.my_name] = agent
            else:
                self.agent_list[type(agent).__name__].update({agent.my_name[0] : {agent.my_name}})
                self._agents[agent.my_name] = agent
        else:
            self.agent_list[type(agent).__name__] = {agent.my_name[0] : {agent.my_name}}
            self._agents[agent.my_name] = agent
        
        self.print(f'> Connecting agent {type(agent).__name__}:{agent.my_name} to channel')

            
    def _rm_agents(self, agents):
        try:
            for agent in agents:
                self._rm_agent(agent)
        except TypeError:
            self._rm_agent(agents)
        #self.send_agents_list()

    def _rm_agent(self, agent):
        if agent.my_name in self._agents:
            del self._agents[agent.my_name]
            del self.agent_list[agent.my_name]
        self.print(
            f"> Desconnecting agent {type(agent).__name__}:{agent.my_name} from channel"
        )

    def _send(self, sender, target, act, msg):            
        try:
            self._agents[target].recieve_msg(sender,act,msg)
        except KeyError:
            self.print(f"> Agent {target} not connected")

    def function_call(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if args[-1] == self._my_name or args[-1] == 'broadcast':
                arg_values = inspect.getcallargs(func, *args, **kwargs)
                msg = {}
                for key,value in arg_values.items():
                    msg[key] = value 
                try:
                    self.print(f"> Sending a message {msg['self'].my_name}>{msg['target']}")
                    self._agents[msg['target']].recieve_msg(msg['self']\
                                    .my_name,msg['act'],msg['msg'])
                except(KeyError):
                    self.print(f"> Agent {msg['target']} not connected")

                return func(*args, **kwargs)
            
        return wrapper

        return wrapper
