from threading import Lock
from typing import Any, Dict, Optional, Set, List
from dataclasses import dataclass, field
from collections.abc import Iterable
from maspy.utils import utils
from maspy.error import InvalidPerceptError
from copy import deepcopy

DEFAULT_GROUP = "default"

@dataclass
class Percept:
    key: str
    _args: tuple = field(default_factory=tuple)
    group: str = DEFAULT_GROUP # Percept Type (still unsure)
    adds_event: bool = True
    
    @property
    def args(self):
        if len(self._args) > 1:
            return self._args
        elif len(self._args) == 1:
            return self._args[0]
        else:
            return tuple()
    
    @property
    def args_len(self):
        return len(self._args)
    
    def __post_init__(self):
        match self._args:
            case list() | dict() | str():
                object.__setattr__(self, "_args", tuple([self._args]))
            case tuple():
                pass
            case Iterable():
                object.__setattr__(self, "_args", tuple(self._args))
            case _:
                object.__setattr__(self, "_args", tuple([self._args]))
    
    def __hash__(self) -> int:
        args_hashable = []
        for arg in self.args:
            args_hashable.append(arg)

        args_hashable = tuple(args_hashable)

        return hash((self.key, args_hashable, self.group))

class EnvironmentMultiton(type):
    _instances: Dict[str, "Environment"] = {}
    _lock: Lock = Lock()

    def __call__(cls, env_name=None,full_log=False):
        with cls._lock:
            _my_name = env_name if env_name else str(cls.__name__)
            if _my_name not in cls._instances:
                vars = []
                if env_name: vars.append(env_name)
                if full_log: vars.append(full_log)
                instance = super().__call__(*vars)
                cls._instances[_my_name] = instance
        return cls._instances[_my_name]

class Environment(metaclass=EnvironmentMultiton):
    def __init__(self, env_name=None,full_log=False):
        self._my_name = env_name if env_name else type(self).__name__
        self.full_log = full_log
        
        from maspy.admin import Admin
        Admin()._add_environment(self)
        
        self.agent_list = {}
        self._agents = {}
        self._name = f"Environment:{self._my_name}"
        self._percepts: Dict[str, Dict[str, Set[Percept]]] = dict()
    
    def print(self,*args, **kwargs):
        return print(f"{self._name}>",*args,**kwargs)
    
    def perception(self):
        return deepcopy(self._percepts)

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
        
        self.print(f'Connecting agent {type(agent).__name__}:{agent.my_name}') if self.full_log else ...
    
    def create(self, 
            percept: Iterable[Percept] | Percept
        ):
        percept_dict = self._clean(percept)
            
        utils.merge_dicts(percept_dict, self._percepts)
        self.print(f"Creating {percept}") if self.full_log else ...

    def get(self, percept:Percept, all=False, ck_group=False, ck_args=True) -> List[Percept] | Percept | None:
        found_data = []
        for group, keys in self._percepts.items():
            for key, prcs in keys.items():
                for prcpt in prcs:
                    if self._compare_data(prcpt,percept,ck_group,ck_args):
                        if not all:
                            return prcpt
                        else:
                            found_data.append(prcpt)
                            
        return found_data if found_data else None
                    
    def _compare_data(self, data1: Percept, data2: Percept, ck_group,ck_args):
        #self.print(f"Comparing: \n\t{data1} and {data2}")
        if ck_group and data1.group != data2.group:
        #    self.print("Failed at group")
            return False
        if data1.key != data2.key:
        #    self.print("Failed at key")
            return False
        if not ck_args:
            return True
        if data1.args_len != data2.args_len:
        #    self.print("Failed at args_len")
            return False
        for arg1,arg2 in zip(data1._args,data2._args):
            if isinstance(arg1,str) and (arg1[0].isupper()):
                continue
            elif isinstance(arg2,str) and (arg2[0].isupper()):
                continue
            elif arg1 == arg2:
                continue
            else:
        #        self.print(f"Failed at args {arg1} x {arg2}")
                return False
        else:
        #    self.print("Data is Compatible")
            return True
    
    def change(self, old_percept:Percept, new_args:Percept.args):
        if type(new_args) is not tuple: new_args = (new_args,) 
        old_percept._args = new_args
            
    def _percept_exists(self, key, args, group=DEFAULT_GROUP) -> bool:
        if type(args) is not tuple: args = (args,)
        return Percept(key,args,group) in self._percepts[group][key]

    def delete(self, 
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

