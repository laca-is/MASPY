from threading import Lock
from typing import Dict, Set, List, TYPE_CHECKING, Union, Optional, Any, Sequence, Callable
from dataclasses import dataclass, field
from collections.abc import Iterable
from maspy.utils import manual_deepcopy, merge_dicts

if TYPE_CHECKING:
    from maspy.agent import Agent

DEFAULT_GROUP = "none"

@dataclass
class Percept:
    key: str = field(default_factory=str)
    _args: tuple | Any = field(default_factory=tuple)
    group: str = DEFAULT_GROUP
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
        for arg in self._args:
            arg_dict = type(arg).__dict__
            if arg_dict.get("__hash__"):
                args_hashable.append(arg)
            elif isinstance(arg, (List, Dict, Set)):
                args_hashable.append(repr(arg))
            else:
                raise TypeError(f"Unhashable type: {type(arg)}")
        args_tuple: tuple = tuple(args_hashable)

        return hash((self.key, args_tuple, self.group))

    def __str__(self) -> str:
        if self.group == DEFAULT_GROUP:
            return f"Percept{self.key,self._args}"
        else:
            return f"Percept{self.key,self._args,self.group}"
    
    def __repr__(self):
        return self.__str__()
    
@dataclass
class Action:
    type: str
    data: Sequence[Any]
    func: Callable = lambda _: {} 

def action(type: str, data: Sequence[Any]):
    class decorator:
        def __init__(self,func):
            self.func = func
                
        def __set_name__(self, instance: Environment, name: str):
            assert isinstance(type, str)
            assert isinstance(data, Sequence) and not isinstance(data, str)
            try:
                instance._actions += [Action(type,data,self.func)]
            except AttributeError:
                instance._actions = [Action(type,data,self.func)]
    return decorator

class EnvironmentMultiton(type):
    _instances: Dict[str, "Environment"] = {}
    _lock: Lock = Lock()

    def __call__(cls, env_name=None,full_log=False):
        with cls._lock:
            _my_name = env_name if env_name else str(cls.__name__)
            if _my_name not in cls._instances:
                vars = []
                if env_name: 
                    vars.append(env_name)
                if full_log: 
                    vars.append(full_log)
                instance = super().__call__(*vars)
                cls._instances[_my_name] = instance
        return cls._instances[_my_name]

class Environment(metaclass=EnvironmentMultiton):
    def __init__(self, env_name: Optional[str]=None,full_log: bool=False):
        self._my_name = env_name if env_name else type(self).__name__
        self.show_exec = full_log
        self.lock = Lock()
        
        from maspy.admin import Admin
        Admin()._add_environment(self)
        #  Dict[Agt_cls, Dict[Agt_name, Set[Agt_fullname]]]
        self.agent_list: Dict[str, Dict[str, Set[tuple]]] = dict()
        #  Dict[Agt_fullname, Agt_inst]
        self._agents: Dict[str, 'Agent'] = dict()
        
        self._name = f"Environment:{self._my_name}"
        #  Dict[env_name, Dict[percept_key, Set[Percept]]]
        self._percepts: Dict[str, Dict[str, Set[Percept]]] = dict()
        
        self._actions: List[Action]
        try:    
            if not self._actions:
                self._actions = []
        except AttributeError:
            self._actions = []
    
    def print(self,*args, **kwargs):
        return print(f"{self._name}>",*args,**kwargs)
    
    @property
    def get_info(self):
        percepts = self.perception()
        percept_list = []
        for group_keys in percepts.values():
            for percept_set in group_keys.values():
                for percept in percept_set:
                    percept_list.append(percept)
                    
        return {"percepts": percept_list, "connected_agents": list(self._agents.keys()).copy()}
    
    def perception(self) -> Dict[str, Dict[str, Set[Percept]]]:
        return manual_deepcopy(self._percepts)

    @property
    def print_percepts(self):
        percepts = ""
        for group_keys in self._percepts.values():
            for percept_set in group_keys.values():
                for percept in percept_set:
                    percepts += f"{percept}\n"
        print(f"{percepts}\r")
        
    @property
    def print_actions(self):
        actions = ""
        for action in self._actions:
            actions += f"{action}\n"
        print(f"{actions}\r")
        
    def add_agents(self, agents: Union[List['Agent'],'Agent']):
        if isinstance(agents, list):
            for agent in agents:
                self._add_agent(agent)
        else:
            self._add_agent(agents)
    
    def _add_agent(self, agent: 'Agent'):
        assert isinstance(agent.my_name, tuple)
        if type(agent).__name__ in self.agent_list:
            if agent.my_name[0] in self.agent_list[type(agent).__name__]:
                self.agent_list[type(agent).__name__][agent.my_name[0]].update({agent.my_name})
            else:
                self.agent_list[type(agent).__name__].update({agent.my_name[0] : {agent.my_name}})
        else:
            self.agent_list[type(agent).__name__] = {agent.my_name[0] : {agent.my_name}}
            
        self._agents[agent.str_name] = agent
        self.print(f'Connecting agent {type(agent).__name__}:{agent.my_name}') if self.show_exec else ...
    
    def _rm_agents(
        self, agents: Union[Iterable['Agent'], 'Agent']
    ) -> None:
        if isinstance(agents, list):
            for agent in agents:
                self._rm_agent(agent)
        else:
            from maspy.agent import Agent
            assert isinstance(agents, Agent)
            self._rm_agent(agents)

    def _rm_agent(self, agent: 'Agent'):
        if agent.str_name in self._agents:
            assert isinstance(agent.my_name, tuple)
            #self.print(f"Removing agent {agent.str_name} from {self._agents.keys()}")
            del self._agents[agent.str_name]
            #self.print(f"new list: {self._agents.keys()}")
            self.agent_list[type(agent).__name__][agent.my_name[0]].remove(agent.my_name)
        self.print(
            f"Disconnecting agent {type(agent).__name__}:{agent.my_name}"
        ) if self.show_exec else ...
    
    def create(self, percept: List[Percept] | Percept):
        with self.lock:
            percept_dict = self._clean(percept)
            aux_percepts = manual_deepcopy(self._percepts)
            merge_dicts(percept_dict, aux_percepts)
            self._percepts = aux_percepts
            self.print(f"Creating {percept}") if self.show_exec else ...

    def get(self, percept:Percept, all=False, ck_group=False, ck_args=True) -> List[Percept] | Percept | None:
        found_data = []
        self.print(f"Looking for percept like: {percept}") if self.show_exec else ...
        for group_keys in self._percepts.values():
            for percept_set in group_keys.values():
                for prcpt in percept_set:
                    if self._compare_data(prcpt,percept,ck_group,ck_args):
                        if not all:
                            return prcpt
                        else:
                            found_data.append(prcpt)
                            
        return found_data if found_data else None
                    
    def _compare_data(self, data1: Percept, data2: Percept, ck_group:bool,ck_args:bool) -> bool:
        self.print(f"Comparing: \n\t{data1} and {data2}") if self.show_exec else ...
        if ck_group and data1.group != data2.group:
            self.print("Failed at group") if self.show_exec else ...
            return False
        if data1.key != data2.key:
            self.print("Failed at key") if self.show_exec else ...
            return False
        if not ck_args:
            return True
        if data1.args_len != data2.args_len:
            self.print("Failed at args_len") if self.show_exec else ...
            return False
        for arg1,arg2 in zip(data1._args,data2._args):
            if isinstance(arg1,str) and (arg1[0].isupper()):
                continue
            elif isinstance(arg2,str) and (arg2[0].isupper()):
                continue
            elif arg1 == arg2:
                continue
            else:
                self.print(f"Failed at args {arg1} x {arg2}") if self.show_exec else ...
                return False
        else:
            self.print("Data is Compatible") if self.show_exec else ...
            return True
    
    def change(self, old_percept:Percept, new_args:tuple | Any):
        if type(new_args) is not tuple: 
            new_args = (new_args,) 
        if old_percept.args_len > 0:
            percept = self.get(old_percept)
        else:
            percept = self.get(old_percept,ck_args=False)
        with self.lock:
            if isinstance(percept, Percept):
                percept._args = new_args
            
    def _percept_exists(self, key, args, group=DEFAULT_GROUP) -> bool:
        if type(args) is not tuple: 
            args = (args,)
        return Percept(key,args,group) in self._percepts[group][key]

    def delete(self, percept: List[Percept] | Percept):
        try:
            if isinstance(percept, list):
                for prcpt in percept:
                    self._percepts[prcpt.group][prcpt.key].remove(prcpt)
            else:
                self._percepts[self._my_name][percept.key].remove(percept)
        except KeyError:
            self.print(f'Percept {percept} couldnt be deleted')
              
    def _clean(self, percept_data: Iterable[Percept] | Percept) -> Dict:
        match percept_data:
            case None:
                return dict()
            case Percept():
                return {self._my_name : {percept_data.key: {percept_data}}}
            case Iterable():
                percept_dict: Dict[str, Dict[str, set]] = dict()
                for prc_dt in percept_data:
                    if prc_dt.key in percept_dict[self._my_name]:
                        percept_dict[self._my_name][prc_dt.key].add(prc_dt)
                    else:
                        percept_dict[self._my_name].update({prc_dt.key: {prc_dt}})

                return percept_dict
            case _:
                raise TypeError(
                    f"Expected data type to have be Iterable[Percept] | Percept, recieved {type(percept_data).__name__}"
                ) 

