from threading import Lock
from typing import Dict, Set, List, TYPE_CHECKING, Union, Optional, Any, Sequence, Callable
from dataclasses import dataclass, field
from collections.abc import Iterable
from maspy.utils import manual_deepcopy, merge_dicts, freeze_obj, unfreeze_obj, bcolors
from logging import getLogger
from maspy.learning.modelling import Group
from itertools import product, combinations, permutations
from threading import Event
import inspect

if TYPE_CHECKING:
    from maspy.agent import Agent

DEFAULT_GROUP = "none"

@dataclass
class Percept:
    """Represents a Observable (Perceivable) component of the Environment"""
    name: str = field(default_factory=str)
    _values: tuple | Any = field(default_factory=tuple)
    _group: str | Group = DEFAULT_GROUP
    adds_event: bool = True
    source: str = field(default_factory=str)
    v_len: int = 0
    
    @property
    def values(self):
        if len(self._values) > 1:
            return self._values
        elif len(self._values) == 1:
            return self._values[0]
        else:
            return tuple()
    
    @property
    def values_len(self):
        return len(self._values)

    @property
    def info(self) -> dict:
        return {
            "data_type": "Percept",
            "name": self.name,
            "values": self._values,
            "group": self.group,
            "source": self.source
        }

    @property
    def group(self):
        if isinstance(self._group, str):
            return self._group
        elif isinstance(self._group, Group):
            return self._group.name
        else:
            print(f"GROUP TYPE ERROR {type(self._group)}:{self._group}")
            return ""
    
    def __post_init__(self):
        object.__setattr__(self, "v_len", len(self._values) if isinstance(self._values, tuple) else 1)
        match self._values:
            case list() | dict() | str():
                object.__setattr__(self, "_values", tuple([self._values]))
            case tuple():
                pass
            case Iterable():
                object.__setattr__(self, "_values", tuple(self._values))
            case _:
                object.__setattr__(self, "_values", tuple([self._values]))
    
    def change(self, name: str|None = None, values: Any|None = None, group: str|None = None, adds_event: bool|None = None, source: str|None = None) -> None:
        frame = inspect.currentframe()
        caller_frame = frame.f_back if frame else None
        assert caller_frame
        caller_locals = caller_frame.f_locals
        caller_instance = caller_locals.get('self', None) if caller_locals else None
        caller_method = caller_frame.f_code.co_name
        args, _, _, vls = inspect.getargvalues(caller_frame)
        args_s = ", ".join(f'{arg}={vls[arg]}' for arg in args if arg != "self")
        if isinstance(caller_instance, Environment):
            old_percept = self.info
            old_str = f'{self}'
            self.name = name if name is not None else self.name
            self._values = values if values is not None else self._values
            self._group = group if group is not None else self.group
            self.source = source if source is not None else self.source
            self.adds_event = adds_event if adds_event is not None else self.adds_event
            
            extras = caller_instance.env_info
            extras.update({"Old Percept": old_percept, "New Percept": self.info, "action_name":caller_method})
            extras.update({"action_args": dict(vls)})
            #if caller_instance.show_exec:
            caller_instance.print(f'Changing percept: {old_str} to {self}')
            caller_instance.logger.info('Changing Percept', extra=extras)
            #caller_instance._notify_change()
        else:
            print(f"{type(caller_instance)}, not an Environment instance, trying to change {self}")

    def __hash__(self) -> int:
        values_hashable = []
        for value in self._values:
            arg_dict = type(value).__dict__
            if arg_dict.get("__hash__"):
                values_hashable.append(value)
            elif isinstance(value, (List, Dict, Set)):
                values_hashable.append(repr(value))
            else:
                raise TypeError(f"Unhashable type: {type(value)}")
        values_tuple: tuple = tuple(values_hashable)

        return hash((self.name, values_tuple, self.group))

    def __str__(self) -> str:
        if self.group == DEFAULT_GROUP:
            s = f"Percept{self.name,self._values,self.source}"
        else:
            s = f"Percept{self.name,self._values,self.group,self.source}"
        return s.replace("typing.Any","Any")
    
    def __repr__(self):
        return self.__str__()

@dataclass
class State:
    """Represents a State of the Environment for Modelling"""
    _state_type: Group = Group.listed
    name: str = field(default_factory=str)
    data: Sequence[Any] = field(default_factory=tuple)
    
    @property
    def state_type(self) -> str:
        if isinstance(self._state_type, str):
            return self._state_type
        elif isinstance(self._state_type, Group):
            return self._state_type.name
        else:
            print(f"STATE GROUP TYPE ERROR {type(self._state_type)}:{self._state_type}")
            return ""
    
@dataclass
class Action:
    """Represents an Action of the Environment for Modelling"""
    _act_type: Group
    data: Sequence[Any]
    transition: Callable
    func: Callable = lambda _: {} 
    
    def __post_init__(self) -> None:
        match self.data:
            case int() | str():
                object.__setattr__(self, "data", [self.data])
    
    @property
    def act_type(self) -> str:
        if isinstance(self._act_type, str):
            return self._act_type
        elif isinstance(self._act_type, Group):
            return self._act_type.name
        else:
            print(f"ACTION GROUP TYPE ERROR {type(self._act_type)}:{self._act_type}")
            return ""

def action(act_type: Group, data: Sequence[Any], transition: Callable) -> Callable:
    """ 
    The Decorator for Actions inteded to be learned upon.

    Parameters
    ----------
        act_type : Group
            The type of the Action
        data : Sequence[Any]
            The data of the Action
        transition : Callable
            The transition function of the Action   
        
    Returns
    -------
        Callable
            The decorated function
    """
    class decorator:
        def __init__(self,func):
            self.func = func
                
        def __set_name__(self, instance: Environment, name: str):
            assert isinstance(act_type, Group), f"Expected Group, got {type(act_type)}"
            if act_type != Group.listed:
                assert isinstance(data, Sequence) and not isinstance(data, str), f"Expected Sequence of values (list/tuple), got {type(data)}"
            try:
                instance._actions += [Action(act_type,data,transition,self.func)]
            except AttributeError:
                instance._actions = [Action(act_type,data,transition,self.func)]
                
        def __get__(self, obj, objtype = None):
            return self.func.__get__(obj, objtype)
        
    return decorator

class EnvironmentMultiton(type):
    _instances: Dict[str, "Environment"] = {}
    _lock: Lock = Lock()

    @classmethod
    def get_instance(cls, env_name: str) -> Optional["Environment"]:
        if env_name in cls._instances:
            return cls._instances[env_name]
        return None

    def __call__(cls, *args: Any, **kwargs: Any):
        env_name = args[0] if args else kwargs.get("env_name")
        if not isinstance(env_name, str): env_name = type(cls).__name__
        with cls._lock:
            if env_name not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[env_name] = instance
        
        return cls._instances[env_name]

class Environment(metaclass=EnvironmentMultiton):
    """Used for the modelling of the Environments in which Agents act and perceive.
    
    Each instance with a unique name is a distinct Environment.
    """
    def __init__(self, 
                env_name: Optional[str]=None,
                *,
                percepts: Optional[Iterable[Percept]]=None,
                show_exec: bool=False,
                logging: bool=False
                ):
        self.my_name = env_name if env_name else type(self).__name__
        self.show_exec = show_exec
        self.printing = True
        self.lock = Lock()
        self.tcolor = ""
        
        from maspy.admin import Admin
        Admin()._add_environment(self)
        self.print_queue = Admin().print_queue
        self.sys_time = Admin().sys_time
        self.logger = getLogger("maspy")
        self.last_msg = ""
        self.agent_list: Dict[str, Dict[str, Set[str]]] = dict()
        self._agents: Dict[str, 'Agent'] = dict()
        
        self._name = f"Environment:{self.my_name}"
        self.perceiving_agents: int = 0
        self._percepts: Dict[str, Dict[str, Set[Percept]]] = dict()
        self.percept_list: List[Percept] = []
        
        self.possible_starts: dict | str = dict()
        self._actions: List[Action]
        self._states: Dict[str, List[State]] = dict()
        self._state_percepts: Dict[str, Percept] = dict()
        try:    
            if not self._actions:
                self._actions = []
        except AttributeError:
            self._actions = []
        
        if percepts:
            self.logger.debug(f"Adding Initial Percepts: {percepts}", extra=self.env_info)
            self.create(percepts)    
        
        self.print(f"Environment {self.my_name} created \n{percepts, show_exec, logging}")
        self.logger.info(f"Environment {self.my_name} created", extra=self.env_info)
    
    def __init_subclass__(cls):
        old_init = cls.__init__

        def new_init(self, *args, **kwargs):
            old_init(self, *args, **kwargs)
            if hasattr(self, "_post_init"):
                self._post_init()

        cls.__init__ = new_init

    def _post_init(self):
        if self._states and self.possible_starts != "off-policy":
            assert isinstance(self.possible_starts, dict), f"possible_starts must be a dict when not off-policy {type(self.possible_starts)}:{self.possible_starts}"
            self.start_states = list(self.possible_starts.values())
            for percept in self._state_percepts.values():
                if percept.name not in self.possible_starts:
                    states = self._states[percept.name][0].data
                    self.start_states.append(states)
                    self.possible_starts[percept.name] = states
            
            normalized = [ 
                [item] if not isinstance(item, list | tuple | set) 
                else list(item) for item in self.start_states
            ]
            
            self.initial_dist = list(product(*normalized))    
            from numpy import random  
            start_state = self.initial_dist[random.randint(0, len(self.initial_dist))] 

            for stt, (name, _) in zip(start_state, self.possible_starts.items()):
                percept = self.get(Percept(name),ck_values=False)
                if isinstance(stt, frozenset):
                    stt = dict(stt)
                percept.change(values=stt)
            #print(f'{self._name} states: {self._states} possible_starts: {self.possible_starts} start_states: {self.start_states} initial_dist: {self.initial_dist}')
    
    def print(self,*args: Any, **kwargs: Any) -> None:
        """Formatted MASPY Print Function"""
        if not self.printing:
            return 
        f_args = "".join(map(str, args))
        f_kwargs = "".join(f"{key}={value}" for key, value in kwargs.items())
        msg = f"{self.tcolor}{self._name}> {f_args}{f_kwargs}{bcolors.ENDCOLOR}"
        self.print_queue.put(msg)
        self.logger.info(msg, extra=self.env_info)
    
    @property
    def get_info(self):
        percepts = self._perception()
        percept_list = []
        for group_keys in percepts.values():
            for percept_set in group_keys.values():
                for percept in percept_set:
                    percept_list.append(percept)
                    
        return {"percepts": percept_list, "connected_agents": list(self._agents.keys()).copy()}
    
    def _perception(self) -> Dict[str, Dict[str, Set[Percept]]]:
        """Returns a copy of the environment's percepts
        
        Returns
        -------
        Dict[str, Dict[str, Set[Percept]]]
            A copy of the environment's percepts
        """
        with self.lock:
            self.perceiving_agents += 1
        percepts = manual_deepcopy(self._percepts)
        with self.lock:
            self.perceiving_agents -= 1
        return percepts

    @property
    def print_percepts(self) -> None:
        """
        Prints all the environment's current percepts
        """
        percepts = ""
        for group_keys in self._percepts.values():
            for percept_set in group_keys.values():
                for percept in percept_set:
                    percepts += f"\n\t{percept}"
        self.print(f"{percepts}\r")
        
    @property
    def print_actions(self) -> None:
        """ 
        Prints all the environment's current actions
        """
        actions = ""
        for action in self._actions:
            actions += f"{action}\n"
        print(f"{actions}\r")
    
    @property
    def env_info(self) -> dict:
        """ 
        Returns information about the environment used for logging
        
        Returns
        -------
        dict
            The Information about the environment
        """
        return {
            "class_name": "Environment",
            "my_name": self.my_name,
            "percepts": [prcpt.info for prcpt in self.percept_list],
            "connected_agents": list(self._agents.keys())
        }
        
    def _check_caller(self) -> tuple[str, str]:
        """ 
        Returns the caller's method name and arguments
        
        Returns
        -------
        tuple[str, str]
            The caller's method name and arguments
        """
        frame = inspect.currentframe()
        assert frame and frame.f_back
        caller_frame = frame.f_back.f_back 
        assert caller_frame
        caller_method = caller_frame.f_code.co_name
        args, a, b, values = inspect.getargvalues(caller_frame)
        #print(args,a,b,values)
        args_s = ", ".join(f'{arg}={values[arg]}' for arg in args if arg != "self")
        return caller_method, args_s
    
    def add_agents(self, agents: Union[List['Agent'],'Agent']) -> None:
        """ Adding agents to the environment
        
        Parameters
        ----------
        agents : Iterable[Agent] | Agent
            The agents to be added
        """
        if isinstance(agents, list):
            for agent in agents:
                self._add_agent(agent)
        else:
            self._add_agent(agents)
    
    def _add_agent(self, agent: 'Agent') -> None:
        """ Actually adding an agent to the environment
        
        Parameters
        ----------
        agent : Agent
            The agent to be added
        """
        assert isinstance(agent.tuple_name, tuple)
        ag_name = f'{agent.tuple_name[0]}_{str(agent.tuple_name[1])}'
        if type(agent).__name__ in self.agent_list:
            if agent.tuple_name[0] in self.agent_list[type(agent).__name__]:
                self.agent_list[type(agent).__name__][agent.tuple_name[0]].update({ag_name})
            else:
                self.agent_list[type(agent).__name__].update({agent.tuple_name[0] : {ag_name}})
        else:
            self.agent_list[type(agent).__name__] = {agent.tuple_name[0] : {ag_name}}
            
        self._agents[ag_name] = agent
        
        if hasattr(self, 'on_connect'):
            getattr(self, 'on_connect')(ag_name)
        if self.show_exec:
            self.print(f'Connecting Agent {type(agent).__name__}:{"_".join(str(x) for x in agent.tuple_name)}')
        self.logger.info(f'Connecting Agent {type(agent).__name__}:{"_".join(str(x) for x in agent.tuple_name)}', extra=self.env_info)
    
    def rm_agents(self, agents: Union[Iterable['Agent'], 'Agent']) -> None:
        """ 
        Removes a agent or a iterable data of agents from the environment

        Parameters
        ----------
            agents : Iterable[Agent] | Agent
                The agent(s) to be removed
        """
        if isinstance(agents, list):
            for agent in agents:
                self._rm_agent(agent)
        else:
            from maspy.agent import Agent
            assert isinstance(agents, Agent)
            self._rm_agent(agents)

    def _rm_agent(self, agent: 'Agent') -> None:
        """ 
        Actually removing each agent from the environment

        Parameters
        ----------
            agent : Agent
                The agent to be removed
        """
        ag_name = f'{agent.tuple_name[0]}_{str(agent.tuple_name[1])}'
        if ag_name in self._agents:
            assert isinstance(agent.tuple_name, tuple)
            del self._agents[ag_name]
            self.agent_list[type(agent).__name__][agent.tuple_name[0]].remove(ag_name)
        if self.show_exec:
            self.print(f'Disconnecting Agent {type(agent).__name__}:{"_".join(str(x) for x in agent.tuple_name)}')
        self.logger.info(f'Disconnecting Agent {type(agent).__name__}:{"_".join(str(x) for x in agent.tuple_name)}', extra=self.env_info)
    
    def _notify_change(self):
        for agent in self._agents.values():
            with agent.env_lock:
                agent._env_changed[self.my_name] = True
                agent._env_changed_count += 1
    
    def create(self, percept: Iterable[Percept] | Percept):
        """
        Creates one or multiple new percept(s) on the environment

        Parameters
        ----------
            percept : List of Percepts or Percept 
                The one or multiple Percepts to be added to the environment.
        """
        percept_dict = self._clean(percept)
        with self.lock:
            aux_percepts = manual_deepcopy(self._percepts)
        merge_dicts(percept_dict, aux_percepts)
        with self.lock:
            self._percepts = aux_percepts
        
        if isinstance(percept, Iterable):
            for prcpt in percept:
                self.percept_list.append(prcpt)
                if prcpt.group in Group:
                    self._add_state(prcpt)
        else:
            self.percept_list.append(percept)
            if percept.group in Group._member_names_:
                self._add_state(percept)    
        
        action, agt = self._check_caller()
        extras = self.env_info
        extras.update({"Create Percept(s)": percept, "action":action, "agent": agt})
        #if self.show_exec:
        self.print(f'Creating {percept}')
        self.logger.info('Creating Percept', extra=extras)
        #self._notify_change()
        
    def _add_state(self, percept: Percept) -> None:
        """
        Adds a new state to the environment
        
        Parameters
        ----------
            percept : Percept
                The percept to be added as a State
        """
        self._state_percepts[percept.name] = percept
        match percept.group:
            case "listed":
                states = State(Group.listed, percept.name, percept.values)
            case "combination":
                if percept.v_len == 2 and isinstance(percept.values[0], Sequence) and isinstance(percept.values[1], int):
                    comb = list(combinations(percept.values[0], percept.values[1]))
                else:
                    comb = []
                    for i in range(1, len(percept.values) + 1):
                        comb.extend(combinations(percept.values, i))
                states = State(Group.combination, percept.name, comb)
            case "permutation":
                perm: list = []
                for i in range(1, len(percept.values) + 1):
                    perm.extend(permutations(percept.values, i))
                states = State(Group.permutation, percept.name, perm)
            case "cartesian":
                ranges: list = []
                for arg in percept._values:
                    if isinstance(arg, str):
                        ranges.append([arg])
                    elif isinstance(arg, Sequence):
                        ranges.append(arg)
                    elif isinstance(arg, int):
                        ranges.append(range(arg))
                    else:
                        self.logger.warning(f'{arg}:{type(arg)} is not a valid type',extra=self.env_info)
                cart = list(product(*ranges))
                states = State(Group.cartesian, percept.name, cart)
        
        if percept.name in self._states:
            self._states[percept.name].append(states)
        else: 
            self._states[percept.name] = [states]
               
    def get(self, percept:Percept, all: bool=False, ck_group: bool=False, ck_values: bool=True) -> List[Percept] | Percept | None:
        """
        Retrieves from the environment one or multiple percepts that match the given parameters

        Parameters
        ----------
            percept: Percept
                The percept to search for.
            all (bool, optional) 
                If True, returns all matching percepts. Defaults to False.
            ck_group (bool, optional)
                Whether to check the group of the percept. Defaults to False.
            ck_values (bool, optional)
                Whether to check the arguments of the percept. Defaults to True.

        Returns
        -------
            List ofPercept] | Percept:  
                The retrieved percept(s).
            None: If no matches are found, returns None.
        """
        found_data = []
        ## self.logger.debug(f'Getting percept like: {percept}', extra=self.env_info)
        for group_keys in self._percepts.values():
            for percept_set in group_keys.values():
                for prcpt in percept_set:
                    if self._compare_data(prcpt,percept,ck_group,ck_values):
                        if not all:
                            return prcpt
                        else:
                            found_data.append(prcpt)
        if found_data:
            return found_data  
        else:
            current_frame = inspect.currentframe()
            assert current_frame is not None
            caller_frame = current_frame.f_back
            assert caller_frame is not None
            caller_function_name = caller_frame.f_code.co_name
            if caller_function_name in {'change','has'}:
                return None
            self.print(f'Does not contain Percept like {percept}. Searched during {caller_function_name}()')
            return None
    
    def has(self, percept: Percept, ck_group: bool=False, ck_values: bool=True) -> bool:
        """ 
        Checks if the environment contains a percept that matches the given parameters
        
        Parameters
        ----------
            percept: Percept
                The percept to search for.
            ck_group (bool, optional)
                Whether to check the group of the percept. Defaults to False.
            ck_values (bool, optional)
                Whether to check the arguments of the percept. Defaults to True.

        Returns
        -------
            bool: True if the environment contains a percept that matches the given parameters, False otherwise
        """
        return self.get(percept, all=False, ck_group=ck_group, ck_values=ck_values) is not None
    
    def _compare_data(self, data1: Percept, data2: Percept, ck_group:bool,ck_args:bool) -> bool:
        """ 
        Compares two percepts

        Parameters
        ----------
            data1: Percept
                The first percept to compare.
            data2: Percept
                The second percept to compare.
            ck_group (bool, optional)
                Whether to check the group of the percept. Defaults to False.
            ck_args (bool, optional)
                Whether to check the arguments of the percept. Defaults to True.

        Returns
        -------
            bool: True if the percepts are compatible, False otherwise
        """
        self.print(f"Comparing: \n\t{data1} and {data2}") if self.show_exec else ...
        if ck_group and data1.group != data2.group:
            self.print("Failed at group") if self.show_exec else ...
            return False
        if data1.name != data2.name:
            self.print("Failed at key") if self.show_exec else ...
            return False
        if not ck_args:
            return True
        if data1.v_len != data2.v_len:
            self.print("Failed at args_len") if self.show_exec else ...
            return False
        for arg1,arg2 in zip(data1._values,data2._values):
            if arg1 is Any or arg2 is Any or arg1 == arg2:
                continue
            else:
                self.print(f"Failed at values {arg1} x {arg2}") if self.show_exec else ...
                return False
        else:
            self.print("Data is Compatible") if self.show_exec else ...
            return True
    
    def change(self, percept: Percept, name: str|None = None, values: Any|None = None, group: str|None = None, adds_event: bool|None = None, source: str|None = None) -> None:
        percept.change(name=name, values=values, group=group, adds_event=adds_event, source=source)
         
    def delete(self, percept: Iterable[Percept] | Percept) -> None:
        """
        Deletes one or multiple percepts from the environment

        Parameters
        ----------
            percept : List of Percepts or Percept)
                The one or multiple Percepts to be deleted from the environment
        """
        self.print(self._check_caller())
        assert percept is not None, f'Percept given to be deleted is None'
        try:
            if isinstance(percept, Iterable):
                for prcpt in percept:
                    self.percept_list.remove(prcpt)
                    self._percepts[prcpt.group][prcpt.name].remove(prcpt)
            else:
                self.percept_list.remove(percept)
                self._percepts[percept.group][percept.name].remove(percept)
            action, agt = self._check_caller()
            extra = self.env_info
            extra.update({"percept(s)": str(percept), "action":action, "agent": agt})
            if self.show_exec:
                self.print(f'Deleting {percept}')
            self.logger.info(f'Deleting Percept', extra=extra)
        except KeyError:
            self.logger.warning(f'{percept} doesnt exist, cannot be deleted',extra=self.env_info)
        #self._notify_change()
              
    def _clean(self, percept_data: Iterable[Percept] | Percept) -> Dict[str, Dict[str, set]]:
        """
        Cleans the percept data by adding the source of the percept

        Parameters
        ----------
            percept_data : Iterable[Percept] | Percept
                The percept data to be cleaned

        Returns
        -------
            Dict[str, Dict[str, set]]
                The cleaned percept data
        """
        match percept_data:
            case None:
                return dict()
            case Percept():
                object.__setattr__(percept_data, "source", self.my_name)
                return {percept_data.group : {percept_data.name: {percept_data}}}
            case Iterable():
                percept_dict: Dict[str, Dict[str, set]] = dict()
                for prc_dt in percept_data:
                    object.__setattr__(prc_dt, "source", self.my_name)
                    if prc_dt.name in percept_dict[prc_dt.group]:
                        percept_dict[prc_dt.group][prc_dt.name].add(prc_dt)
                    else:
                        percept_dict[prc_dt.group].update({prc_dt.name: {prc_dt}})

                return percept_dict
            case _:
                raise TypeError(
                    f"Expected data type to have be Iterable[Percept] | Percept, recieved {type(percept_data).__name__}"
                ) 

