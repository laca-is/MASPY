import threading
import ctypes
from logging import getLogger
from dataclasses import dataclass, field
from maspy.environment import Environment, Percept	
from maspy.communication import Channel, Act, broadcast
from maspy.learning import EnvModel
from maspy.error import (
    InvalidBeliefError,
    InvalidPlanError,
    RunPlanError,
)
from maspy.utils import set_changes, merge_dicts, manual_deepcopy, freeze_obj, unfreeze_obj, bcolors, Condition
from typing import List, Optional, Dict, Set, Any, Union, Type, cast, _SpecialForm, TypeGuard, TypeVar, TYPE_CHECKING
from collections.abc import Iterable, Callable, Sequence, Mapping
from collections import deque
from time import sleep
from enum import Enum
from importlib import import_module
from traceback import extract_tb
from contextlib import nullcontext
from functools import reduce
from operator import and_
import inspect
import sys

from concurrent.futures import ThreadPoolExecutor
import cProfile, pstats, io

Event_Change = Enum('gain | lose | test | success | failure', ['gain', 'lose', 'test', 'success', 'failure']) # type: ignore[misc]

gain = Event_Change.gain
lose = Event_Change.lose
test = Event_Change.test
success = Event_Change.success
failure = Event_Change.failure

Operation = Enum('add | rm', ['add', 'rm']) # type: ignore[misc]

add = Operation.add
rm = Operation.rm

Option = Enum('ignore | focus', ['ignore', 'focus']) # type: ignore[misc]

ignore = Option.ignore
focus = Option.focus

Plan_Type = Enum('default | atomic', ['default','atomic']) # type: ignore[misc]

default = Plan_Type.default
atomic = Plan_Type.atomic

DEFAULT_SOURCE = "self"
DEFAULT_CHANNEL = "default"
PENDING_TIMER = 20
PRINT_CHECKS = False

@dataclass(eq=True, frozen=True)
class Belief(Condition):
    name: str = field(default_factory=str)
    _values: tuple | Any = field(default_factory=tuple)
    source: str = DEFAULT_SOURCE
    adds_event: bool = True
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
            "data_type": "Belief",
            "name": self.name,
            "values": self._values,
            "source": self.source
        }

    def __post_init__(self):
        if not isinstance(self.name, str): raise TypeError(f"Belief.name[ {self.name} ] is not a string")
        if not isinstance(self.source, str): raise TypeError(f"Belief.source[ {self.source} ] is not a string")
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

    def weak_eq(self, other: "Belief"):
        return (
            self.name == other.name
            and len(self._values) == len(other._values)
            and self.source == other.source
        )

    def change(self, key: str|None = None, values: Any|None = None, source: str|None = None, adds_event: bool|None = None) -> None:
        frame = inspect.currentframe()
        caller_frame = frame.f_back if frame else None
        caller_locals = caller_frame.f_locals if caller_frame else None
        caller_instance = caller_locals.get('self', None) if caller_locals else None
        if isinstance(caller_instance, Agent):
            caller_instance.rm(self)
            new_belief = Belief(
                key if key is not None else self.name,
                values if values is not None else self._values,
                source if source is not None else self.source,
                adds_event if adds_event is not None else self.adds_event
            )
            caller_instance.add(new_belief)
        else:
            print(f"{type(caller_instance)}, not an Agent instance, trying to change {self}")

    def __hash__(self) -> int:
        values_hashable = []
        for value in self._values:
            value_dict = type(value).__dict__
            if value_dict.get("__hash__"):
                values_hashable.append(value)
            elif isinstance(value, (List, Dict, Set)):
                values_hashable.append(repr(value))
            else:
                raise TypeError(f"Belief.values[ {type(value)}:{value} ] is not hashable")
        values_tuple = tuple(values_hashable)

        return hash((self.name, values_tuple, self.source))
    
    def __str__(self) -> str:
        s = f'Belief {self.name}({self.values if self.values else ""})[{self.source}]'
        return s.replace("typing.Any","Any")
    
    def __repr__(self):
        return self.__str__()

@dataclass
class Goal(Condition):
    name: str = field(default_factory=str)
    _values: tuple | Any = field(default_factory=tuple)
    source: str = DEFAULT_SOURCE
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
            "data_type": "Goal",
            "name": self.name,
            "values": self._values,
            "source": self.source
        }

    def __post_init__(self):
        if not isinstance(self.name, str): raise TypeError(f"Goal.name[ {self.name} ] is not a string")
        if not isinstance(self.source, str): raise TypeError(f"Goal.source[ {self.source} ] is not a string")
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

    def weak_eq(self, other: "Goal"):
        return (
            self.name == other.name
            and len(self._values) == len(other._values)
            and self.source == other.source
        )

    def change(self, key: str|None = None, values: Any|None = None, source: str|None = None, adds_event: bool|None = None) -> None:
        frame = inspect.currentframe()
        caller_frame = frame.f_back if frame else None
        caller_locals = caller_frame.f_locals if caller_frame else None
        caller_instance = caller_locals.get('self', None) if caller_locals else None
        if isinstance(caller_instance, Agent):
            caller_instance.rm(self)
            new_belief = Belief(
                key if key is not None else self.name,
                values if values is not None else self._values,
                source if source is not None else self.source
            )
            caller_instance.add(new_belief)
        else:
            print(f"{type(caller_instance)}, not an Agent instance, trying to change {self}")
    
    def __hash__(self) -> int:
        values_hashable = []
        for value in self._values:
            value_dict = type(value).__dict__
            if value_dict.get("__hash__"):
                values_hashable.append(value)
            elif isinstance(value, (List, Dict, Set)):
                values_hashable.append(repr(value))
            else:
                raise TypeError(f"Goal.values[ {type(value)}:{value} ] is not hashable")
        values_tuple = tuple(values_hashable)

        return hash((self.name, values_tuple, self.source))
    
    def __str__(self) -> str:
        s = f"Goal {self.name}({self.values if self.values else ''})[{self.source}]"
        return s.replace("typing.Any","Any")
    
    def __repr__(self):
        return self.__str__()
    
@dataclass
class Event:
    """ Events represent a change of the Agent's Information """
    change: Event_Change = field(default_factory=lambda:gain)
    data: Belief | Goal | Percept | None = None
    
    @property
    def info(self) -> dict:
        return {
            "data_type": "Event",
            "change": self.change.name,
            "data": self.data.info if self.data else None
        }
    
    def __str__(self) -> str:
        return f"{self.change.name}:{self.data}"
    
    def __repr__(self):
        return self.__str__()
    
@dataclass
class Plan:
    """ Plans represent how the Agent will respond to an Event in a given Context """
    trigger: Event = field(default_factory=Event)
    context: Optional[Condition] = None
    body: Callable = lambda _: {}
    conditions: tuple[Callable[..., Any], ...] = (lambda _: {},)
    plan_type: Plan_Type = field(default_factory=lambda:default)
    ev_ctrl: threading.Event = threading.Event()
    
    @property
    def info(self) -> dict:
        return {
            "data_type": "Plan",
            "trigger": self.trigger.info,
            "context": self.context,
            "body": self.body.__name__
        }
    
    def __str__(self) -> str:
        return f"Plan( {self.trigger}, {self.context} -> {self.body.__name__}() )"
    
    def __repr__(self):
        return self.__str__()

    def executable(self, *args, **kwargs):
        for condition in self.conditions:
            try:
                if not condition(*args, **kwargs):
                    return False
            except Exception as e:
                return False
        return True
    
@dataclass
class Ask:
    """ Asks represent a request for information from the Agent """
    data_type: Belief | Goal
    source: str = "unknown"
    reply_event: threading.Event = threading.Event()
    reply_content: Belief | Goal | Plan | List[Belief | Goal | Plan] | None = None 
    
    @property
    def info(self) -> dict:
        return {
            "data_type": "Ask",
            "data": self.data_type.info,
            "source": self.source,
            "reply_content": self.reply_content
        }
    
    def __str__(self) -> str:
        return f"Ask( {self.data_type}, {self.source}, reply={self.reply_content} )"
    
    def __repr__(self):
        return self.__str__()

@dataclass
class Intention:
    """ Intentions represent how an Agent will execute a Plan to respond to an Event """
    plan: Plan = field(default_factory=Plan)
    event: Event = field(default_factory=Event)
    args: tuple | Any = field(default_factory=tuple)
    
    @property
    def info(self) -> dict:
        return {
            "plan": self.plan.info,
            "event": self.event.info,
            "args": self.args
        }
    
    def __str__(self) -> str:
        return f"{self.event} -> {self.plan.body.__name__}() Context={self.plan.context,self.args}"
    
    def __repr__(self):
        return self.__str__()

MSG = Belief | Ask | Goal | Plan | List[Belief | Goal | Plan]

Data_Type = TypeVar("Data_Type", bound=Belief | Goal | Plan | Event)

_type_env_set = {Environment, "environment", "envrmnt", "env"}
_type_ch_set = {Channel, "channel", "chnnl", "ch", "c"}

def pl(change: Event_Change, data: Belief | Goal, context: Belief | Goal | List[Belief | Goal] | Condition = [], plan_type: Plan_Type = default):
    class decorator:
        def __init__(self,func):
            self.func = func
  
        def __set_name__(self, instance: Agent, name: str):
            if not isinstance(change, Event_Change): 
                raise TypeError(f"Expected {Event_Change._member_names_} for Change, got {type(change).__name__}:{change}")
            if not isinstance(data, Belief | Goal):
                raise TypeError(f"Expected Belief or Goal for Information, got {type(data).__name__}:{data}")

            context_condition: Condition | None
            
            match context:
                case Condition() if not isinstance(context, Belief | Goal):
                    context_condition = context
                
                case Belief() | Goal():
                    context_condition = Condition("=", "=", context)
                
                case Iterable():
                    context_condition = reduce(and_, context) if context else None
            
            event = Event(change,data)
            plan = Plan(event,context_condition,self.func,plan_type=plan_type)
            try:
                instance._plans += [plan]
            except AttributeError:
                instance._plans = [plan]
            
        def __call__(*args, **kwargs):
            print(f'{args} {kwargs}')
        
    return decorator

class Agent: 
    """Extends all capabilities of a BDI Agent"""
    def __init__(
        self,
        name: Optional[str] = None,
        beliefs: Optional[Iterable[Belief] | Belief] = None,
        goals: Optional[Iterable[Goal] | Goal] = None,
        show_exec = False,
        show_cycle = False,
        show_prct = False,
        show_slct = False,
        logging = False,
        instant_mail = False,
        read_all_mail = False,
        max_intentions = 5
    ):              
        self.show_exec: bool = show_exec
        self.show_cycle: bool = show_cycle
        self.show_prct: bool = show_prct
        self.show_slct: bool = show_slct
        self.logging = logging
        self.cycle_log: Dict[float, list[Dict[str, Any]]] = dict()
        self.cycle_counter = 0
        self.last_log: Any = ""
        self.printing = True
        
        from maspy.admin import Admin
        self.unique: bool = False
        self.tcolor = ""
        if name is None:
            name = type(self).__name__
        self.tuple_name: tuple[str, int] = (name, 0)
        self.my_name = name
        Admin().add_agents(self)
        self.print_queue = Admin().print_queue
        self.sys_time = Admin().sys_time
        self.logger = getLogger("maspy")
        self.delay: int|float = 0
        self.stop_flag: threading.Event | None = None
        self.running: bool = False
        self.thread: threading.Thread | None = None
        self._plan_executor: ThreadPoolExecutor = ThreadPoolExecutor(
            max_workers=max_intentions, 
            thread_name_prefix=f"{self.my_name}_plans"
        )
        self._msg_executor: ThreadPoolExecutor = ThreadPoolExecutor(
            max_workers=5,
            thread_name_prefix=f"{self.my_name}_msgs"
        )
                
        self.lock = threading.Lock()
        self.env_lock = threading.Lock()
        self.ch_lock = threading.Lock()
        self.update_lock = threading.Lock()
        self.intention_lock = threading.Lock()
        self.print_lock = threading.Lock()
        self.msg_lock = threading.Lock()
        self.reply_event: Dict[tuple, threading.Event] = {}
        self._work_condition: threading.Event = threading.Event()
        self._has_pending_mail = False
        self._has_pending_perception = False
        
        self._ml_models: List = []
        self.policies: List = []
    
        self._environments: Dict[str, Environment] = dict()
        self._channels: Dict[str, Channel] = dict()
        self._dicts: Dict[str, Union[Dict[str, Environment], Dict[str, Channel]]] = {"environment":self._environments, "channel":self._channels}
        self._env_changed: Dict[str, bool] = {}
        self._env_changed_count: int = 0
        
        self._strategies: list[EnvModel] = []
        self.auto_action: bool = False

        self.max_intentions: int = max_intentions
        self.og_max_intentions: int = max_intentions
        self.last_intention: Intention | None = None
        self.__intentions: list[Intention] = []
        self.__supended_intentions: deque[tuple[Intention, str, Event | None]] = deque()
        self.__running_intentions: deque[Intention] = deque()
        
        self.__events: List[Event] = []
        self._pending_events: List[tuple[Event, int, str]] = []
        self.curr_event: Event | None = None
        self.last_event: Event | None = None
        self.__beliefs: Dict[str, Dict[str, Set[Belief]]] = dict()
        self.__goals: Dict[str, Dict[str, Set[Goal]]] = dict()
        self.__perceptions: Dict[str, Dict[str, Set[Percept]]] = dict()
        self.belief_list: List[Belief] = []
        self.goal_list: List[Goal] = []
        self.last_goal: Goal | None = None
        self.percept_filter: Dict[str, set[str]] = {ignore.name: set(), focus.name: set()}
        
        self.saved_msgs: deque = deque()
        self.last_sent: list[tuple[str, str | List[str] | broadcast, str, MSG]] = []
        self.last_recv: list[tuple[str, MSG]] = []
        self.last_plan: Plan | None = None
        self.relevant_plans: List[Plan] | None = None
        
        if beliefs:
            if self.logging: self.logger.debug(f"Adding Initial Beliefs: {beliefs}", extra=self.agent_info)
            self.add(beliefs, False)
        if goals: 
            if self.logging: self.logger.debug(f"Adding Initial Goals: {goals}", extra=self.agent_info)
            self.add(goals, False)
        
        self._plans: List[Plan]
        try:    
            if not self._plans:
                self._plans = []
        except AttributeError:
            self._plans = []
        self._plan_index: Dict[tuple, List[Plan]] = {}
        self._build_plan_index()

        self.instant_mail = instant_mail
        self.read_all_mail = read_all_mail
        self.connect_to(Channel())
    
    def print(self,*args, **kwargs):
        """Formatted MASPY Print Function"""
        if not self.printing:
            return
        f_args = "".join(map(str, args))
        f_kwargs = "".join(f"{key}={value}" for key, value in kwargs.items())
        name = self.my_name if not self.unique else self.tuple_name[0]
        msg = f"{self.tcolor}Agent:{name}> {f_args}{f_kwargs}{bcolors.ENDCOLOR}"
        self.print_queue.put(msg)
        self.logger.info(msg, extra=self.agent_info)
        
    @property
    def print_beliefs(self):
        """Prints all Beliefs of the Agent"""
        buffer = "Beliefs:"
        for sources_dict in self.__beliefs.values():
            for belief_set in sources_dict.values():
                for belief in belief_set:
                    buffer += f'\n\t{belief}'
        if buffer == "Beliefs:":
            buffer = "Perceptions:"
        else:
            buffer += "\nPerceptions:"
        for sources_dict in self.__perceptions.values():
            for percept_set in sources_dict.values():
                for percept in percept_set:
                    buffer += f'\n\t{percept}'
        self.print(buffer,"\n")

    @property
    def print_goals(self):
        """Prints all Goals of the Agent"""
        buffer = "Goals:"
        for group_keys in self.__goals.values():
            for goal_set in group_keys.values():
                for goal in goal_set:
                    buffer += f'\n\t{goal}'
        self.print(buffer)
    
    @property
    def print_plans(self):
        """Prints all Plans of the Agent"""
        buffer = "Plans:"
        for plan in self._plans:
            buffer += f'\n\t{plan}'
        self.print(buffer)
    
    @property
    def print_events(self):
        """Prints all Events of the Agent"""
        self.print("Events:",self.__events) 
    
    @property
    def print_intentions(self):
        """Prints all Intentions of the Agent"""
        buffer = "Running Intentions:"
        for plan, _ in self.__running_intentions:
            buffer += f"\n\t{plan}"
        self.print(buffer)
    
    @property
    def agent_info(self):
        """Returns the latest internal information from the Agent"""
        return {
            "class_name": "Agent",
            "my_name": self.my_name if not self.unique else self.tuple_name[0],
            "cycle": self.cycle_counter,
            "curr_event": self.curr_event.info if self.curr_event else None,
            "aplc_plans": [self.rlv_plans.info for self.rlv_plans in (self.relevant_plans or [])],
            "running_intentions": [rng_intention.info for rng_intention in self.__running_intentions],
            "num_intentions": self.__running_intentions.__len__(),
            "last_intention": self.last_intention.info if self.last_intention else None,
            "last_event": self.last_event.info if self.last_event else None,   
            "intentions": [intention.info for intention in self.__intentions],
            "events": [event.info for event in self.__events],
            "saved_msgs": list(self.saved_msgs),
            "beliefs": [belief.info for belief in self.belief_list], 
            "perceptions": [p.info for p_dict in self.__perceptions.values() for p_set in p_dict.values() for p in p_set],
            "goals": [goal.info for goal in self.goal_list],
            "envs": list(self._environments.keys()), 
            "chs": list(self._channels.keys())
        }
    
    def _build_plan_index(self):
        self._plan_index.clear()
        for plan in self._plans:
            key = (plan.trigger.change, type(plan.trigger.data), plan.trigger.data.name)
            if key not in self._plan_index:
                self._plan_index[key] = []
            self._plan_index[key].append(plan)
    
    def filter_perceptions(self, operation: Operation, option: Option, group: List[str] | str):
        """
        Filters how the Agents perceives the Environment - by ignoring and(or) focusing on Percept's groups

        Parameters
        ----------
            operation : Operation[add or rm]
                Adding or removing a filter to the Agent.
            option : Option[ignore or focus]
                Determines whether to ignore or focus on the given groups.
            group : List or str or str
                The group(s) to ignore or focus on.
        """
        assert isinstance(operation,Operation), f"Invalid operation. Choose {Operation}."
        assert isinstance(option,Option), f"Invalid option. Choose {Option}."

        if isinstance(group, str):
            group = [group]
            
        option_str = option.name
        self.print(f'{operation.name} {option_str} {group} to filter.')
        for g in group:
            if operation == Operation.add:
                self.percept_filter[option_str].add(g)
            elif operation == Operation.rm and g in self.percept_filter[option_str]:
                self.percept_filter[option_str].remove(g)
            else:
                if self.logging: self.logger.warning(f"{g} not in {option_str} filter.", extra=self.agent_info)
    
    def connect_to(self, target: Environment | Channel | str) -> Environment | Channel | None:
        """
        Connects agent to a Environment or Channel 

        Parameters
        ----------
            target : Environment or Channel
                Connects to the given instance
            target : str
                Searches for a file with 'str' filename to connect
        Returns
        -------
            connection : (Environment or Channel
                The connected Environment or Channel 
            None : when no connectable target is found
        """
        if isinstance(target, str):
            instance = Environment.get_instance(target) or Channel.get_instance(target)
            if instance:
                target = instance
                
        if isinstance(target, str):
            classes: List[tuple] = []
            try:
                imported = import_module(target)
            except ModuleNotFoundError:
                if self.logging: self.logger.error(f"No File named '{target}' found", extra=self.agent_info)
                self.print(f"No File named '{target}' found")
                return None
            for name, obj in inspect.getmembers(imported):
                if inspect.isclass(obj) and name != "Environment" and name != "Channel":
                    lineno = inspect.getsourcelines(obj)[1]
                    classes.append((lineno, obj))
            classes.sort()
            target = classes[0][1](target)      
            del imported 
                    
        match target:
            case Environment():
                with self.env_lock:
                    self._environments[target.my_name] = target
                    self._env_changed.update({target.my_name:False})
            case Channel():
                with self.ch_lock:
                    self._channels[target.my_name] = target
            case _:
                raise Exception(f'Invalid type {type(target)}:{target} - was expecting Channel or Environment')
        
        target.add_agents(self)
        return target

    def disconnect_from(self, target: Channel | Environment | str):
        """
        Disconnects the agent from a Environment or Channel 

        Parameters
        -----------
        target : Environment, Channel or str 
            Disconnects from the connected target
        """
        if isinstance(target, str):
            instance = Environment.get_instance(target) or Channel.get_instance(target)
            if instance:
                target = instance
                
        match target:
            case Environment():
                with self.env_lock:
                    target._rm_agent(self)
                    del self._environments[target.my_name]
                    del self._env_changed[target.my_name]
            case Channel():
                with self.ch_lock:
                    target._rm_agent(self)
                    del self._channels[target.my_name]
                
    def add_policy(self, policy: EnvModel):
        """
        Adds a policy to the Agent's Reasoning Cycle

        Parameters
        ----------
        policy: EnvModel
            Modelled Environment with the Learning Class
        """
        if self.logging: self.logger.info(f"Adding model for {policy.name}", extra=self.agent_info)
        self._strategies.append(policy)
        if policy.name not in self._environments.keys():
            self.connect_to(policy.env)
    
    def _new_event(self,change: Event_Change, data: Belief | Goal | Percept | Iterable[Belief | Goal| Percept], instant: bool = False):
        """ 
        Creates a new Event and adds it to the Agent
        
        Parameters
        ----------
        change : Event_Change
            The type of change (gain | lose | test | success | failure)
        data : Belief | Goal | Percept | Iterable[Belief | Goal| Percept]
            The data or information that Changed
        instant : bool
            If True, an applicable Plan for this Event is executed instantly [default: False]
        """
        new_event: Event
        if not isinstance(data, Iterable):
            data = [data]
            
        for dt in data:
            if isinstance(dt, Belief | Percept) and not dt.adds_event: 
                continue
            new_event = Event(change, dt)
            if instant:
                self._instant_plan(new_event)
            else:
                self.__events.append(new_event)
                self._check_event_supended(new_event)
        self._notify_work()
                        
    def _check_event_supended(self,event: Event):
        """ 
        Checks if a supended Intention should be resumed because of a new Event
        
        Parameters
        ----------
        event : Event
            The Event to check
        """
        for intention in self.__supended_intentions:
            if intention[0].event.change == event.change and self._compare_data(intention[0].event.data, event.data, True, True, False):
                intention[0].plan.ev_ctrl.set()
    
    def _get_type_base(self, 
            data_type: Belief | Goal | Plan | Event | Type[Belief | Goal | Plan | Event]
        ) -> tuple[Dict[str, Dict[str, Set[Belief]]], Dict[str, Dict[str, Set[Percept]]]] | Dict[str, Dict[str, Set[Goal]]] | List[Plan] | List[Event] | None:
        """ 
        Returns the database for a given type of data (Belief | Goal | Plan | Event)
        
        Parameters
        ----------
        data_type : Belief | Goal | Plan | Event | Type[Belief | Goal | Plan | Event]
            The type of data
        
        Returns
        -------
        tuple[Dict[str, Dict[str, Set[Belief]]], Dict[str, Dict[str, Set[Percept]]]] | Dict[str, Dict[str, Set[Goal]]] | List[Plan] | List[Event] | None
            The database
        """
        if isinstance(data_type,Belief) or data_type == Belief:
            return (self.__beliefs, self.__perceptions)
        elif isinstance(data_type,Goal) or data_type == Goal:
            return self.__goals
        elif isinstance(data_type,Plan) or data_type == Plan:
            return self._plans
        elif isinstance(data_type,Event) or data_type == Event:
            return self.__events
        else:
            print(f"Type is neither Belief | Goal | Plan | Event : {data_type}")
            return None
    
    def update_lists(self, data_type: Belief | Goal, change: str):
        """ 
        Updates the lists of Beliefs and Goals
        
        Parameters
        ----------
        data_type : Belief | Goal
            The type of data
        change : str
            The type of change (add | rm)
        """
        if change == "add":
            if isinstance(data_type,Belief):
                self.belief_list.append(data_type)
            else:
                self.goal_list.append(data_type)
        if change == "rm":
            if isinstance(data_type,Belief):
                self.belief_list.remove(data_type)
            else:
                self.goal_list.remove(data_type)
    
    def _check_caller(self) -> str:
        """ 
        Returns the name of the method that called the current method
        """
        stack = inspect.stack(3)
        caller_frame = stack[2]
        caller_method = caller_frame.function

        if caller_method != "__init__" and caller_method in Agent.__dict__:
            return f"Called internally from {type(self).__name__}:{caller_method}"
        else:
            return f"Called externally from {type(self).__name__}:{caller_method}"
    
    def _is_type_iter(self, it: Iterable[object] , typ: Type[Data_Type]) -> TypeGuard[Iterable[Data_Type]]:
        """ 
        Checks if all elements in an iterable are of a given type
        """
        return all(isinstance(i, typ) for i in it)  
          
    def add(self, data_type: Belief | Goal | Plan | Iterable[Belief | Goal | Plan], instant: bool = False, no_lock: bool = False):
        """
        Adds one or more Beliefs, Goals or Plans to the Agent.

        Parameters
        ----------
        data_type : Belief, Goal, Plan, or list of Beliefs, Goals, or Plans
            The information to be added.
        instant : bool, default=False
            If True, an applicable plan with the triggered event is executed immediately
        """
        if self.running is False:
            instant = False
        if self.logging: self.logger.debug(f"Adding Info: {self._format_data("Adding Info", data_type=data_type,instant=instant)}", extra=self.agent_info)
        
        if isinstance(data_type, Plan):
            self._plans.append(data_type)
            return
        elif isinstance(data_type, Iterable) and self._is_type_iter(data_type, Plan):
            self._plans.extend(data_type)
            return
        
        data_type = cast(Belief | Goal |Iterable[Belief | Goal], data_type)
        cleaned_data = self._clean(data_type)
        lock = nullcontext() if no_lock else self.update_lock
        for type_data, data in cleaned_data.items():
            if len(data) == 0: 
                continue
            type_base = self._get_type_base(type_data)
            with lock:
                if isinstance(type_base,dict):
                    merge_dicts(data,type_base)
                elif isinstance(type_base,tuple):
                    merge_dicts(data,type_base[0])
            
            for src in data.values():
                for values in src.values():
                    for data_v in values:    
                        self.update_lists(data_v,"add")
                        
        self._new_event(gain,data_type,instant)
    
    def rm(self, data_type: Belief | Goal | Plan | Iterable[Belief | Goal | Plan], instant: bool = False, no_lock: bool=False):
        """
        Removes one or more Beliefs, Goals or PLans to the Agent.

        Parameters
        ----------
        data_type : Belief, Goal, Plan, or list of Beliefs, Goals, or Plans
            The information to be removed.
        instant : bool, default=False
            If True, an applicable plan with the triggered event is executed immediately
        """
        if self.running is False:
            instant = False
        if self.logging: self.logger.debug(f"Removing Info: {self._format_data("Removing Info", data_type=data_type,instant=instant)}", extra=self.agent_info)
        
        if not isinstance(data_type, Iterable): 
            data_type = [data_type]
        lock = nullcontext() if no_lock else self.update_lock
        for typ in data_type:
            found_typ = self.get(typ)
            if found_typ is None:
                if self.logging: self.logger.warning(f"Data_Type {typ} is not available to be removed", extra=self.agent_info)
                self.print(f"Data_Type {typ} is not available to be removed")
                continue
            assert not isinstance(found_typ, Event | list), f"Data_Type {found_typ} is not a Belief, Goal or Plan"
            typ = found_typ
            with lock:
                if isinstance(typ, Belief):
                    a = self.__beliefs[typ.source]
                    b = a[typ.name]
                    if len(b) == 1:
                        del a[typ.name]
                    else:
                        b.remove(typ)
                elif isinstance(typ, Goal):
                    c = self.__goals[typ.source]
                    d = c[typ.name]
                    d.remove(typ)
                elif isinstance(typ, Plan):
                    self._plans.remove(typ)
                else:
                    if self.logging: self.logger.warning(f"Data_Type {typ} is neither Belief, Goal or Plan", extra=self.agent_info)
                    self.print(f"Data_Type {typ} is neither Belief, Goal or Plan")
            if not isinstance(typ, Plan):
                self.update_lists(typ,"rm")

                
        if self._is_type_iter(data_type, Belief) or self._is_type_iter(data_type, Goal):
            self._new_event(lose,data_type,instant)

    def test(self, data_type: Belief | Goal, instant: bool = False):
        """
        Tests if the Agent has a Belief or Goal

        Parameters
        ----------
        data_type : Belief or Goal
            The information to be tested
        instant : bool, default=False
            If True, an applicable plan with the triggered event is executed immediately
        """
        if self.running is False:
            instant = False
        if self.logging: self.logger.debug(f"Testing Info: {self._format_data("Testing Info", data_type=data_type,instant=instant)}", extra=self.agent_info)
        self._new_event(test,data_type,instant)
    
    def has(self, data_type: Belief | Goal | Plan | Event) -> bool:
        """
        Checks if the agent has a Belief, Goal, Plan, or Event

        Parameters
        ----------
        data_type : Belief, Goal, Plan, or Event 
            The Information to be checked
        Returns:
            bool: True if it has, False if not
        """
        if isinstance(data_type, Belief):
            if data_type.source != "self":
                return self.get(data_type) is not None
            try:
                return data_type in self.__beliefs[data_type.source][data_type.name]
            except KeyError:
                return False
        elif isinstance(data_type, Goal):
            try:
                return data_type in self.__goals[data_type.source][data_type.name]
            except KeyError:
                return False
        return self.get(data_type) is not None

    def get(self, data_type: Belief | Goal | Plan | Event | Type[Belief | Goal | Plan | Event],
        search_with:  Optional[Belief | Goal | Plan | Event] = None,
        all: bool = False, ck_chng: bool = True, ck_type: bool = True, ck_values: bool = True, ck_src: bool=True, no_lock: bool=False
    ) -> Belief | Goal | Plan | Event | List[Belief | Goal | Plan | Event] | None:
        """
        Retrieves specific data from the agent's knowledge on the given data_type and search parameters

        Parameters
        ----------
            data_type : Belief, Goal, Plan, or Event
                The type of data to retrieve.
            search_with : Belief, Goal, Plan or Event, default=None
                The infomation to search with.
            all : bool, default=False 
                Whether to return all matching data or just the first match.
            ck_chng : bool, default=True
                Whether to check the changes argument in the data.
            ck_type : bool, default=True
                Whether to check the type of the data.
            ck_values : bool, default=True
                Whether to check the arguments of the data.
            ck_src : bool, default=True
                Whether to check the source of the data.
        Returns
        -------
            found_info : Belief, Goal, Plan, Event, or a list of these
                The retrieved data of the specified type.
            None: If no matches are found, it returns None.
        """  
        if isinstance(data_type, type): 
            data_type = data_type()
        type_base = self._get_type_base(data_type)

        if type_base is None:
            return None
        if search_with is None: 
            search_with = data_type

        change, data = self._to_belief_goal(search_with)
        if data is None: return None
        
        lock = nullcontext() if no_lock else self.update_lock
        found_data: List[Belief | Goal | Plan | Event] = []
        match data_type:
            case Belief() | Goal() | Percept():  
                if isinstance(type_base, tuple):
                    for base in type_base:
                        with lock:
                            found = self._search(base, data, ck_type, ck_values, ck_src, all)
                        if all:
                            found_data.extend(found)
                        if not all and found:
                            return found
                elif isinstance(type_base, dict):
                    with lock:
                        found = self._search(type_base, data, ck_type, ck_values, ck_src, all)
                    if all:
                        found_data.extend(found)
                    if not all and found:
                        return found            
            case Plan() | Event(): 
                for plan_event in type_base:
                    assert isinstance(plan_event, Plan | Event)
                    chng, belf_goal = self._to_belief_goal(plan_event)
                    if belf_goal is None: continue
                    
                    if change and ck_chng and chng != change:
                        continue
                    if self._compare_data(belf_goal,data,ck_type,ck_values,ck_src):
                        found_data.append(plan_event)
                        if not all: 
                            return plan_event
            case _: 
                pass
        if found_data:
            return found_data  
        else:
            current_frame = inspect.currentframe()
            assert current_frame is not None
            caller_frame = current_frame.f_back
            assert caller_frame is not None
            caller_function_name = caller_frame.f_code.co_name
            if caller_function_name in {'_retrieve_plans','recieve_msg','_retrieve_context','_select_plan','has','rm','_check', '_format_check'}:
                return None
            if data_type == search_with:
                self.print(f'Does not contain {type(data_type).__qualname__} like {data_type}. Searched during {caller_function_name}()')
            else:
                self.print(f'Does not contain {type(data_type).__qualname__} like {search_with}. Searched during {caller_function_name}()')
            return None
    
    def _search(self, type_base: Dict[str, Dict[str, Set[Belief]]] | Dict[str, Dict[str, Set[Percept]]] | Dict[str, Dict[str, Set[Goal]]], data: Belief | Goal, ck_type: bool, ck_values: bool, ck_src: bool, all: bool):
        """ 
        Private Internal function to search for data
        
        Parameters
        ----------
            type_base : Dict[str, Dict[str, Set[Belief]]] | Dict[str, Dict[str, Set[Percept]]] | Dict[str, Dict[str, Set[Goal]]]
                The type of data to search for.
            data : Belief | Goal
                The data to search for.
            ck_type : bool
                Whether to check the type of the data.
            ck_values : bool
                Whether to check the arguments of the data.
            ck_src : bool
                Whether to check the source of the data.
            all : bool
                Whether to return all matching data or just the first match.
        
        Returns
        -------
            found : List[Belief | Goal | Percept]
                The retrieved data of the specified type.
            None: If no matches are found, it returns None.
        """
        found: list[Belief | Goal | Percept] = []
        if ck_src and data.source != DEFAULT_SOURCE:
            try:
                data_type_set = type_base[data.source][data.name]
            except KeyError:
                return found
            for data_type in data_type_set:
                if isinstance(data_type, Percept):
                    data_type = Belief(data_type.name, data_type._values, data_type.source, data_type.adds_event)
                if self._compare_data(data_type, data, ck_type, ck_values, ck_src):
                    if not all:
                        return data_type
                    found.append(data_type)
            return found
        else:
            for source_dict in type_base.values():
                try:
                    data_type_set = source_dict[data.name]
                except KeyError:
                    continue
                for data_type in data_type_set:
                    if isinstance(data_type, Percept):
                        data_type = Belief(data_type.name, data_type._values, data_type.source, data_type.adds_event)
                    if self._compare_data(data_type, data, ck_type, ck_values, ck_src):
                        if not all:
                            return data_type
                        found.append(data_type)
        return found
         
    def wait(self, timeout: Optional[float] = None, event: Optional[Event] = None):
        """
        Suspends the current intention for a given time or until a certain event is received.
        
        Parameters
        ----------
            timeout : (float, optional)
                The time in seconds to suspend the intention. Defaults to None.
            event : (Event, optional)
                The event to wait for. Defaults to None.
        """
        reason = ""
        if timeout is not None:
            timeout = max(timeout-0.5, 0)
            reason += "timeout"
        if event is not None:
            if reason == "":
                reason += "event"
            else:
                reason += "_event"
            
        if timeout is not None or event is not None: 
            tracing = True
            level = 1
            while tracing:
                frame = sys._getframe(level)
                if frame.f_code.co_name != "_run_plan":
                    prev_frame = frame
                    level += 1
                else:
                    plan_function_name = prev_frame.f_code.co_name
                    tracing = False
            
            intention: Intention
            
            for run_int in self.__running_intentions:
                if run_int.plan.body.__name__ == plan_function_name:
                    intention = run_int
                    break
            else:
                self.print(f"Plan {plan_function_name} not found")
                return
        else:
            return
        
        intention_reason = (intention, reason, event)
        
        self.__running_intentions.remove(intention)
        self.__supended_intentions.append(intention_reason)
        
        intention.plan.ev_ctrl.wait(timeout)
        
        self.__supended_intentions.remove(intention_reason)
        
        while self.__running_intentions.__len__() > self.max_intentions:
            sleep(0.01)

        self.__running_intentions.append(intention)
    
    def drop_all_desires(self):
        """
        Stops and removes all **Intentions** and **Events** from the **Agent**.
        """
        self.drop_all_events()
        self.drop_all_intentions()
    
    def drop_all_events(self):
        """
        Removes all **Events** from the **Agent**.
        """
        self.__events = []
    
    def drop_all_intentions(self):
        """
        Stops and removes all **Intentions** from the **Agent**.
        """
        self.__intentions = []
        for suspended_intention in self.__supended_intentions:
            self._force_close_thread(suspended_intention[1])
        self.__supended_intentions = []
    
    def drop_desire(self, data_type: Belief | Goal):
        """
        Stops and removes all **Intentions** and **Events** from the **Agent** that contain the given data_type.
        
        Parameters
        ----------
        data_type : Belief or Goal
            The data type used to remove intentions and events.
        """
        self.drop_event(data_type)
        self.drop_intention(data_type)
        
    def drop_event(self, data_type: Belief | Goal):
        """
        Removes all **Events** from the **Agent** that contain the given data_type.
        
        Parameters
        ----------
        data_type : Belief or Goal
            The data type used to remove events.
        """
        for event in self.__events:
            if self._compare_data(event.data, data_type, ck_type=True, ck_values=True, ck_src=False):
                self.__events.remove(event)
    
    def drop_intention(self, data_type: Belief | Goal):  
        """
        Stops all **Intentions** from the **Agent** that contain the given data_type.
        
        Parameters
        ----------
        data_type : Belief or Goal
            The data type used to remove intentions.
        """       
        for intention in self.__intentions:
            if self._compare_data(intention.plan.trigger.data, data_type, ck_type=True, ck_values=True, ck_src=False): 
                self.__intentions.remove(intention)

    def _get_running_intentions(self):
        return self.__running_intentions
    
    def _to_belief_goal(self, data_type: Belief | Goal | Plan | Event) -> tuple[Optional[str | Event_Change], Optional[Belief | Goal]]:
        """ 
        Converts a belief, goal, plan or event to a tuple with the type change and the belief or goal. 
        
        Parameters
        ----------
        data_type : Belief | Goal | Plan | Event
            The data type to convert.
        
        Returns
        -------
        change : Optional[str | Event_Change]
            The change type.
        belief_goal : Optional[Belief | Goal]
            The belief or goal.
        """
        change: Optional[str | Event_Change] = None
        belief_goal: Optional[Belief | Goal] = None
        match data_type:
            case Belief() | Goal():
                belief_goal = data_type
            case Plan(): 
                event_dt = data_type.trigger.data
                if isinstance(event_dt, Percept):
                    event_dt = Belief(event_dt.name, event_dt._values, event_dt.source)
                change = data_type.trigger.change
                belief_goal = event_dt
            case Event(): 
                event_dt = data_type.data
                if isinstance(event_dt, Percept):
                    event_dt = Belief(event_dt.name, event_dt._values, event_dt.source)
                change = data_type.change
                belief_goal = event_dt
            case _: 
                self.print(f"Error in _to_belief_goal: {type(data_type)}:{data_type}")
                return None, None
        return change,belief_goal
    
    def _compare_data(self, data1: Belief | Goal | Percept | None, data2: Belief | Goal | Percept | None, ck_type: bool, ck_values: bool, ck_src: bool):
        """ 
        Compares two beliefs, goals or percepts.
        
        Parameters
        ----------
        data1 : Belief | Goal | Percept
            The first data to compare.
        data2 : Belief | Goal | Percept
            The second data to compare.
        ck_type : bool
            If True, the type of the data is checked.
        ck_values : bool
            If True, the values of the data are checked.
        ck_src : bool
            If True, the source of the data is checked.
        
        Returns
        -------
        bool
            True if the data are the same, False otherwise.
        """
        if data1 is None or data2 is None:
            if self.show_slct: self.print(f"Comparing: {data1}  &  {data2} >> None")
            return False
        if ck_type and type(data1) is not type(data2):
            if self.show_slct: self.print(f"Comparing: {data1}  &  {data2} >> Different type")
            return False
        if data1.name != data2.name:
            if self.show_slct: self.print(f"Comparing: {data1}  &  {data2} >> Different key")
            return False
        if ck_src and data2.source != DEFAULT_SOURCE and data1.source != data2.source:
            if self.show_slct: self.print(f"Comparing: {data1}  &  {data2} >> Different source")
            return False
        if not ck_values:
            return True
        if data1.v_len != data2.v_len:
            if self.show_slct: self.print(f"Comparing: {data1}  &  {data2} >> Different values length {data1.v_len} x {data2.v_len}")
            return False
        
        for arg1,arg2 in zip(data1._values, data2._values):
            if arg1 is Any or arg2 is Any or arg1 == arg2:
                continue
            if self.show_slct: self.print(f"Comparing: {data1}  &  {data2} >> Different values {arg1} x {arg2}")
            return False
        else:
            if self.show_slct: self.print(f"Comparing: {data1}  &  {data2} >> Compatible")
            return True
    
    def send(self, target: str | List[str] | type[broadcast], msg_act: Act, msg: MSG, channel: str = DEFAULT_CHANNEL, no_lock: bool = False) -> None | Belief | Goal | Plan | Iterable[Belief | Goal | Plan]: 
        """
        Sends a message to a target agent or list of agents, optionally through a channel
        
        Parameters
        ----------
            target : str, list of str or broadcast: 
                a broadcast, target agent name, or agent names to send the message to.
            msg_act : Act :
                The type of message being sent.
            msg : Belief, Goal, Ask, Plan or Beliefs, Goals, Asks or Plans 
                The message to be sent.
            forget : (bool, optional)
                Whether the target adds or forgets the message information. Defaults to False.
            channel : (str, optional) 
                The name of channel to send the message through. Defaults to DEFAULT_CHANNEL.
        """
        self.last_sent = []
        if type(target) is str and not target.split("_")[-1].isdigit():
            target = f"{target}_1"
        try:
            if msg_act.name in ['askOneReply','askAllReply']:
                with self.lock: # Dont remember why this lock is needed
                    assert isinstance(msg, Belief | Goal)
                    msg = Ask(msg, self.my_name)
                    
                msg.reply_event.clear()
                future = self._msg_executor.submit(self._channels[channel]._send, self.my_name,target,msg_act,msg)
                was_set = msg.reply_event.wait(timeout=2)
                
                if msg.reply_content is not None:
                    self.add(msg.reply_content, False, no_lock)
                    if self.logging: self.logger.info(f'Reply for {msg} from {target}', extra=self.agent_info)
                    return msg.reply_content
                elif was_set:
                    if self.logging:
                        self.logger.warning(f"{target} Doesnt have a reply for {msg}", extra=self.agent_info)
                    else:
                        self.print("{target} Doesnt have a reply for {msg}")
                    return None
                else:
                    if self.logging:
                        self.logger.warning(f"Timeout while waiting a reply for {msg}", extra=self.agent_info)
                    else:
                        self.print(f"Timeout while waiting a reply for {msg}")    
                    return None
            else:
                future = self._msg_executor.submit(self._channels[channel]._send, self.my_name,target,msg_act,msg)
            
            ch = "in the default channel"
            if channel != DEFAULT_CHANNEL:
                ch = f"in the channel {channel}"
            if isinstance(target,str | list): 
                if self.logging: self.logger.debug(f'Send Message: {self.my_name}  to  {target}  -  {msg_act.name} {msg} {ch}', extra=self.agent_info)
            else:
                if self.logging: self.logger.debug(f'Send Message: {self.my_name}  broadcasting  {msg_act.name} {msg} {ch}', extra=self.agent_info)
        except KeyError:
            if self.show_exec:
                self.print(f'Not Connected to Selected Channel:{channel}')
            if self.logging: self.logger.warning(f'Agent:{self.my_name} Not Connected to Selected Channel:{channel}', extra=self.agent_info)
            raise KeyError(f"Connection Error: Not Connected to Selected Channel:{channel}")
        except AssertionError:
            raise
        return None
    
    def sendf(self, target: str | List[str] | broadcast, msg: MSG, forget: bool = False, channel: str = DEFAULT_CHANNEL, no_lock: bool = False) -> None:   
        """
        Sends a message to a target agent or list of agents, optionally through a channel
        
        Parameters
        ----------
            target : str, list of str or broadcast: 
                a broadcast, target agent name, or agent names to send the message to.
            msg : Belief, Goal, Ask, Plan or Beliefs, Goals, Asks or Plans 
                The message to be sent.
            forget : (bool, optional)
                Whether the target adds or forgets the message information. Defaults to False.
            channel : (str, optional) 
                The name of channel to send the message through. Defaults to DEFAULT_CHANNEL.
        """
        
        self.last_sent = []
        if type(target) is str and not target.split("_")[-1].isdigit():
            target = f"{target}_1"
        try:
            typ = "forget" if forget else "add"
            future = self._msg_executor.submit(self._channels[channel]._sendf, self.my_name,target,msg,typ)
            self.last_sent.append((self.my_name,target,typ,msg))
            
            ch = "in the default channel"
            if channel != DEFAULT_CHANNEL:
                ch = f"in the channel {channel}"
            if isinstance(target,str | list): 
                if self.logging: self.logger.debug(f'Send Message: {self.my_name}  to  {target}  -  {typ} {msg} {ch}', extra=self.agent_info)
            else:
                if self.logging: self.logger.debug(f'Send Message: {self.my_name}  broadcasting  {typ} {msg} {ch}', extra=self.agent_info)
        except KeyError:
            if self.show_exec:
                self.print(f'Not Connected to Selected Channel:{channel}')
            if self.logging: self.logger.warning(f'Agent:{self.my_name} Not Connected to Selected Channel:{channel}', extra=self.agent_info)
        except AssertionError:
            raise
        return None

    def ask(self, target: str | List[str] | broadcast, msg: MSG, all: bool = False, wait_reply: bool = False, channel: str = DEFAULT_CHANNEL, no_lock: bool = False) -> None | Belief | Goal | Plan | Iterable[Belief | Goal | Plan]:
        """
        Sends a message to target agent asking for an information
        Optionally, the agent can wait for the reply

        Parameters
        ----------
            target : str, list of str or broadcast: 
                a broadcast, target agent name, or agent names to send the message to.
            msg : Belief, Goal, Plan or Beliefs, Goals, Asks or Plans 
                The information being Asked.
            all : bool, optional): 
                Whether to asks for all similar information. Defaults to False.
            wait_reply (bool, optional): 
                Whether to waits for the reply. Defaults to False.
            channel (str, optional): 
                The name of channel to send the message through. Defaults to DEFAULT_CHANNEL.

        Returns:
             reply : Belief, Goal, Plan or List of Beliefs, Goals, or Plans, optional
                An MSG when a reply is being waited for. None otherwise.
        """
        try:
            with self.lock: # Dont remember why this lock is needed
                assert isinstance(msg, Belief | Goal)
                msg = Ask(msg, self.my_name)
                
            #self._channels[channel]._send(self.my_name,target,msg_act,msg)
            typ = f'ask{"All" if all else ""}{"Reply" if wait_reply else ""}'
            msg.reply_event.clear()
            future = self._msg_executor.submit(self._channels[channel]._sendf, self.my_name,target,msg,typ)
            self.last_sent.append((self.my_name,target,typ,msg))
            was_set = msg.reply_event.wait(timeout=2)
            
            if msg.reply_content is not None:
                self.add(msg.reply_content, False, no_lock)
                if self.logging: self.logger.info(f'Reply for {msg} from {target}', extra=self.agent_info)
                return msg.reply_content
            elif was_set:
                if self.logging:
                    self.logger.warning(f"{target} Doesnt have a reply for {msg}", extra=self.agent_info)
                else:
                    self.print("{target} Doesnt have a reply for {msg}")
                return None
            else:
                if self.logging:
                    self.logger.warning(f"Timeout while waiting a reply for {msg}", extra=self.agent_info)
                else:
                    self.print(f"Timeout while waiting a reply for {msg}")    
                return None
        except KeyError:
            if self.logging: self.logger.warning(f'Agent:{self.my_name} Not Connected to Selected Channel:{channel}', extra=self.agent_info)
        except AssertionError:
            raise
        return None
    
    def _save_msg(self, typ: str | Act, msg: Belief | Goal | Ask | Plan | List[Belief | Goal | Plan], msg_flag: bool) -> None:
        """ 
        Save Message to Mail
        
        Parameters
        ----------
            typ : str | Act
                The type of the Message
            msg : Belief | Goal | Ask | Plan | List[Belief | Goal | Ask | Plan]
                The Message
            msg_flag : bool
                Whether the Message uses alternate format
        """
        if self.instant_mail: 
            try:
                self._recieve_msgf(cast(str,typ),msg) if msg_flag else self._recieve_msg(cast(Act,typ),msg)
            except AssertionError:
                raise
        else:
            if self.logging: self.logger.info(f'Saving Message to Mail: {msg}', extra=self.agent_info)
            self.saved_msgs.append((typ,msg,msg_flag))
        self._notify_work()

    def _mail(self, selection_function: Callable | None = None) -> None:
        """ 
        Read Oldest Message from Mail
        
        Parameters
        ----------
        selection_function : Callable | None
            The Optional function to select the message [default: None]        
        """
        self.last_recv = []
        if callable(selection_function):
            selection_function(self.saved_msgs)
        else:                
            if self.read_all_mail:
                with self.msg_lock:
                    mail = list(self.saved_msgs)
                    self.saved_msgs.clear()
            elif self.saved_msgs:
                mail = [self.saved_msgs.popleft()]
            else:
                mail = []
            
            while mail:
                typ,msg,msg_flag = mail.pop(0)
                try:
                    self.last_recv.append((typ,msg))    
                    
                    if self.logging: self.logger.debug(f'Receiving Message: {msg}', extra=self.agent_info)
                    
                    self._recieve_msgf(typ,msg) if msg_flag else self._recieve_msg(typ,msg)
                except AssertionError as ae:
                    print(f"\t{repr(ae)}")
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    last_frame = extract_tb(exc_traceback)[-1]
        
                    formatted_last_frame = f"File \"{last_frame.filename}\", line {last_frame.lineno}, in {last_frame.name}\n  {last_frame.line}"
                    
                    print("Error originated from:")
                    print(formatted_last_frame)
                    self.logger.error(formatted_last_frame, extra=self.agent_info)
    
    def _recieve_msg(self, act: Act, msg: MSG) -> None:
        """ 
        Properly Recieve KQML Message
        
        Parameters
        ----------
            act : Act
                The Act / Perfomative of the Message (tell | achieve | untell | unachieve | askOne | askAll)
            msg : MSG
                The Message Content (Belief | Ask | Goal | Plan | List[Belief | Ask | Goal | Plan])
        """
        match act.name:
            case 'tell':
                assert isinstance(msg, Belief),f'Act tell must receive Belief not {type(msg).__qualname__}'
                self.add(msg, False, True)
                
            case 'achieve':
                assert isinstance(msg, Goal),f'Act achieve must receive Goal not {type(msg).__qualname__}'
                self.add(msg, False, True)
                
            case 'untell':
                assert isinstance(msg, Belief),f'Act untell must receive Belief not {type(msg).__qualname__}'
                self.rm(msg, False, True)
                
            case 'unachieve':
                assert isinstance(msg, Goal),f'Act unachieve must receive Goal not {type(msg).__qualname__}'
                self.rm(msg, False, True)
                
            case 'askOne':
                assert isinstance(msg, Ask), f'Act askOne must request an Ask not {type(msg).__qualname__}'
                found_data = self.get(msg.data_type,ck_src=False,no_lock=True)
                if isinstance(found_data, Belief):
                    self.send(msg.source, Act.tell, found_data)
                    
            case 'askOneReply':
                assert isinstance(msg, Ask), f'Act askOneReply must request an Ask not {type(msg).__qualname__}'
                found_data = self.get(msg.data_type,ck_src=False,no_lock=True)
                if isinstance(found_data, Belief):
                    msg.reply_content = Belief(
                        found_data.name, found_data._values, 
                        self.my_name, found_data.adds_event)
                elif isinstance(found_data, Goal):
                    msg.reply_content = Goal(
                        found_data.name, found_data._values,self.my_name
                    )
                else:
                    msg.reply_content = None
                msg.reply_event.set()
                
            case 'askAll':
                assert isinstance(msg, Ask), f'Act askAll must request an Ask not {type(msg).__qualname__}'
                found_data = self.get(msg.data_type,all=True,ck_src=False,no_lock=True)
                assert isinstance(found_data, list)
                for data in found_data:
                    if isinstance(data, Belief | Goal):
                        self.send(msg.source, Act.tell, data)
                    
            case 'askAllReply':
                assert isinstance(msg, Ask), f'Act askAllReply must request an Ask not {type(msg).__qualname__}'
                found_data = self.get(msg.data_type,all=True,ck_src=False,no_lock=True)
                if isinstance(found_data, list):
                    content: List[Belief|Goal|Plan] = []
                    for data in found_data:
                        if isinstance(found_data, Belief):
                            content.append(Belief(
                                found_data.name, found_data._values, 
                                self.my_name, found_data.adds_event))
                        elif isinstance(found_data, Goal):
                            content.append(Goal(
                                found_data.name, found_data._values,self.my_name
                            ))
                    msg.reply_content = content
                else:
                    msg.reply_content = None
                msg.reply_event.set()
                    
            case 'tellHow':
                assert isinstance(msg, Plan), f'Act tellHow must receive a Plan not {type(msg).__qualname__}'
                self.add(msg, False, True)

            case 'untellHow':
                assert isinstance(msg, Plan), f'Act untellHow must receive a Plan not {type(msg).__qualname__}'
                self.add(msg, False, True)

            case 'askHow':
                assert isinstance(msg, Ask), f'Act askHow must request an Ask not {type(msg).__qualname__}'
                found_plans = self.get(Plan(Event(test,msg.data_type)),all=True,ck_chng=False,no_lock=True)
                assert isinstance(found_plans, list)
                for plan in found_plans:
                    assert isinstance(plan, Plan)
                    self.send(msg.source, Act.tellHow, plan)
            case _:
                TypeError(f"Unknown type of message {act}:{msg}")

    def _recieve_msgf(self, typ: str, msg: Belief | Goal | Plan | Ask | List[Belief | Goal | Plan]) -> None:
        """ 
        Alternative Method to Receive the Message (Without Proper KQML)

        Parameters
        ----------
            typ : str
                The type of message (add | forget | ask | askReply)
            msg : Belief | Goal | Plan | Ask | List[Belief | Goal | Ask | Plan]
                The message
        """
        match typ:
            case "add":
                assert not isinstance(msg, Ask)
                if isinstance(msg, List): assert self._is_type_iter(msg, Belief) or self._is_type_iter(msg, Goal) or self._is_type_iter(msg, Plan)
                self.add(msg, False)
                
            case "forget":
                assert not isinstance(msg, Ask)
                if isinstance(msg, List): assert self._is_type_iter(msg, Belief) or self._is_type_iter(msg, Goal) or self._is_type_iter(msg, Plan)
                self.rm(msg, False)
                
            case "ask":
                assert isinstance(msg, Ask), f'Act ask must request an Ask not {type(msg).__qualname__}'
                found_data = self.get(msg.data_type,ck_src=False,no_lock=True)
                if isinstance(found_data, Belief | Goal | Plan):
                    self.sendf(msg.source, found_data)
                    
            case 'askReply':
                assert isinstance(msg, Ask), f'Act askReply must request an Ask not {type(msg).__qualname__}'
                found_data = self.get(msg.data_type,ck_src=False,no_lock=True)
                if isinstance(found_data, Belief):
                    msg.reply_content = Belief(
                        found_data.name, found_data._values, 
                        self.my_name, found_data.adds_event)
                elif isinstance(found_data, Goal):
                    msg.reply_content = Goal(
                        found_data.name, found_data._values,self.my_name
                    )
                elif isinstance(found_data, Plan):
                    msg.reply_content = found_data
                else:
                    msg.reply_content = None
                msg.reply_event.set()
                
            case 'askAll':
                assert isinstance(msg, Ask), f'Act askAll must request an Ask not {type(msg).__qualname__}'
                found_data = self.get(msg.data_type,all=True,ck_src=False,no_lock=True)
                assert isinstance(found_data, list)
                for data in found_data:
                    if isinstance(data, Belief | Goal | Plan):
                        self.sendf(msg.source, data)
                    
            case 'askAllReply':
                assert isinstance(msg, Ask), f'Act askAllReply must request an Ask not {type(msg).__qualname__}'
                found_data = self.get(msg.data_type,all=True,ck_src=False,no_lock=True)
                if isinstance(found_data, list):
                    content: List[Belief|Goal|Plan] = []
                    for data in found_data:
                        if isinstance(found_data, Belief):
                            content.append(Belief(
                                found_data.name, found_data._values, 
                                self.my_name, found_data.adds_event))
                        elif isinstance(found_data, Goal):
                            content.append(Goal(
                                found_data.name, found_data._values,self.my_name
                            ))
                        elif isinstance(found_data, Plan):
                            content.append(found_data)
                    msg.reply_content = content
                else:
                    msg.reply_content = None
                msg.reply_event.set()
            case _:
                TypeError(f"Unknown type of message {typ}:{msg}")
    
    def list_agents(self, 
            agent_class: str | List[str], 
            cls_type: Optional[str] = None,
            cls_name: Optional[str] = None, 
        ) -> list[str] | None:
        """
        Finds other Agent(s) name(s) also connected to an Environment or Channel

        Parameters
        ---------
        agent_name : str or list or strs 
            The class agent or list containing the class name and instance name.
        cls_type : (str, optional) 
            The type of class to search in. Defaults to None.	
        cls_name : (str, optional)
            The name of the class to search in. Defaults to None.

        Returns
        -------
        Names : list of str
            A list of the names of the agents with the provided specifications.
        None: 
            When no agent with the specifications is found.
        """
        if isinstance(agent_class, str):
            agent_class = [agent_class]
            
        if isinstance(cls_type, str):
            cls_type = cls_type.lower()
            if cls_type in _type_env_set:
                cls_type = "environment"
            elif cls_type in _type_ch_set:
                cls_type = "channel"
            else:
                self.print(f"Unexpected environment or channel nomeclature: {cls_type}")
                return None  
        
        agents : list[Dict[Any, set[Any]]] = []
        for ag_cls in agent_class:
            if cls_type == "environment": 
                if cls_name is not None and cls_name in self._environments:
                    if ag_cls in self._environments[cls_name].agent_list :
                        agents.append(manual_deepcopy(self._environments[cls_name].agent_list)[ag_cls])
                else:
                    for env in self._environments.values():
                        if ag_cls in env.agent_list:
                            agents.append(manual_deepcopy(env.agent_list)[ag_cls])
                                    
            elif cls_type == "channel":   
                if cls_name is not None and cls_name in self._channels:
                    if ag_cls in self._channels[cls_name].agent_list:
                        agents.append(manual_deepcopy(self._channels[cls_name].agent_list)[ag_cls])
                else:
                    for ch in self._channels.values():
                        if ag_cls in ch.agent_list:
                            agents.append(manual_deepcopy(ch.agent_list)[ag_cls]) 
            else:
                if ag_cls in self._channels[DEFAULT_CHANNEL].agent_list:
                    agents.append(manual_deepcopy(self._channels[DEFAULT_CHANNEL].agent_list)[ag_cls])   
        list_of_agents = []
        for ag_dict in agents: 
            for ag_set in ag_dict.values():
                for ag in ag_set:
                    list_of_agents.append(ag)
        return list_of_agents    
    
    def action(self,env_name:str) -> Environment | None:
        """
        # Depreciated
        
        Aquires Instance of Environment with given Name

        Parameters
        ----------
        env_name : str
            Name of the wanted 

        """
        try:
            env = self._environments[env_name]
            return env
        except KeyError:
            self.print(f"Not Connected to Environment:{env_name}")
            return None

    def __getattr__(self, name):
        for instance in self._environments.values():
            if hasattr(instance, name):
                method = getattr(instance, name)
                def wrapper(*args, **kwargs):
                    try:
                        return method(self.my_name, *args, **kwargs) 
                    except TypeError as e:
                        if "object is not callable" not in str(e):
                            raise 
                return wrapper
        raise AttributeError(f"{self.my_name} doesnt have the method '{name}' and is not connected to any environment with the method '{name}'.")
    
    def start_cycle(self, start_flag: threading.Event | None = None) -> None:
        """Starts the Agent's Reasoning Cycle"""    
        self.running = True
        self.paused_agent = False
        self.stop_flag = threading.Event()
        self.thread = threading.Thread(target=self._cycle,args=(start_flag,self.stop_flag,))
        self.thread.start()
    
    def stop_cycle(self, log_flag=False) -> None:
        """Stops the Agent's Reasoning Cycle"""
        if self.running: 
            self.running = False
            if self.stop_flag is not None: self.stop_flag.set()
            self._plan_executor.shutdown(wait=False)
            #self.print("Stopping Reasoning")
            if self.logging: self.logger.debug("Ending Reasoning", extra=self.agent_info)
            
        
                 
    def _cycle(self, start_flag: threading.Event, stop_flag: threading.Event) -> None:
        """
        ## The main Reasoning Loop of the Agent
            1. Perception
            2. Mail
            3. Select Event
            4. Retrieve Plans
            5. Create Intention
            6. Select Intention
            7. Execute Intention
        """
        if start_flag is not None:
            start_flag.wait()
 
        self.cycle_counter = 1
        self.idle_counter = 0
        while not stop_flag.is_set():  
            if self.paused_agent:
                start_flag.wait()
            
            self._work_condition.wait(timeout=1.0)
            self._work_condition.clear()
            
            if stop_flag.is_set():
                break
            
            if self._environments:
                with self.update_lock: self._perception()
            if self.saved_msgs:
                with self.update_lock: self._mail()
            
            num_running_intentions = self.__running_intentions.__len__()
            while True: # loop until there are no more events
                self.curr_event, pending_flag = self._select_event()
                if self.curr_event is None: # if no events, there will be no new intention
                    break # no need to retrieve plans ou create an intention then
                self.relevant_plans = self._retrieve_plans(self.curr_event)
                if self.relevant_plans: # if there are relevant plans, check if any is applicable to create an intention
                    self._create_intention(self.relevant_plans, self.curr_event, pending_flag)
                    break
            
            intention = self._select_intention()
            
            if stop_flag.is_set():
                break
            
            self._execute_intention(intention, num_running_intentions)
            
            if self.delay > 0:
                self._delay()
            self.cycle_counter += 1
    
    def _notify_work(self):
        if not self._work_condition.is_set():
            self._work_condition.set()
    
    def _delay(self):
        """ 
        ### Delays the Agent's Reasoning Cycle
        Delay is normally set to 0
        
        Without this, an agent will hog the CPU and slow down the system
        
        With a sleep(0) [at least] the agent yields his thread to others
        """
        sleep(self.delay)

    def _execute_intention(self, intention: Intention | None, num_running_intentions: int) -> None:
        """ 
        ### Executes a given Intention (Plan, Trigger Event, Arguments)

        When the intention is None, if: 
            1. The number of running Intentions is less than the maximum number of concurrently running Intentions 
            2. There are available strategies
            3. Agent is set to auto_action
                The agent will try to execute a strategy
        
            If there are no strategies available, the agent will idle
        
        Parameters
        ----------
        intention : Intention
            The Intention to be executed
        num_running_intentions : int
            The number of currently running Intentions
        """
        if intention is None: 
            if num_running_intentions < self.max_intentions and self._strategies and self.auto_action:
                self.idle_counter = 0
                future = self._plan_executor.submit(self._execute_strategy)
            elif num_running_intentions > 0:
                self.idle_counter = 0
                if self.last_log != "Running Intention":
                    self.last_log = "Running Intention"
                    if self.logging: self.logger.debug("Running Intention", extra=self.agent_info)
            else:
                if self.last_log != "idle":
                    self.last_log = "idle"
                    if self.show_exec: self.print("Idle")
                    if self.logging: self.logger.debug("Idle", extra=self.agent_info)
                try:
                    self.idle_counter += 1
                    future = self._plan_executor.submit(self.on_idle)
                except Exception as e:
                    ...
        else:
            self.idle_counter = 0
            self.last_log = "Running Intention"
            self._execute_plan(intention)
            
    def _execute_strategy(self):
        """ 
        ### Executes a strategy
        
        The agent will try to execute the first available strategy
        """
        for strat in self._strategies:
            state, terminated = strat.get_state()
            if terminated:
                continue
            int_action = strat.get_action(state)
            env = self._environments[strat.env.my_name]
            str_action = strat.actions_list[int_action]
            action = strat.actions_dict[str_action]
            if self.show_exec: self.print(f"Executing Strategy {strat.name}({str_action})")
            if self.logging: self.logger.debug(f"Executing Strategy {strat.name}({str_action})", extra=self.agent_info)
            if not isinstance(str_action, str):
                str_action = str_action.original
            if len(action.data) == 1:
                action.func(env, self.my_name)
            else:
                action.func(env, self.my_name, str_action)
            break
    
    def _cycle_decision(self, 
                chosen_plan: Plan | None, trgr: Event | None, 
                args: tuple, last_message: str
        ):
        description: Any
        if chosen_plan is not None and trgr is not None:
            decision = "Execute Intention"
            description = self._format_data(decision,chosen_plan,trgr,args)
        elif len(self.__running_intentions) >= 1:
            decision = "Running Intention"
        elif self._strategies and self.auto_action:
            for strat in self._strategies:
                state, terminated = strat.get_state()
                if terminated:
                    continue
                int_action = strat.get_action(state)
                env = self._environments[strat.name]
                str_action = strat.actions_list[int_action]
                action = strat.actions_dict[str_action]
                if len(action.data) == 1:
                    action.func(env, self.my_name)
                else:
                    action.func(env, self.my_name, str_action)
                decision = "Execute Strategy"
                description = f'state: {state} action:{str_action}'
                break
            else:
                decision = "No Intention"
                description = self._format_data(decision,trgr=self.curr_event)
        else:
            decision = "No Intention"
            description = self._format_data(decision,trgr=self.curr_event)
        
        message = f"{decision}: {description}"
        if last_message != message:
            if self.logging: self.logger.debug(message, extra=self.agent_info)
            last_message = message
        return last_message
                
    def get_best_action(self, env_name: str, set_state: Any = None) -> tuple[Any, Callable] | None:
        """
        Executes the best trained Action on the given Environment, optionally on a given State
        
        Parameters
        ----------
            env_name : str
                The name of the Environment the Agent has a trained model for.
            set_state : (Any, optional)
                A given state for this Environment. Defaults to None.
                
        Returns
        -------
            action : Any or None
                The Action that was executed or None if no Action was executed
        """
        assert isinstance(env_name, str), f"best_action must receive string envrironment name not {type(env_name).__qualname__}"
        
        for strat in self._strategies:
            if strat.name not in {f"Model_{env_name}", f"Model_{self.my_name}_{env_name}"}:
                continue
            if set_state is not None:
                state = set_state
                int_action = strat.get_action(set_state)
            else:
                state, terminated = strat.get_state()
                
                if terminated:
                    continue
                int_action = strat.get_action(state)
                
            str_action = strat.actions_list[int_action]
            decision = "Execute Strategy"
            description = f'state: {state} action: {str_action}'
            if self.logging: self.logger.debug(f'{decision}: {description}', extra=self.agent_info)
            return str_action.original, strat.actions_dict[str_action].func
        
        if self.show_exec: self.print(f"No policy for Environment: {env_name}")
        if self.logging: self.logger.warning(f"No policy for Environment: {env_name}", extra=self.agent_info)
        return None
    
    def _perception(self) -> None:
        """ 
            Perceives all connected Environments and updates the agent's beliefs
        """
        percept_dict: Dict[str, dict] = dict()
        with self.env_lock:
            for env_name in self._environments:
                percepts = self._environments[env_name]._perception()
                percepts = self._apply_filters(percepts,env_name)
                merge_dicts(percepts,percept_dict)
        if percept_dict == {}:
            return
        self._env_changed_count = 0
        self._revision(percept_dict)
    
    def _apply_filters(self, percepts: Dict[str, Dict[str, Set[Percept]]], env_name: str):
        """ 
            Filters incoming percepts based on the agent's percept_filter
        """
        filtered_percepts: Dict[str, Dict[str, Set[Percept]]] = dict()
        focusing = True if len(self.percept_filter['focus']) > 0 else False
        for group, keys in percepts.items():
            #print(f'group: {group} keys: {keys} {self.percept_filter["focus"]}')
            if (focusing and group in self.percept_filter['focus']) or (not focusing and group not in self.percept_filter['ignore']):
                if env_name in filtered_percepts:
                    for key, value in keys.items():
                        filtered_percepts[env_name].setdefault(key, set()).update(value)
                else:
                    filtered_percepts[env_name] = keys
        #print(f'filtered_percepts: {filtered_percepts}')
        return filtered_percepts

    def perceive(self, env_name: str | List[str]) -> None:
        """
            Instantly Perceives the given Environment(s) and updates the agent's beliefs.
            
            Parameters
            ----------
            env_name : str or list of strs 
                The name(s) of the connected environment(s) to perceive.
                
                env_name also accepts "**all**" to perceive all connected environments.
        """
        if env_name == "all":
            self._perception()
            return
        
        percept_dict: Dict[str, dict] = dict()
        if isinstance(env_name, list):
            for name in env_name:
                try:
                    percepts = self._environments[name]._perception()
                    percepts = self._apply_filters(percepts,name)
                    if self.logging: self.logger.info(f"Perceiving {name} : {percepts}", extra=self.agent_info)
                    merge_dicts(percepts,percept_dict)
                except KeyError:
                    if self.show_exec: self.print(f"Not Connected to Environment:{name}")
                    if self.logging: self.logger.warning(f"Not Connected to Environment:{name}", extra=self.agent_info)
        else:
            try:
                percept_dict = self._environments[env_name]._perception()
                percept_dict = self._apply_filters(percept_dict,env_name)
                if self.logging: self.logger.info(f"Perceiving {env_name} : {percept_dict}", extra=self.agent_info)
            except KeyError:
                if self.show_exec: self.print(f"Not Connected to Environment:{env_name}")
                if self.logging: self.logger.warning(f"Not Connected to Environment:{env_name}", extra=self.agent_info)
        
        #belief_dict = self._percepts_to_beliefs_new(percept_dict)
        self._revision(percept_dict)
    
    def _percepts_to_beliefs(self,percepts: Dict[str, Dict[str, Set[Percept]]]) -> Dict[str, Dict[str, Set[Belief]]]:
        """ 
            Converts a dictionary of percepts to a dictionary of beliefs
        """
        beliefs: Dict[str, Dict[str, Set[Belief]]] = dict()
        for source, keys in percepts.items():
            beliefs[source] = dict()
            for key,percepts_set in keys.items():
                belief_set: Set[Belief] = set()
                for percept in percepts_set:
                    belief_set.add(Belief(percept.name,percept._values,source,percept.adds_event))
                beliefs[source][key] = belief_set
        return beliefs
    
    def _percepts_to_beliefs_new(self,percepts: Dict[str, Dict[str, Set[Percept]]]) -> Dict[str, Dict[str, Set[Belief]]]:
        beliefs: Dict[str, Dict[str, Set[Belief]]] = {
            source: {
                key: {Belief(percept.name, percept._values, source, percept.adds_event) for percept in percepts_set}
                for key, percepts_set in keys.items()
            }
            for source, keys in percepts.items()
        }
        return beliefs
                    
    def _revision(self, new_dict: Dict[str, Dict[str, Set[Percept]]]) -> None:
        """ 
            Revisions the agent's beliefs based on the new perceptions
        """
        for source, keys in self.__perceptions.copy().items():
            if source not in self._environments.keys() or isinstance(source, tuple):
                continue
            if source in new_dict:
                for key, beliefs in keys.copy().items():
                    if key in new_dict[source]: 
                        new_beliefs, gained_beliefs, lost_beliefs = set_changes(beliefs,new_dict[source][key])
                        self.__perceptions[source][key] = new_beliefs
                        self._new_event(gain, gained_beliefs) # Gained new specific belief
                        self._new_event(lose, lost_beliefs) # Lost an old specific belief
                        del new_dict[source][key]
                        if gained_beliefs:
                            if self.logging: self.logger.debug(f"Beliefs Gained: {source} Specific Beliefs gained in revision: {gained_beliefs}", extra=self.agent_info)
                        if lost_beliefs:
                            if self.logging: self.logger.debug(f"Beliefs Lost: {source} Specific Beliefs lost in revision: {lost_beliefs}", extra=self.agent_info)
                    else:
                        self._new_event(lose, self.__perceptions[source][key]) # Lost whole key belief
                        if self.logging: self.logger.debug(f"Beliefs Lost: {source} {key} Beliefs lost in revision: {self.__perceptions[source][key]}", extra=self.agent_info)
                        del self.__perceptions[source][key]
                        
                if new_dict[source] == {}:
                    del new_dict[source]
            else:
                for beliefs in keys.values():
                    if self.logging: self.logger.debug(f"Beliefs Lost: {source} Beliefs lost in revision: {beliefs}", extra=self.agent_info)
                    self._new_event(lose, beliefs) # Lost whole source of belief (env)
                del self.__perceptions[source]
        
        for source,keys in new_dict.items():
            for beliefs in keys.values():
                if self.logging: self.logger.debug(f"Beliefs Gained: Rest of {source} Beliefs gained in revision: {beliefs}", extra=self.agent_info)
                self._new_event(gain, beliefs) # Gained beliefs of new sources/keys
                
        merge_dicts(new_dict,self.__perceptions)
    
    def _select_event(self) -> tuple[Event, bool] | tuple[None, bool]:
        """ 
            Selects the next Event (FIFO) to be processed 
        """
        if self.__events == []:
            if self._pending_events != [] and self._pending_events[0][1] > self.cycle_counter:
                return self._pending_events.pop(0)[0], False
            else:
                return None, False
        else:
            return self.__events.pop(0), True
    
    def _instant_plan(self, event: Event):
        """ Executes the plan triggered by the event immediately """
        plans = self._retrieve_plans(event)
        if plans is None:
            if isinstance(event.data,Goal) and event.change.name == "gain":
                if self.logging:
                    self.logger.warning(f"Doesn't have Plan with {event} as trigger event", extra=self.agent_info)  
                else:
                    self.print(f"Doesn't have Plan with {event} as trigger event")
            elif isinstance(event.data,Belief):
                if self.logging:
                    self.logger.debug(f"Doesn't have Plan with {event} as trigger event", extra=self.agent_info)
                else:
                    self.print(f"Doesn't have Plan with {event} as trigger event")
            return
            
        args = None
        while plans:
            plan = plans.pop(0)
            args = self._retrieve_context(plan)
            if args is not None:
                break
            
        if args is not None:
            assert event.data is not None, f"{event} data is None"
            if event.data.v_len < 2:
                ev_args = event.data._values
            else:
                ev_args = (event.data._values,)
            if self.logging: self.logger.debug(f"Instant Plan: {self._format_data('Instant Plan',plan,event,ev_args+args)}", extra=self.agent_info)
            self._run_plan(Intention(plan,event,ev_args+args),True)
        elif type(event.data) is Goal and event.change.name == "gain":
            if self.logging: self.logger.warning(f"Doesnt have Plan with proper context for Event {event}", extra=self.agent_info)
        else:
            if self.logging: self.logger.debug(f"Doesnt have Plan with proper context for Event {event}", extra=self.agent_info)
    
    def _retrieve_plans(self, event: Event | None) -> List[Plan] | None: 
        """ Retrieves the plans that are triggered by the event """
        if event is None or event.data is None: 
            return None
        key = (event.change, type(event.data), event.data.name)
        retrieved = self._plan_index.get(key, None)
        if retrieved is None:
            return None
        applicable: List[Plan] = []
        for plan in retrieved:
            if self._compare_data(plan.trigger.data, event.data, True, True, False):
                applicable.append(plan)
        if applicable == []:
            return None
        return applicable
    
    def _create_intention(self, plans: List[Plan] | None, event: Event | None, pending_flag: bool):
        """ Creates an intention from the applicable plans that were triggered by the event """
        if plans is None or event is None:
            if event is not None and isinstance(event.data,Goal) and event.change.name == "gain":
                if self.logging:
                    self.logger.warning(f"Doesn't have Plan with {'' if pending_flag else 'Pending '}{event} as trigger event", extra=self.agent_info)  
                else:
                    self.print(f"Doesn't have Plan with {'' if pending_flag else 'Pending '}{event} as trigger event")
                if pending_flag:
                    self._pending_events.append((event,self.cycle_counter+PENDING_TIMER,"relevant"))
                else:
                    typ = event.data
                    self.__goals[typ.source][typ.name].remove(typ)
                    self._new_event(failure, event.data, instant=False)
            elif event is not None and isinstance(event.data,Belief):
                if self.logging: self.logger.debug(f"Doesn't have Plan for {event} as trigger event", extra=self.agent_info)
            return
        
        applicable_flag = True
        retrieved_plans = plans.copy()
        while retrieved_plans:
            plan = retrieved_plans.pop(0)
            ctxt = self._retrieve_context(plan)
            if ctxt is not None:
                applicable_flag = False
                assert event.data is not None, f"{event} data is None"
                aux = event.data._values
                ev_args = aux if isinstance(aux, tuple) and event.data.v_len < 2 else (aux,)
                
                if ctxt == ((),):
                    args = ev_args
                else:
                    if not isinstance(ctxt, tuple):
                        ctxt = (ctxt,)
                    args = ev_args+ctxt
                    
                #print(f'{event.data.name} : {args}[{len(args)}] = {event.data.values}[{event.data.v_len}] + {ctxt}[{len(ctxt)}]')    
                a = Intention(plan,event,args)
                self.__intentions.append(a)
                break
                
        if applicable_flag and event is not None and isinstance(event.data,Goal) and event.change.name == "gain":
            if self.logging:
                self.logger.warning(f"Doesnt have Plan with proper context for {'' if pending_flag else 'Pending '}Event {event}", extra=self.agent_info)  
            else:
                self.print(f"Doesnt have Plan with proper context for {'' if pending_flag else 'Pending '}Event {event}")
            
            if pending_flag:
                self._pending_events.append((event,self.cycle_counter+PENDING_TIMER,"applicable"))
            else:
                typ = event.data
                self.__goals[typ.source][typ.name].remove(typ)
                self._new_event(failure, event.data, instant=False)
    
    def _select_intention(self) -> Intention | None:    
        """ 
        Selects an intention from the list of intentions (FIFO)
        
        If the intention has the type of Plan 'atomic', then the max_intentions will be set to 1
        """
        try:
            if self.__running_intentions.__len__() < self.max_intentions:
                intention = self.__intentions.pop(0)
                if intention.plan.plan_type.name == 'atomic':
                    self.max_intentions = 1
                return intention
            else:
                return None
        except IndexError:
            if self.curr_event is not None and isinstance(self.curr_event.data,Goal) and self.curr_event.change.name == "gain":
                if self.logging:
                    if self.logging: self.logger.warning(f"Improper context for applicable plan(s) for {self.curr_event}", extra=self.agent_info)
                else:
                    if self.logging: self.logger.debug(f"Improper context for applicable plan(s) for {self.curr_event}", extra=self.agent_info)
            return None
    
    def _retrieve_context(self, plan: Plan) -> tuple | None:
        """ Checks if the Agents has appropriate Beliefs or Goals for the Plan's context """
        args: tuple = tuple()
        
        if isinstance(plan.context, Condition):
            if plan.context.c_type == "=":
                assert isinstance(plan.context.left_value, Belief | Goal), f"Unexpected Context Type: {type(plan.context.left_value)}, Expected Belief | Goal"
                ctxt = self.get(plan.context.left_value,ck_src=False)
                if not ctxt:
                    return None
                assert isinstance(ctxt, Belief | Goal), f"{self.my_name} > {plan.context.left_value} - Unexpected Context Type: {type(ctxt)}, Expected Belief | Goal"
                if ctxt.v_len == 1:
                    return ctxt._values
                else:
                    return (ctxt._values,)  
            else:
                if PRINT_CHECKS: self.print(f'Starting Check: {plan.context}')
                c_args,_ = self._check(plan.context)
                #print(f'{plan.body.__name__} - Context: {plan.context} - Context Args: {c_args}')
                if c_args and len(c_args) == 1:
                    return c_args[0]
                else:
                    return c_args
        else:
            return tuple()
    
    def _format_check(self, value: Belief | Goal | Condition, args: tuple, tupled: bool) -> tuple[tuple | None, bool, bool, bool]: 
        """ The checking proccess for if the Belief or Goal is present in the Agent's knowledge """
        f_value: tuple | Belief | Goal | bool | None
        v_args: bool
        if PRINT_CHECKS: self.print(f'Format Check: {value} :: {args} :: {tupled}')
        if isinstance(value, Condition) and not isinstance(value, Belief|Goal|Percept): 
            f_value, f_tupled = self._check(value, args, tupled)
            if f_value is None:
                return None, False, True, f_tupled
            v_args = True
        else: 
            f_tupled = tupled
            f_value = value
            v_args = False
        
        v_bool: bool = False
        v_data: tuple | Belief | Goal | Plan | Event | List[Belief | Goal | Plan | Event] | None
        if isinstance(f_value, Belief|Goal|Percept):
            v_data = self.get(f_value, ck_src=False)
            if v_data is not None and not isinstance(v_data, list | tuple | Plan | Event):
                v_bool = True
                v_data = cast(tuple, v_data._values)
            else:
                v_data = (None,)
            for v in f_value._values:
                if v is Any:
                    v_args = True
        elif isinstance(f_value, bool):
            v_data = f_value
            v_bool = f_value
        elif isinstance(f_value, Sequence) and not isinstance(f_value, str):
            v_data = f_value
            v_bool = True
        else:
            v_data = (f_value,)
            v_bool = True
        if isinstance(v_data, tuple) and len(v_data) == 1: 
            f_tupled = True 
        if PRINT_CHECKS: self.print(f'End of Format Check: {v_data} :: {v_bool} :: {v_args} :: {f_tupled}')
        return v_data, v_bool, v_args, f_tupled
    
    def _check(self, condition: Condition, args: tuple = tuple(), tupled: bool = False) -> tuple[tuple | None, bool]:
        """ Checks if the Condition is True """
        if PRINT_CHECKS: self.print(f'Checking Condition: {condition} - {type(condition.left_value)} - {args} - {tupled}')
        cnd_type = condition.c_type
        
        if cnd_type == "~":
            if isinstance(condition.left_value, Belief | Goal) and self.get(condition.left_value, ck_src=False) is None:
                return args, True
            elif isinstance(condition.left_value, Condition) and not isinstance(condition.left_value, Belief | Goal) and self._check(condition.left_value, args, tupled)[0] is None:
                return args, True
            else:
                return None, True
        
        assert condition.right_value is not None and condition.func is not None, f"Unexpected Condition: [ {condition} ]"
        
        v0_data, v0_bool, v0_args, v0_tupled = self._format_check(condition.left_value, args, tupled)
        v1_data, v1_bool, v1_args, v1_tupled = self._format_check(condition.right_value, args, tupled)
        if PRINT_CHECKS: self.print(f'After Format Check: {v0_data}:{v0_bool}:{v0_args}:{v0_tupled} {condition.str_type} {v1_data}:{v1_bool}:{v1_args}:{v1_tupled}')
        
        if v0_data is None and v1_data is None:
            return None, tupled
        if not v0_bool and not v1_bool:
            return None, tupled
        
        ret_bool = False    
        match cnd_type:
            case "op":
                ret_bool = condition.func(v0_bool, v1_bool)
            case "comp":
                assert v0_data is not None and v1_data is not None
                for v0, v1 in zip(v0_data,v1_data):
                    if v0 is None or v1 is None:
                        break
                    if not condition.func(v0, v1):
                        break
                else:
                    ret_bool = True
            case _:
                self.print(f"Unexpected condition: {cnd_type}")
        
        if not ret_bool:
            return None, tupled
        
        f_args: tuple = tuple()
        if v0_args and v0_data is not None:
            if not v0_tupled:
                f_args += (v0_data,)
            else:
                f_args += v0_data
        if v1_args and v1_data is not None:
            if not v1_tupled:
                f_args += (v1_data,)
            else:
                f_args += v1_data
        f_args += args
        
        if PRINT_CHECKS: self.print(f'End of Check: {f_args}')
        return f_args, True
    
    def _force_close_thread(self, thread: threading.Thread):
        """ 
        Forces the thread to close
        
        Used to kill executing Intentions as a last resort
        """
        thread_id = thread.ident
        assert isinstance(thread_id, int)
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread_id), ctypes.py_object(SystemExit))
        if res == 0:
            raise ValueError("Invalid thread ID")
        elif res > 1:
            ctypes.pythonapi.PyThreadState_SetAsyncExc(ctypes.c_long(thread_id), None)
            raise SystemError("Exception raise failed")
        self.print(f"Exception raised in thread {thread_id}")
        thread.join()
    
    def _execute_plan(self, intention: Intention):
        """ Starts the executes of a Intention's Plan in separate thread """
        if self.__running_intentions.__len__() >= self.max_intentions:
            self.__intentions.insert(0,intention)
            if self.logging:
                self.logger.debug(f"Intention {intention} not executed as max intentions reached", extra=self.agent_info) 
            else:
                self.print(f"Intention {intention} not executed as max intentions reached")
            return None
        try:
            self.__running_intentions.append(intention)
            if intention.plan.plan_type.name == "atomic":
                result = self._run_plan(intention)
            else:
                result = self._plan_executor.submit(self._run_plan, intention)
            
        except RunPlanError:
            if self.logging:
                self.logger.warning(f"Intention {intention} failed", extra=self.agent_info)
            else:
                self.print(f"Intention {intention} failed")

    def _run_plan(self, intention: Intention, instant_flag: bool = False):
        """ Where the actual execution of a Intention's Plan occurs """
        if self.logging: self.logger.debug(f"Executing Intention : {intention}", extra=self.agent_info)
        if self.show_exec or self.show_cycle: self.print(f"Executing Intention : {intention}")
        try:     
            assert intention.event.data is not None, f"{intention.event.data} data is None"
            result = intention.plan.body(self, intention.event.data.source, *intention.args)
                
            self.last_event = intention.event
            trigger_data = intention.event.data    
            if result == "Error" or result == -1:
                if self.logging:
                    self.logger.warning(f"Intention {intention} did not complete successfully", extra=self.agent_info)
                else:
                    self.print(f"Intention {intention} did not complete successfully, recreating Event {intention.event}")
            else:
                #print(f'Remove {(plan,trigger,args)} in {self.__intentions}',flush=True)
                #self.__intentions.remove((plan,trigger,args))
                if intention.plan.plan_type.name == 'atomic':
                    self.max_intentions = self.og_max_intentions
                if not instant_flag:
                    self.__running_intentions.remove(intention)
                    self.last_intention = intention

                if type(trigger_data) is Goal:
                    self.last_goal = trigger_data
                    if self.has(trigger_data) and result == False:
                        #self.__intentions.append((plan,trigger,args))
                        self._new_event(gain, trigger_data, instant=False)
                    elif self.has(trigger_data) and result != False:
                        self.rm(trigger_data)
                        self._new_event(success, trigger_data, instant=False)
                        if self.show_exec:
                            self.print(f"{intention} successfully cleared")
                        if self.logging: self.logger.info(f"{intention.event} cleared", extra=self.agent_info)
                    else:
                        if self.logging:
                            self.logger.warning(f"{trigger_data} already cleared by another plan's execution", extra=self.agent_info)
                        else:
                            self.print(f"{trigger_data} already cleared by another plan's execution")
            self.last_plan = intention.plan
            return result
        except Exception as e:
            buffer = ""
            _, _, exc_traceback = sys.exc_info()
            tb_entries = extract_tb(exc_traceback)
            
            #excluded_files = ['agent.py', 'communication.py', 'admin.py', 'environment.py']
            
            filtered_entries = [
                entry for entry in tb_entries 
                #if not any(excluded_file in entry.filename for excluded_file in excluded_files)
            ]
            
            if filtered_entries:
                buffer += "Filtered Traceback (most recent call last):"
                for entry in filtered_entries:
                    buffer +=f'\n\tFile "{entry.filename}", line {entry.lineno}, in {entry.name}, during cycle {self.cycle_counter}\n'
                    if entry.line:
                        buffer += f'\t\t{entry.line}'
                if "positional argument" in str(e):
                    buffer += f"\n\tCheck Plan '{intention.plan.body.__name__}' for self, src, and trigger/context args"
            else:
                buffer += " No matching traceback entries found."
            
            buffer += f"\n\n<{self.my_name}> Error while executing {intention}\n"
            if "is not a" in str(e):
                buffer += f"\tWhile creating a \033[1m{str(e).split('.')[0]}\033[0m: {repr(e)}\n"
            elif "is not hash" in str(e):
                buffer += f"\tWhile adding a \033[1m{str(e).split('.')[0]}\033[0m: {repr(e)}\n"
            else:      
                buffer += f"\t>>{repr(e)}\n"
            if "args" in str(e):
                buffer += f"\tThe \033[1margs\033[0m parameter in Belief/Goal/Percept was changed to \033[1mvalues\033[0m\n\tPlease replace <>.args to <>.values in your implementation" 
            print(buffer)
            self.logger.error(buffer, extra=self.agent_info)
            exit(-1) 
    
    def save_cycle_log(self, decision: str, description: Any | None = None, event: Event | None = None, plans: List[Plan] | None = None) -> None:
        log: Dict[str, Any] = {"cycle":self.cycle_counter}
        info = {
            "decision":decision,
            "description":description,
            "beliefs":self.belief_list.copy(),
            "goals":self.goal_list.copy(),
            "running_goal":self.last_goal,
            "last_recv":self.last_recv,
            "event":event,
            "last_event":self.last_event,
            "retrieved_plans":plans,
            "intentions":self.__intentions.copy(),
            "events":self.__events.copy(),
            "connected_envs":list(self._environments.keys()), 
            "connected_chs":list(self._channels.keys())
        }
        self.last_recv = []
        self.last_goal = None
        if self.last_log != info and (self.running or self.cycle_counter == 0):
            if self.running is False:
                log["cycle"] = "Setup"
            self.last_log = info
            log.update(info)
            sys_time = self.sys_time()
            if sys_time in self.cycle_log:
                self.cycle_log[sys_time].append(log)
            else:
                self.cycle_log[sys_time] = [log]
      
    def _format_data(self, decision: str, chosen_plan: Plan | None = None, trgr: Event | None = None, args: tuple | None = None, data_type: Iterable[Belief | Goal | Plan] | Belief | Goal | Plan | None = None, instant: bool | None = False) -> str:
        match decision:
            case "Adding Info" | "Removing Info" | "Testing Info":
                return f'{data_type}  -  instant[{instant}]'
            case "Execute Intention" | "Running Intention" | "Instant Plan":
                assert trgr is not None and trgr.data is not None
                return f' {chosen_plan}, source[{trgr.data.source}], args{args}'
            case "No Intention":
                return ""
            case "Sending Message":
                return ""
            
        return ""
    
    # TODO: should invalid arguments be an error or a warning?
    def _clean(
        self, data_type: Iterable[Belief | Goal] | Belief | Goal 
    ) -> Dict[Type[Belief | Goal], dict[str, Dict[str, Set[Belief | Goal]]]]:
        type_dicts: Dict[Type[Belief | Goal], dict] = {Belief: dict(), Goal: dict()}
        match data_type:
            case None:
                pass
            case Belief() | Goal():
                type_dicts[type(data_type)].update({data_type.source: {data_type.name: {data_type}}})
            case Iterable():
                for typ in data_type:
                    if not isinstance(typ, Belief) and not isinstance(typ, Goal):
                        raise InvalidBeliefError(
                            f"Expected data type to be Iterable[Belief | Goal] | Belief | Goal, recieved Iterable[{type(typ).__name__}]"
                        )
                    # Dict[ source, Dict[ key, Set[ Belief | Goal ]]]
                    type_dict: Dict[str | tuple[str,int], Dict[str, Set]] = type_dicts[type(typ)]
                    if typ.source in type_dict:
                        if typ.name in type_dict[typ.source]:
                            type_dict[typ.source][typ.name].add(typ)
                        else:
                            type_dict[typ.source].update({typ.name: {typ}})
                    else:
                        type_dict.update({typ.source: {typ.name: {typ}}})
            case _:
                raise InvalidBeliefError(
                    f"Expected data type to have be Iterable[Belief | Goal] | Belief | Goal, recieved {type(data_type).__name__}"
                )    
        return type_dicts
    
    def _clean_plans(
        self,
        plans: Optional[Iterable[Plan] | Plan],
    ) -> List[Plan]:
        match plans:
            case None:
                return []
            case Plan():
                return [plans]
            case Iterable():
                plan_list = []
                for plan in plans:
                    if isinstance(plan, Plan):
                        plan_list.append(plan)
                    if isinstance(plan,tuple):
                        plan_list.append(Plan(*plan))
                        
                return plan_list
            case _:
                raise InvalidPlanError(
                    f"Expected plans to have type Dict[str, Callable] | Iterable[Tuple[str, Callable]] | Tuple(str, Callable), recieved {type(plans).__name__}"
                )

