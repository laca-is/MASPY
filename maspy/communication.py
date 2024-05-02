from threading import Lock
from collections.abc import Iterable
from typing import Dict, TypeVar

Agt_name = TypeVar('Agt_name')
Agt_cls = TypeVar('Agt_cls')
Agt_inst = TypeVar('Agt_inst')
Agt_fullname = TypeVar('Agt_fullname')

tell= TypeVar('tell')
untell = TypeVar('untell')
tellHow = TypeVar('tellHow')
untellHow = TypeVar('untellHow')
achieve = TypeVar('achieve')
unachieve = TypeVar('unachieve')
askOne = TypeVar('askOne')
askAll = TypeVar('askAll')
askHow = TypeVar('askHow')

broadcast = TypeVar('broadcast')

class CommsMultiton(type):
    _instances: Dict[str, "Channel"] = {}
    _lock: Lock = Lock()

    def __call__(cls, __my_name="default"):
        with cls._lock:
            if __my_name not in cls._instances:
                instance = super().__call__(__my_name)
                cls._instances[__my_name] = instance
        return cls._instances[__my_name]


class Channel(metaclass=CommsMultiton):
    def __init__(self, comm_name):
        self.full_log = False
        
        from maspy.admin import Admin
        self._my_name = comm_name
        Admin()._add_channel(self)
        
        from maspy.agent import Belief, Goal, Ask, Plan
        self.data_types = {Belief,Goal,Ask,Plan}
        self._my_name = comm_name
        self.agent_list: Dict[Agt_cls, Dict[Agt_name, Agt_fullname]] = {}
        self._agents: Dict[Agt_fullname, Agt_inst] = {}
        self._name = f"{type(self).__name__}:{self._my_name}"
        
    def print(self,*args, **kwargs):
        return print(f"{self._name}>",*args,**kwargs)
    
    def add_agents(self, agents):
        try:
            for agent in agents:
                self._add_agent(agent)
        except TypeError:
            self._add_agent(agents)

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
        
        self.print(f'Connecting agent {type(agent).__name__}:{agent.my_name}') if self.full_log else ...

            
    def _rm_agents(self, agents):
        try:
            for agent in agents:
                self._rm_agent(agent)
        except TypeError:
            self._rm_agent(agents)

    def _rm_agent(self, agent):
        if agent.my_name in self._agents:
            del self._agents[agent.my_name]
            del self.agent_list[type(agent).__name__][agent.my_name[0]]
        self.print(
            f"Desconnecting agent {type(agent).__name__}:{agent.my_name}"
        ) if self.full_log else ...

    def _send(self, sender, target, act, message):  
        if type(act) == TypeVar: act = act.__name__ 
        
        messages = []
        if type(message) == Iterable:
            for m in message:
                messages.append(self.parse_sent_msg(sender,act,m))
        else:
            messages.append(self.parse_sent_msg(sender,act,message))

        for msg in messages:
            if type(target) == Iterable:
                for trgt in target:
                    self._sending(sender,trgt,act,msg)
            elif target == broadcast:
                for agent_name in self._agents.keys():
                    self._sending(sender,agent_name,act,msg)
            else:
                self._sending(sender,target,act,msg)
    
    def _sending(self, sender, target, act, msg):
        self.print(f"{sender} sending {act}:{msg} to {target}") if self.full_log else ...        
    
        try:         
            self._agents[target].save_msg(act,msg)
        except KeyError:
            self.print(f"Agent {target} not connected")
    
    def parse_sent_msg(self,sender, act, msg):
        from maspy.agent import Belief, Goal, Ask, Plan
        if type(msg) in {Belief, Goal} and msg is not None:
            msg = msg.update(source=sender)
        if act in {"askOne","askAll","askHow"}:
            msg = Ask(msg, source=sender)
        return msg