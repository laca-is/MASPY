from threading import Lock
from typing import Any, Dict, Optional, Set, List
from dataclasses import dataclass, field
from collections.abc import Iterable
from maspy.utils import utils
from maspy.error import InvalidPerceptError

DEFAULT_GROUP = "default"

@dataclass
class Percept:
    key: str
    args: tuple = field(default_factory=tuple)
    group: str = DEFAULT_GROUP # Percept Type (still unsure)
    
    def __hash__(self) -> int:
        args_hashable = []
        for arg in self.args:
            args_hashable.append(arg)

        args_hashable = tuple(args_hashable)

        return hash((self.key, args_hashable, self.group))

class EnvironmentMultiton(type):
    _instances: Dict[str, "Environment"] = {}
    _lock: Lock = Lock()

    def __call__(cls, __my_name="env"):
        with cls._lock:
            if __my_name not in cls._instances:
                instance = super().__call__(__my_name)
                cls._instances[__my_name] = instance
        return cls._instances[__my_name]

class Environment(metaclass=EnvironmentMultiton):
    def __init__(self, env_name: str):
        self.full_log = False
        self._my_name = env_name
        self.agent_list = {}
        self._agents = {}
        self._name = f"Environment:{self._my_name}"
        self._percepts = dict()
    
    def print(self,*args, **kwargs):
        return print(f"{self._name}>",*args,**kwargs)
    
    def perception(self):
        return self._percepts

    @property
    def print_percepts(self):
        percepts = ""
        for group_keys in self._percepts.values():
            for percept_set in group_keys.values():
                for percept in percept_set:
                    percepts += f"{percept}\n"
        print(f"{percepts}\r")
        
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
        
        self.print(f'Connecting agent {type(agent).__name__}:{agent.my_name}')
    
    def create_percept(self, 
            key: str = None, 
            args: Optional[Any] = tuple(), 
            group: Optional[str] = DEFAULT_GROUP,
            percept: Optional[Iterable[Percept] | Percept] = None
        ):
        if key is None and percept is None:
            raise Exception
        
        if key and not percept: 
            if type(args) is not tuple: args = (args,) 
            percept_dict = self._clean(Percept(key, args, group))
        
        if percept: 
            percept_dict = self._clean(percept)
            
        self._percepts = utils.merge_dicts(self._percepts,percept_dict)
        self.print(f"Creating percept {percept_dict}") if self.full_log else ...

    def change_percept(self, key: str, old_args: Any = tuple(), new_args: Any = tuple(), group: Optional[str] = DEFAULT_GROUP):
        if type(old_args) is not tuple: old_args = (old_args,) 
        if type(new_args) is not tuple: new_args = (new_args,) 
        for percept in self._percepts[group][key]:
            if percept == Percept(key,old_args,group): 
                self.print(f"Updating {percept} to", end="")
                percept.args = new_args
                print(f" {percept}") 
                break   
            
    def _percept_exists(self, key, args, group=DEFAULT_GROUP) -> bool:
        if type(args) is not tuple: args = (args,)
        return Percept(key,args,group) in self._percepts[group][key]

    def delete_percept(self, 
            key: str, 
            args: Optional[Any] = tuple(), 
            group: Optional[str] = DEFAULT_GROUP,
        ):
        if type(args) is not tuple: args = (args,) 
        self._percepts[group][key].remove(Percept(key,args,group))
              
    def _clean(
        self, percept_data: Iterable[Percept] | Percept
    ) -> Dict:
        match percept_data:
            case None:
                return dict()
            case Percept():
                return {self._my_name : {percept_data.key: {percept_data}}}
            case Iterable():
                percept_dict = dict()
                for prc_dt in percept_data:
                    if prc_dt.key in percept_dict[self._my_name]:
                        percept_dict[prc_dt.group][prc_dt.key].add(prc_dt)
                    else:
                        percept_dict[prc_dt.group].update({prc_dt.key: {prc_dt}})

                return percept_dict
            case _:
                raise TypeError(
                    f"Expected data type to have be Iterable[Percept] | Percept, recieved {type(percept_data).__name__}"
                ) 

