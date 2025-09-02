import threading
import ctypes
from logging import getLogger
from dataclasses import dataclass, field
from maspy.environment import Environment, Percept	
from maspy.communication import Channel, Act
from maspy.learning import EnvModel
from maspy.error import (
    InvalidBeliefError,
    InvalidPlanError,
    RunPlanError,
)
from maspy.utils import set_changes, merge_dicts, manual_deepcopy, bcolors, Condition
from typing import List, Optional, Dict, Set, Any, Union, Type, cast, _SpecialForm
from collections.abc import Iterable, Callable, Sequence
from collections import deque
from time import sleep
from enum import Enum
from importlib import import_module
from traceback import extract_tb
from contextlib import nullcontext
import inspect
import sys

Event_Change = Enum('gain | lose | test', ['gain', 'lose', 'test']) # type: ignore[misc]

gain = Event_Change.gain
lose = Event_Change.lose
test = Event_Change.test

Operation = Enum('add | rm', ['add', 'rm']) # type: ignore[misc]

add = Operation.add
rm = Operation.rm

Option = Enum('ignore | focus', ['ignore', 'focus']) # type: ignore[misc]

ignore = Option.ignore
focus = Option.focus

DEFAULT_SOURCE = "self"
DEFAULT_CHANNEL = "default"

@dataclass(eq=True, frozen=True)
class Belief(Condition):
    key: str = field(default_factory=str)
    _args: tuple | Any = field(default_factory=tuple)
    source: str = DEFAULT_SOURCE
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

    def weak_eq(self, other: "Belief"):
        return (
            self.key == other.key
            and len(self._args) == len(other._args)
            and self.source == other.source
        )

    def change(self, key: str|None = None, args: Any|None = None, source: str|None = None, adds_event: bool|None = None) -> None:
        frame = inspect.currentframe()
        caller_frame = frame.f_back if frame else None
        caller_locals = caller_frame.f_locals if caller_frame else None
        caller_instance = caller_locals.get('self', None) if caller_locals else None
        if isinstance(caller_instance, Agent):
            caller_instance.rm(self)
            new_belief = Belief(
                key if key is not None else self.key,
                args if args is not None else self._args,
                source if source is not None else self.source,
                adds_event if adds_event is not None else self.adds_event
            )
            caller_instance.add(new_belief)
        else:
            print(f"{type(caller_instance)}, not an Agent instance, trying to change {self}")

    def __hash__(self) -> int:
        args_tuple = tuple(
            arg if type(arg).__dict__.get("__hash__") else 
            repr(arg) if isinstance(arg, (List, Dict, Set, _SpecialForm)) else 
            TypeError(f"Unhashable type: {arg}:{type(arg)}")
            for arg in self._args
        )
        return hash((self.key, args_tuple, self.source))
    
    def __str__(self) -> str:
        s = f'Belief {self.key}({self.args})[{self.source}]'
        return s.replace("typing.Any","Any")
    
    def __repr__(self):
        return self.__str__()

@dataclass
class Goal(Condition):
    key: str = field(default_factory=str)
    _args: tuple | Any = field(default_factory=tuple)
    source: str = DEFAULT_SOURCE

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

    def weak_eq(self, other: "Goal"):
        return (
            self.key == other.key
            and len(self._args) == len(other._args)
            and self.source == other.source
        )

    def change(self, key: str|None = None, args: Any|None = None, source: str|None = None, adds_event: bool|None = None) -> None:
        frame = inspect.currentframe()
        caller_frame = frame.f_back if frame else None
        caller_locals = caller_frame.f_locals if caller_frame else None
        caller_instance = caller_locals.get('self', None) if caller_locals else None
        if isinstance(caller_instance, Agent):
            caller_instance.rm(self)
            new_belief = Belief(
                key if key is not None else self.key,
                args if args is not None else self._args,
                source if source is not None else self.source
            )
            caller_instance.add(new_belief)
        else:
            print(f"{type(caller_instance)}, not an Agent instance, trying to change {self}")

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
        args_tuple = tuple(args_hashable)

        return hash((self.key, args_tuple, self.source))
    
    def __str__(self) -> str:
        s = f"Goal {self.key}({self.args})[{self.source}]"
        return s.replace("typing.Any","Any")
    
    def __repr__(self):
        return self.__str__()
    
@dataclass
class Event:
    change: Event_Change = field(default_factory=lambda:gain)
    data: Belief | Goal | Percept = field(default_factory=Belief)
    
    def __str__(self) -> str:
        return f"{self.change.name} : {self.data}"
    
    def __repr__(self):
        return self.__str__()
    
@dataclass
class Plan:
    trigger: Event = field(default_factory=Event)
    context: List[tuple[bool, Belief | Goal]] | Condition = field(default_factory=list)
    body: Callable = lambda _: {}
    conditions: tuple[Callable[..., Any], ...] = (lambda _: {},)
    ev_ctrl: threading.Event = threading.Event()
    
    def __str__(self) -> str:
        return f"\n\tPlan:\n\ttrigger: {self.trigger},\n\tcontext: {self.context},\n\tbody: {self.body.__name__}()"
    
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
    data_type: Belief | Goal
    source: str = "unknown"
    reply_event: threading.Event = threading.Event()
    reply_content: Belief | Goal | List[Belief | Goal] | None = None 
    
    def __str__(self) -> str:
        return f"Ask( {self.data_type}, {self.source}, reply={self.reply_content} )"
    
    def __repr__(self):
        return self.__str__()

MSG = Belief | Ask | Goal | Plan | List[Belief | Ask | Goal | Plan]

_type_env_set = {Environment, "environment", "envrmnt", "env"}
_type_ch_set = {Channel, "channel", "chnnl", "ch", "c"}

def pl(change: Event_Change, data: Belief | Goal, context: Belief | Goal | List[Belief | Goal] | Condition = []):
    class decorator:
        def __init__(self,func):
            self.func = func
  
        def __set_name__(self, instance: Agent, name: str):
            if not isinstance(change, Event_Change) or not isinstance(data, Belief | Goal):
                raise TypeError

            context_condition: List[tuple[bool, Belief | Goal]] | Condition
            
            match context:
                case Condition() if not isinstance(context, Belief | Goal):
                    context_condition = context
                
                case Belief() | Goal():
                    context_condition = [(True,context)]
                
                case Iterable():
                    context_condition = []
                    for ctxt in context:
                        if isinstance(ctxt, Belief | Goal):
                            context_condition.append((True,ctxt))
                        elif isinstance(ctxt, tuple) and len(ctxt) == 2 and isinstance(ctxt[0], bool) and isinstance(ctxt[1], Belief | Goal):
                            context_condition.append(ctxt)
                        elif ctxt is False:
                            context_condition.append(context)
                            break
                        else:
                            raise Exception(f'Invalid type {type(ctxt)}:{ctxt} - was expecting Belief or Goal')
            
            event = Event(change,data)
            plan = Plan(event,context_condition,self.func)
            try:
                instance._plans += [plan]
            except AttributeError:
                instance._plans = [plan]
            
        def __call__(*args, **kwargs):
            print(f'{args} {kwargs}')
        
    return decorator

class Agent: 
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
        log_type = "Default",
        instant_mail = False,
        read_all_mail = False,
        nax_intentions = 1
    ):              
        self.show_exec: bool = show_exec
        self.show_cycle: bool = show_cycle
        self.show_prct: bool = show_prct
        self.show_slct: bool = show_slct
        self.log_type: str = log_type
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
        self.sys_time = Admin().sys_time
        self.logger = getLogger("maspy")
        self.delay: int|float = 0
        self.stop_flag: threading.Event | None = None
        self.running: bool = False
        self.thread: threading.Thread | None = None
        
        self.lock = threading.Lock()
        self.env_lock = threading.Lock()
        self.ch_lock = threading.Lock()
        self.update_lock = threading.Lock()
        self.intention_lock = threading.Lock()
        self.print_lock = threading.Lock()
        self.msg_lock = threading.Lock()
        self.reply_event: Dict[tuple, threading.Event] = {}
        
        self._ml_models: List = []
        self.policies: List = []
    
        self._environments: Dict[str, Environment] = dict()
        self._channels: Dict[str, Channel] = dict()
        self._dicts: Dict[str, Union[Dict[str, Environment], Dict[str, Channel]]] = {"environment":self._environments, "channel":self._channels}
        
        self._strategies: list[EnvModel] = []
        self.auto_action: bool = False

        self.max_intentions: int = nax_intentions
        self.last_intention: tuple[Plan, Event, tuple] = (Plan(), Event(), tuple())
        self.__intentions: list[tuple[Plan, Event, tuple]] = []
        self.__supended_intentions: deque[tuple[Plan, Event, tuple, str, Event | None]] = deque()
        self.__running_intentions: deque[tuple[Plan, Event, tuple]] = deque()
        
        self.__events: List[Event] = []
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
        self.last_sent: list[tuple[str, str | List[str], str, MSG]] = []
        self.last_recv: list[tuple[str, MSG]] = []
        self.last_plan: Plan | None = None
        self.aplc_plans: List[Plan] | None = None
        
        if beliefs:
            self.logger.debug(f"Adding Initial Beliefs: {beliefs}", extra=self.agent_info) if self.logging else ... 
            self.add(beliefs, False)
        if goals: 
            self.logger.debug(f"Adding Initial Goals: {goals}", extra=self.agent_info) if self.logging else ...
            self.add(goals, False)
        
        self._plans: List[Plan]
        try:    
            if not self._plans:
                self._plans = []
        except AttributeError:
            self._plans = []

        self.instant_mail = instant_mail
        self.read_all_mail = read_all_mail
        self.connect_to(Channel())
        self.paused_agent = False

    def start(self):
        from maspy.admin import Admin
        Admin().start_agents(self)
    
    def print(self,*args, **kwargs):
        if not self.printing:
            return
        f_args = "".join(map(str, args))
        f_kwargs = "".join(f"{key}={value}" for key, value in kwargs.items())
        name = self.my_name if not self.unique else self.tuple_name[0]
        with self.print_lock:
            return print(f"{self.tcolor}Agent:{name}> {f_args}{f_kwargs}{bcolors.ENDCOLOR}")
        
    @property
    def print_beliefs(self):
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
        buffer = "Goals:"
        for group_keys in self.__goals.values():
            for goal_set in group_keys.values():
                for goal in goal_set:
                    buffer += f'\n\t{goal}'
        self.print(buffer)
    
    @property
    def print_plans(self):
        buffer = "Plans:"
        for plan in self._plans:
            buffer += f'\n\t{plan}'
        self.print(buffer)
    
    @property
    def print_events(self):
        print("Events:",self.__events) 
    
    @property
    def print_intentions(self):
        buffer = "Running Intentions:"
        for plan, _ in self.__running_intentions:
            buffer += f"\n\t{plan}"
        self.print(buffer)
    
    @property
    def agent_info(self):
        return {
            "class_name": "Agent",
            "my_name": self.my_name if not self.unique else self.tuple_name[0],
            "cycle": self.cycle_counter,
            "curr_event": self.curr_event,
            "aplc_plans": self.aplc_plans,
            "running_intentions": list(self.__running_intentions.copy()),
            "num_intentions": self.__running_intentions.__len__(),
            #"last_recv": self.last_recv,
            #"last_sent": self.last_sent,
            "last_plan": self.last_plan,
            "last_event": self.last_event,   
            "intentions": list(self.__intentions.copy()),
            "events": self.__events.copy(),
            "saved_msgs": list(self.saved_msgs),
            "beliefs": self.belief_list,
            "perceptions": self.__perceptions,
            "goals": self.goal_list,
            "envs": list(self._environments.keys()), 
            "chs": list(self._channels.keys())
        }
    
    def filter_perceptions(self, operation: Operation, option: Option, group: str | list[str]):
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
                self.logger.warning(f"{g} not in {option_str} filter.", extra=self.agent_info) if self.logging else ...
    
    def connect_to(self, target: Environment | Channel | str) -> Environment | Channel | None:
        if isinstance(target, str):
            instance = Environment.get_instance(target) or Channel.get_instance(target)
            if instance:
                target = instance
                
        if isinstance(target, str):
            classes: List[tuple] = []
            try:
                imported = import_module(target)
            except ModuleNotFoundError:
                self.logger.error(f"No File named '{target}' found", extra=self.agent_info) if self.logging else ...
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
            case Channel():
                with self.ch_lock:
                    self._channels[target.my_name] = target
            case _:
                raise Exception(f'Invalid type {type(target)}:{target} - was expecting Channel or Environment')
        
        target.add_agents(self)
        return target

    def disconnect_from(self, target: Channel | Environment | str):
        if isinstance(target, str):
            instance = Environment.get_instance(target) or Channel.get_instance(target)
            if instance:
                target = instance
                
        match target:
            case Environment():
                with self.env_lock:
                    target._rm_agent(self)
                    del self._environments[target.my_name]
            case Channel():
                with self.ch_lock:
                    target._rm_agent(self)
                    del self._channels[target.my_name]
                
    def add_policy(self, policy: EnvModel):
        self.logger.info(f"Adding model for {policy.name}", extra=self.agent_info) if self.logging else ...
        self._strategies.append(policy)
        if policy.name not in self._environments.keys():
            self.connect_to(Environment(policy.name))
    
    def add_plan(self, plan: Plan | Iterable[Plan]):
        plans = self._clean_plans(plan)
        self._plans += plans

    def rm_plan(self, plan: Plan | Iterable[Plan]):
        if isinstance(plan, Iterable):
            for p in plan: 
                self._plans.remove(p)
        else:
            self._plans.remove(plan)
    
    def _new_event(self,change: Event_Change, data: Belief | Goal | Percept | Iterable[Belief | Goal| Percept], instant: bool = False):
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
                        
    def _check_event_supended(self,event: Event):
        for intention in self.__supended_intentions:
            if isinstance(intention[3],Event) and intention[3].change == event.change and self._compare_data(intention[3].data, event.data, True, True, False):
                intention[0].ev_ctrl.set()
    
    def _get_type_base(self, 
            data_type: Belief | Goal | Plan | Event | Type[Belief | Goal | Plan | Event]
        ) -> tuple[Dict[str, Dict[str, Set[Belief]]], Dict[str, Dict[str, Set[Percept]]]] | Dict[str, Dict[str, Set[Goal]]] | List[Plan] | List[Event] | None:
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
    
    def _check_caller(self):
        stack = inspect.stack(3)
        caller_frame = stack[2]
        caller_method = caller_frame.function

        if caller_method != "__init__" and caller_method in Agent.__dict__:
            return f"Called internally from {type(self).__name__}:{caller_method}"
        else:
            return f"Called externally from {type(self).__name__}:{caller_method}"
    
    def add(self, data_type: Belief | Goal | Iterable[Belief | Goal], instant: bool = False):
        #print(f"Add {data_type} | {self._check_caller()}")
        
        if self.running is False:
            instant = False
        self.logger.debug(f"Adding Info: {self._format_data("Adding Info", data_type=data_type,instant=instant)}", extra=self.agent_info) if self.logging else ...    
        # self.save_cycle_log("Adding Info", self._format_data("Adding Info", data_type=data_type,instant=instant))
        
        cleaned_data = self._clean(data_type)
        
        for type_data, data in cleaned_data.items():
            if len(data) == 0: 
                continue
            type_base = self._get_type_base(type_data)
            if isinstance(type_base,dict):
                merge_dicts(data,type_base)
            elif isinstance(type_base,tuple):
                merge_dicts(data,type_base[0])
            
            for src in data.values():
                for values in src.values():
                    for data_v in values:    
                        self.update_lists(data_v,"add")
                        
        self._new_event(gain,data_type,instant)
    
    def rm(self, data_type: Belief | Goal | Iterable[Belief | Goal], instant: bool = False):
        #print(f"Rm {data_type} | {self._check_caller()}")
        if self.running is False:
            instant = False
        self.logger.debug(f"Removing Info: {self._format_data("Removing Info", data_type=data_type,instant=instant)}", extra=self.agent_info) if self.logging else ...
        # self.save_cycle_log("Removing Info",self._format_data("Removing Info", data_type=data_type,instant=instant))  
        
        if not isinstance(data_type, Iterable): 
            data_type = [data_type]
            
        for typ in data_type:
            if isinstance(typ, Belief):
                self.__beliefs[typ.source][typ.key].remove(typ)
            elif isinstance(typ, Goal):
                self.__goals[typ.source][typ.key].remove(typ)
            else:
                self.logger.warning(f"Data_Type {typ} is neither Belief or Goal", extra=self.agent_info) if self.logging else ...
                self.print(f"Data_Type {typ} is neither Belief or Goal")
                
            self.update_lists(typ,"rm")
              
        self._new_event(lose,data_type,instant)

    def test(self, data_type: Belief | Goal, instant: bool = False):
        if self.running is False:
            instant = False
        self.logger.debug(f"Testing Info: {self._format_data("Testing Info", data_type=data_type,instant=instant)}", extra=self.agent_info) if self.logging else ...    
        # self.save_cycle_log("Testing Info",self._format_data("Testing Info", data_type=data_type,instant=instant)) 
        self._new_event(test,data_type,instant)
    
    def has(self, data_type: Belief | Goal | Plan | Event) -> bool:
        return self.get(data_type) is not None

    def get(self, data_type: Belief | Goal | Plan | Event | Type[Belief | Goal | Plan | Event],
        search_with:  Optional[Belief | Goal | Plan | Event] = None,
        all = False, ck_chng=True, ck_type=True, ck_args=True, ck_src=True, no_lock=False
    ) -> Belief | Goal | Plan | Event | List[Belief | Goal | Plan | Event] | None:
        if isinstance(data_type, type): 
            data_type = data_type()
        type_base = self._get_type_base(data_type)

        if type_base is None:
            return None
        if search_with is None: 
            search_with = data_type

        change, data = self._to_belief_goal(search_with)
        
        lock = nullcontext() if no_lock else self.update_lock
        found_data: List[Belief | Goal | Plan | Event] = []
        match data_type:
            case Belief() | Goal() | Percept():  
                if isinstance(type_base, tuple):
                    for base in type_base:
                        with self.lock:
                            found = self._search(base, data, ck_type, ck_args, ck_src, all)
                        if all:
                            found_data.extend(found)
                        if not all and found:
                            return found
                elif isinstance(type_base, dict):
                    with lock:
                        found = self._search(type_base, data, ck_type, ck_args, ck_src, all)
                    if all:
                        found_data.extend(found)
                    if not all and found:
                        return found            
            case Plan() | Event(): 
                for plan_event in type_base:
                    assert isinstance(plan_event, Plan | Event)
                    chng, belf_goal = self._to_belief_goal(plan_event)
                    
                    if change and ck_chng and chng != change:
                        continue
                    if self._compare_data(belf_goal,data,ck_type,ck_args,ck_src):
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
            if caller_function_name in {'_retrieve_plans','recieve_msg','_retrieve_context','_select_plan','has','_check', '_format_check'}:
                return None
            if data_type == search_with:
                self.print(f'Does not contain {type(data_type).__qualname__} like {data_type}. Searched during {caller_function_name}()')
            else:
                self.print(f'Does not contain {type(data_type).__qualname__} like {search_with}. Searched during {caller_function_name}()')
            return None
    
    def _search(self, type_base: Dict[str, Dict[str, Set[Belief]]] | Dict[str, Dict[str, Set[Percept]]] | Dict[str, Dict[str, Set[Goal]]], data, ck_type, ck_args, ck_src, all):
        found = []
        for keys in type_base.values():
            for values in keys.values():
                for value in values:
                    if isinstance(value, Percept):
                        value = Belief(value.key, value.args, value.source, value.adds_event)
                    if self._compare_data(value,data,ck_type,ck_args,ck_src):
                        found.append(value)
                        if not all: 
                            return value  
        return found
         
    def wait(self, timeout: Optional[float] = None, event: Optional[Event] = None):
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
            
            intention: tuple[Plan, Event, tuple]
            
            for run_int in self.__running_intentions:
                if run_int[0].body.__name__ == plan_function_name:
                    intention = run_int
                    break
            else:
                self.print(f"Plan {plan_function_name} not found")
                return
        else:
            return
        
        intention_reason = intention + (reason, event)
        
        self.__running_intentions.remove(intention)
        self.__supended_intentions.append(intention_reason)
        
        intention[0].ev_ctrl.wait(timeout)
        
        self.__supended_intentions.remove(intention_reason)
        
        while self.__running_intentions.__len__() > self.max_intentions:
            sleep(0.01)

        self.__running_intentions.append(intention)
    
    def drop_all_desires(self):
        self.drop_all_events()
        self.drop_all_intentions()
    
    def drop_all_events(self):
        self.__events = []
    
    def drop_all_intentions(self):
        self.__intentions = []
        for suspended_intention in self.__supended_intentions:
            self._force_close_thread(suspended_intention[1])
        self.__supended_intentions = []
    
    def drop_desire(self, data_type: Belief | Goal):
        self.drop_event(data_type)
        self.drop_intention(data_type)
        
    def drop_event(self, data_type: Belief | Goal):
        for event in self.__events:
            if self._compare_data(event.data, data_type, ck_type=True, ck_args=True, ck_src=False):
                self.__events.remove(event)
    
    def drop_intention(self, data_type: Belief | Goal):         
        for intention in self.__intentions:
            if self._compare_data(intention[0].trigger.data, data_type, ck_type=True, ck_args=True, ck_src=False): 
                self.__intentions.remove(intention)

    def _get_running_intentions(self):
        return self.__running_intentions
    
    def _to_belief_goal(self, data_type: Belief | Goal | Plan | Event):
        change: Optional[str | Event_Change] = None
        belief_goal: Optional[Belief | Goal] = None
        match data_type:
            case Belief() | Goal():
                belief_goal = data_type
            case Plan(): 
                event_dt = data_type.trigger.data
                if isinstance(event_dt, Percept):
                    event_dt = Belief(event_dt.key, event_dt.args, event_dt.source)
                change = data_type.trigger.change
                belief_goal = event_dt
            case Event(): 
                event_dt = data_type.data
                if isinstance(event_dt, Percept):
                    event_dt = Belief(event_dt.key, event_dt.args, event_dt.source)
                change = data_type.change
                belief_goal = event_dt
            case _: 
                self.print(f"Error in _to_belief_goal: {type(data_type)}:{data_type}")
                return None, None
        return change,belief_goal
    
    def _compare_data(self, data1: Belief | Goal | Percept, data2: Belief | Goal | Percept, ck_type: bool, ck_args: bool, ck_src: bool):
        buffer = f"Comparing: {data1}  &  {data2}"
        if ck_type and type(data1) is not type(data2):
            self.print(f"{buffer} >> Different type") if self.show_slct else ...
            return False
        if data1.key != data2.key:
            self.print(f"{buffer} >> Different key") if self.show_slct else ...
            return False
        if ck_src and data2.source != DEFAULT_SOURCE and data1.source != data2.source:
            self.print(f"{buffer} >> Different source") if self.show_slct else ...
            return False
        if not ck_args:
            return True
        if data1.args_len != data2.args_len:
            self.print(f"{buffer} >> Different args length") if self.show_slct else ...
            return False
        for arg1,arg2 in zip(data1._args,data2._args):
            if arg1 is Any or arg2 is Any or arg1 == arg2:
                continue
            else:
                self.print(f"{buffer} >> Different args {arg1} x {arg2}") if self.show_slct else ...
                return False
        else:
            self.print(f"{buffer} >> Compatible") if self.show_slct else ...
            return True
                    
    def send(self, target: str | List[str], msg_act: Act, msg: MSG, channel: str = DEFAULT_CHANNEL) -> None | Belief | Goal | Iterable[Belief | Goal]:   
        self.last_sent = []
        #self.print(f"Sending {msg_act.name} to {target} on {channel} [{self._check_caller()}]")
        
        if type(target) is str and not target.split("_")[-1].isdigit():
            target = f"{target}_1"
        try:
            if msg_act.name in ['askOneReply','askAllReply']:
                with self.lock: # Dont remember why this lock is needed
                    assert isinstance(msg, Belief | Goal)
                    msg = Ask(msg, self.my_name)
                    
                #self._channels[channel]._send(self.my_name,target,msg_act,msg)
                msg.reply_event.clear()
                send_thread = threading.Thread(target=self._channels[channel]._send,args=(self.my_name,target,msg_act,msg))
                send_thread.start()
                self.last_sent.append((self.my_name,target,msg_act.name,msg))
                was_set = msg.reply_event.wait(timeout=2)
                
                if msg.reply_content is not None:
                    self.add(msg.reply_content, False)
                    self.logger.info(f'Reply for {msg} from {target}', extra=self.agent_info) if self.logging else ...
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
                #self._channels[channel]._send(self.my_name,target,msg_act,msg)
                send_thread = threading.Thread(target=self._channels[channel]._send,args=(self.my_name,target,msg_act,msg))
                send_thread.start()
                self.last_sent.append((self.my_name,target,msg_act.name,msg))
            
            ch = "in the default channel"
            if channel != DEFAULT_CHANNEL:
                ch = f"in the channel {channel}"
            if isinstance(target,str | list): 
                self.logger.debug(f'Send Message: {self.my_name}  to  {target}  -  {msg_act.name} {msg} {ch}', extra=self.agent_info) if self.logging else ...
                # self.save_cycle_log("Send Message", f' {self.my_name}  to  {target}  -  {msg_act.name} {msg}{ch}')
            else:
                self.logger.debug(f'Send Message: {self.my_name}  broadcasting  {msg_act.name} {msg} {ch}', extra=self.agent_info) if self.logging else ...
                # self.save_cycle_log("Send Message", f' {self.my_name}  broadcasting  {msg_act.name} {msg}{ch}')
        except KeyError:
            self.logger.warning(f'Agent:{self.my_name} Not Connected to Selected Channel:{channel}', extra=self.agent_info) if self.logging else ...
        except AssertionError:
            raise
        return None
    
    def save_msg(self, act: Act, msg: MSG) -> None:
        if self.instant_mail: 
            try:
                self.recieve_msg(act,msg)
            except AssertionError:
                raise
        else:
            #with self.msg_lock:
            self.logger.info(f'Saving Message to Mail: {msg}', extra=self.agent_info) if self.logging else ...
            self.saved_msgs.append((act,msg))

    def _mail(self, selection_function: Callable | None = None) -> None:
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
                act,msg = mail.pop(0)
                try:
                    self.last_recv.append((act.name,msg))    
                    
                    self.logger.debug(f'Receiving Message: {msg}', extra=self.agent_info) if self.logging else ...
                    
                    self.recieve_msg(act,msg)
                except AssertionError as ae:
                    print(f"\t{repr(ae)}")
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    last_frame = extract_tb(exc_traceback)[-1]
        
                    formatted_last_frame = f"File \"{last_frame.filename}\", line {last_frame.lineno}, in {last_frame.name}\n  {last_frame.line}"
                    
                    print("Error originated from:")
                    print(formatted_last_frame)

    def recieve_msg(self, act: Act, msg: MSG) -> None:
        match act.name:
            case 'tell':
                assert isinstance(msg, Belief),f'Act tell must receive Belief not {type(msg).__qualname__}'
                self.add(msg, False)
                
            case 'achieve':
                assert isinstance(msg, Goal),f'Act achieve must receive Goal not {type(msg).__qualname__}'
                self.add(msg, False)
                
            case 'untell':
                assert isinstance(msg, Belief),f'Act untell must receive Belief not {type(msg).__qualname__}'
                self.rm(msg, False)
                
            case 'unachieve':
                assert isinstance(msg, Goal),f'Act unachieve must receive Goal not {type(msg).__qualname__}'
                self.rm(msg, False)
                
            case 'askOne':
                assert isinstance(msg, Ask), f'Act askOne must request an Ask not {type(msg).__qualname__}'
                found_data = self.get(msg.data_type,ck_src=False)
                if isinstance(found_data, Belief):
                    self.send(msg.source, Act.tell, found_data)
                    
            case 'askOneReply':
                assert isinstance(msg, Ask), f'Act askOneReply must request an Ask not {type(msg).__qualname__}'
                found_data = self.get(msg.data_type,ck_src=False,no_lock=True)
                if isinstance(found_data, Belief):
                    msg.reply_content = Belief(
                        found_data.key, found_data.args, 
                        self.my_name, found_data.adds_event)
                elif isinstance(found_data, Goal):
                    msg.reply_content = Goal(
                        found_data.key, found_data.args,self.my_name
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
                    content: List[Belief|Goal] = []
                    for data in found_data:
                        if isinstance(found_data, Belief):
                            content.append(Belief(
                                found_data.key, found_data.args, 
                                self.my_name, found_data.adds_event))
                        elif isinstance(found_data, Goal):
                            content.append(Goal(
                                found_data.key, found_data.args,self.my_name
                            ))
                    msg.reply_content = content
                else:
                    msg.reply_content = None
                msg.reply_event.set()
                    
            case 'tellHow':
                assert isinstance(msg, Plan), f'Act tellHow must receive a Plan not {type(msg).__qualname__}'
                self.add_plan(msg)

            case 'untellHow':
                assert isinstance(msg, Plan), f'Act untellHow must receive a Plan not {type(msg).__qualname__}'
                self.rm_plan(msg)

            case 'askHow':
                assert isinstance(msg, Ask), f'Act askHow must request an Ask not {type(msg).__qualname__}'
                found_plans = self.get(Plan(Event(test,msg.data_type)),all=True,ck_chng=False,no_lock=True)
                assert isinstance(found_plans, list)
                for plan in found_plans:
                    assert isinstance(plan, Plan)
                    self.send(msg.source, Act.tellHow, plan)
            case _:
                TypeError(f"Unknown type of message {act}:{msg}")
    
    def list_agents(self, 
            agent_class: str | List[str], 
            cls_type: Optional[str] = None,
            cls_name: Optional[str] = None, 
        ) -> list[str] | None:
        
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
    
    def reasoning(self, start_flag: threading.Event | None = None) -> None:    
        self.running = True
        self.stop_flag = threading.Event()
        self.thread = threading.Thread(target=self.cycle,args=(start_flag,self.stop_flag,))
        self.thread.start()
    
    def stop_cycle(self, log_flag=False) -> None:
        self.running = False
        self.logger.debug("Ending Reasoning", extra=self.agent_info) if self.logging else ...
        # self.save_cycle_log(decision="End of Reasoning")
        if self.stop_flag is not None:
            self.stop_flag.set()
        self.paused_agent = True
        #sys.exit()
                 
    def cycle(self, start_flag: threading.Event, stop_flag: threading.Event) -> None:
        if start_flag is not None:
            start_flag.wait()
 
        self.cycle_counter = 1
        while not stop_flag.is_set():  
            if self.paused_agent:
                start_flag.wait()
                
            with self.update_lock:
                self._perception()
                self._mail()
            
            num_running_intentions = self.__running_intentions.__len__()
            self.curr_event = self._select_event()
            self.aplc_plans = self._retrieve_plans(self.curr_event)
            chosen_plan, trgr, args = self._select_intention(self.aplc_plans,self.curr_event)
            
            if stop_flag.is_set():
                break
            
            if not (chosen_plan and trgr): 
                if num_running_intentions < self.max_intentions and self._strategies and self.auto_action:
                    self._execute_strategy()
                elif num_running_intentions > 0:
                    if self.last_log != "Running Intention":
                        self.last_log = "Running Intention"
                        self.logger.debug("Running Intention", extra=self.agent_info) if self.logging else ...
                else:
                    if self.last_log != "idle":
                        self.last_log = "idle"
                        self.logger.debug("Idle", extra=self.agent_info) if self.logging else ...
                    try:
                        self.on_idle()
                    except Exception as e:
                        ...
            else:   
                self._execute_plan(chosen_plan, trgr, args)
            
            self._delay()
            self.cycle_counter += 1
    
    def _delay(self):
        sleep(self.delay)

    def _execute_strategy(self):
        for strat in self._strategies:
            state, terminated = strat.get_state()
            if terminated:
                continue
            int_action = strat.get_action(state)
            env = self._environments[strat.name]
            str_action = strat.actions_list[int_action]
            action = strat.actions_dict[str_action]
            self.logger.debug(f"Executing Strategy {strat.name}({str_action})", extra=self.agent_info) if self.logging else ...
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
            description = self._format_data(decision,*self.__running_intentions[0])
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
            self.logger.debug(message, extra=self.agent_info) if self.logging else ...
            last_message = message
        return last_message
                
    def best_action(self, env_name: str, set_state: Any = None) -> None:
        assert isinstance(env_name, str), f"best_action must receive string envrironment name not {type(env_name).__qualname__}"
        
        for strat in self._strategies:
            if strat.name != env_name:
                continue
            if set_state is not None:
                state = set_state
                int_action = strat.get_action(set_state)
            else:
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
                action.func(env, self.my_name, str_action.original)
            decision = "Execute Strategy"
            description = f'state: {state} action: {str_action}'
            self.logger.debug(f'{decision}: {description}', extra=self.agent_info) if self.logging else ...
            # self.save_cycle_log(decision, description)
            break
        else:
            self.logger.warning(f"No policy for Environment: {env_name}", extra=self.agent_info) if self.logging else ...
    
    def _perception(self) -> None:
        percept_dict: Dict[str, dict] = dict()
        with self.env_lock:
            for env_name in self._environments:
                percepts = self._environments[env_name].perception()
                percepts = self._apply_filters(percepts,env_name)
                #self.logger.debug(f"Percepting {env_name} : {percepts}", extra=self.agent_info) if self.logging else ...
                merge_dicts(percepts,percept_dict)
        if percept_dict == {}:
            return
        #belief_dict: Dict[str, Dict[str, Set[Belief]]] = self._percepts_to_beliefs_new(percept_dict)
        self._revision(percept_dict)
    
    def _apply_filters(self, percepts: Dict[str, Dict[str, Set[Percept]]], env_name: str):
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
        if env_name == "all":
            self._perception()
            return
        
        percept_dict: Dict[str, dict] = dict()
        if isinstance(env_name, list):
            for name in env_name:
                try:
                    percepts = self._environments[name].perception()
                    percepts = self._apply_filters(percepts,name)
                    self.logger.info(f"Perceiving {name} : {percepts}", extra=self.agent_info) if self.logging else ...
                    merge_dicts(percepts,percept_dict)
                except KeyError:
                    self.logger.warning(f"Not Connected to Environment:{name}", extra=self.agent_info) if self.logging else ...
        else:
            try:
                percept_dict = self._environments[env_name].perception()
                percept_dict = self._apply_filters(percept_dict,env_name)
                self.logger.info(f"Perceiving {env_name} : {percept_dict}", extra=self.agent_info) if self.logging else ...
            except KeyError:
                self.logger.warning(f"Not Connected to Environment:{env_name}", extra=self.agent_info) if self.logging else ...
        
        #belief_dict = self._percepts_to_beliefs_new(percept_dict)
        self._revision(percept_dict)
    
    def _percepts_to_beliefs(self,percepts: Dict[str, Dict[str, Set[Percept]]]) -> Dict[str, Dict[str, Set[Belief]]]:
        beliefs: Dict[str, Dict[str, Set[Belief]]] = dict()
        for source, keys in percepts.items():
            beliefs[source] = dict()
            for key,percepts_set in keys.items():
                belief_set: Set[Belief] = set()
                for percept in percepts_set:
                    belief_set.add(Belief(percept.key,percept.args,source,percept.adds_event))
                beliefs[source][key] = belief_set
        return beliefs
    
    def _percepts_to_beliefs_new(self,percepts: Dict[str, Dict[str, Set[Percept]]]) -> Dict[str, Dict[str, Set[Belief]]]:
        beliefs: Dict[str, Dict[str, Set[Belief]]] = {
            source: {
                key: {Belief(percept.key, percept.args, source, percept.adds_event) for percept in percepts_set}
                for key, percepts_set in keys.items()
            }
            for source, keys in percepts.items()
        }
        return beliefs
                    
    def _revision(self, new_dict: Dict[str, Dict[str, Set[Percept]]]) -> None:
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
                            self.logger.debug(f"Beliefs Gained: {source} Specific Beliefs gained in revision: {gained_beliefs}", extra=self.agent_info) if self.logging else ...
                        if lost_beliefs:
                            self.logger.debug(f"Beliefs Lost: {source} Specific Beliefs lost in revision: {lost_beliefs}", extra=self.agent_info) if self.logging else ...
                    else:
                        self._new_event(lose, self.__perceptions[source][key]) # Lost whole key belief
                        self.logger.debug(f"Beliefs Lost: {source} Beliefs lost in revision: {self.__perceptions[source][key]}", extra=self.agent_info) if self.logging else ...
                        del self.__perceptions[source][key]
                        
                if new_dict[source] == {}:
                    del new_dict[source]
            else:
                for beliefs in keys.values():
                    self.logger.debug(f"Beliefs Lost: {source} Beliefs lost in revision: {beliefs}", extra=self.agent_info) if self.logging else ...
                    self._new_event(lose, beliefs) # Lost whole source of belief (env)
                del self.__perceptions[source]
        
        for source,keys in new_dict.items():
            for beliefs in keys.values():
                self.logger.debug(f"Beliefs Gained: Rest of {source} Beliefs gained in revision: {beliefs}", extra=self.agent_info) if self.logging else ...
                # self.save_cycle_log("Beliefs Gained", f"Rest of {source} Beliefs gained in revision: {beliefs}")
                self._new_event(gain, beliefs) # Gained beliefs of new sources/keys
                
        merge_dicts(new_dict,self.__perceptions)
    
    def _select_event(self) -> Event | None:
        if self.__events == []: 
            return None 
        event = self.__events.pop(0)
        return event
    
    def _instant_plan(self, event: Event):
        plans = self._retrieve_plans(event)
        if plans is None:
            if event is not None and isinstance(event.data,Goal) and event.change.name == "gain":
                if self.logging:
                    self.logger.warning(f"Found no applicable plan for {event}", extra=self.agent_info)  
                else:
                    print(f"[WARNING] Found no applicable plan for {event}")
            elif event is not None and isinstance(event.data,Belief):
                if self.logging:
                    self.logger.debug(f"Found no applicable plan for {event}", extra=self.agent_info)
                else:
                    print(f"[DEBUG] Found no applicable plan for {event}")
            return
            
        args = None
        while plans:
            plan = plans.pop(0)
            args = self._retrieve_context(plan)
            if args is not None:
                break
            
        if args is not None:
            if event.data.args_len < 2:
                ev_args = event.data._args
            else:
                ev_args = (event.data._args,)
            self.logger.debug(f"Instant Plan: {self._format_data('Instant Plan',plan,event,ev_args+args)}", extra=self.agent_info) if self.logging else ...
            # self.save_cycle_log("Instant Plan", self._format_data("Instant Plan",plan,event,ev_args+args),event,plans)
            self._run_plan(plan,event,ev_args+args,True)
        elif type(event.data) is Goal and event.change.name == "gain":
            self.logger.warning(f"Improper context for applicable plan(s) with {event}", extra=self.agent_info) if self.logging else ...
        else:
            self.logger.debug(f"Improper context for applicable plan(s) with {event}", extra=self.agent_info) if self.logging else ...
    
    def _retrieve_plans(self, event: Event | None) -> List[Plan] | None: 
        if event is None: 
            return None
        retrieved = self.get(Plan,event,all=True,ck_src=False)
        assert isinstance(retrieved, list | None), f"Unexpected Retrieved Plan: {type(retrieved)}, Expected List[Plan] | None"
        return cast(List[Plan] | None, retrieved) 
    
    def _select_intention(self, plans: List[Plan] | None, event: Event | None) -> tuple[Plan, Event, tuple] | tuple[None, None, tuple]:
        if plans is None:
            if event is not None and isinstance(event.data,Goal) and event.change.name == "gain":
                if self.logging:
                    self.logger.warning(f"Found no applicable plan for {event}", extra=self.agent_info)  
                else:
                    print(f"[WARNING] Agent {self.my_name} found no applicable plan for {event}")
            elif event is not None and isinstance(event.data,Belief):
                self.logger.debug(f"Found no applicable plan for {event}", extra=self.agent_info) if self.logging else ...
            try:
                plan, trigger, args = self.__intentions.pop(0)
                return plan, trigger, args
            except IndexError:
                return None, None, tuple()
        if event is None:
            return None, None, tuple()
        retrieved_plans = plans.copy()
        while retrieved_plans:
            plan = retrieved_plans.pop(0)
            ctxt = self._retrieve_context(plan)
            if ctxt is None and event is not None and isinstance(event.data,Goal) and event.change.name == "gain":
                if self.logging:
                    self.logger.warning(f"Found no available context for {plan}", extra=self.agent_info)  
                else:
                    print(f"[WARNING] Agent {self.my_name} found no available context for {plan}")
            if ctxt is not None and event is not None:
                if event.data.args_len < 2:
                    ev_args = event.data._args
                else:
                    ev_args = (event.data._args,)
                
                if ctxt == ((),):
                    args = ev_args
                else:
                    args = ev_args+ctxt
                    
                #self.print(f'{args}[{len(args)}] - {event.data._args}[{event.data.args_len}] - {ctxt}[{len(ctxt)}]')    
                self.__intentions.append((plan,event,args))
        try:
            if self.__running_intentions.__len__() < self.max_intentions:
                plan, trigger, args = self.__intentions.pop(0)
                return plan, trigger, args
            else:
                return None, None, tuple()
        except IndexError:
            if isinstance(event.data,Goal) and event.change.name == "gain":
                self.logger.warning(f"Improper context for applicable plan(s) for {event}", extra=self.agent_info) if self.logging else ...
            else:
                self.logger.debug(f"Improper context for applicable plan(s) for {event}", extra=self.agent_info) if self.logging else ...
            return None, None, tuple()
    
    def _retrieve_context(self, plan: Plan) -> tuple | None:
        args: tuple = tuple()
        
        if isinstance(plan.context, Condition):
            c_args,_ = self._check(plan.context)
            #print(f'Args: {c_args}')
            return c_args
        
        for context in plan.context:
            ctxt = self.get(context[1],ck_src=False) 
            #print(f'{context} :: {ctxt}')
            if ctxt is None:
                if context[0] is False: 
                    continue
                break
            assert isinstance(ctxt, Belief | Goal), f"Unexpected Context Type: {type(ctxt)}, Expected Belief | Goal"
            if ctxt.args_len == 0: 
                continue
            elif ctxt.args_len == 1:
                args += ctxt._args
            else:
                args += (ctxt._args,)  
            
        else:
            return args
        return None
    
    def _format_check(self, value, args, tupled):
        #print(f'Formating Value: {value}:{type(value)}')
        if isinstance(value, Condition) and not isinstance(value, Belief|Goal|Percept): 
            f_value, f_tupled = self._check(value, args, tupled)
            if f_value is None:
                return None, False, True, f_tupled
            v_args = True
        else: 
            f_tupled = tupled
            f_value = value
            v_args = False
        
        v_bool = False
        if isinstance(f_value, Belief|Goal|Percept):
            v_data = self.get(f_value, ck_src=False)
            if v_data is not None:
                v_bool = True
                v_data = v_data._args
            else:
                v_data = (None,)
            for v in f_value._args:
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
        
        return v_data, v_bool, v_args, f_tupled
    
    def _check(self, condition: Condition, args: tuple = tuple(), tupled = False) -> tuple[tuple, bool] | tuple[None, bool]:
        #print(f'Checking Condition: {condition} - {type(condition.left_value)} - {args} - {tupled}')
        cnd_type = condition.c_type
        
        if cnd_type == "~":
            if isinstance(condition.left_value, Belief | Goal) and self.get(condition.left_value, ck_src=False) is None:
                return args, True
            elif isinstance(condition.left_value, Condition) and not isinstance(condition.left_value, Belief | Goal) and self._check(condition.left_value, args, tupled)[0] is None:
                return args, True
            else:
                return None, True
        
        assert condition.right_value is not None and condition.func is not None, f"Unexpected Condition: {condition}"
        
        v0_data, v0_bool, v0_args, v0_tupled = self._format_check(condition.left_value, args, tupled)
        v1_data, v1_bool, v1_args, v1_tupled = self._format_check(condition.right_value, args, tupled)
        #print(f'Checking: {v0_data}:{v0_bool}:{v0_args}:{v0_tupled} | {v1_data}:{v1_bool}:{v1_args}:{v1_tupled}')
        
        if v0_data is None and v1_data is None:
            return None, tupled
        if not v0_bool and not v1_bool:
            return None, tupled
        
        ret_bool = False    
        match cnd_type:
            case "op":
                ret_bool = condition.func(v0_bool, v1_bool)
            case "comp":
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
        if v0_args:
            if not v0_tupled:
                f_args += (v0_data,)
            else:
                f_args += v0_data
        if v1_args:
            if not v1_tupled:
                f_args += (v1_data,)
            else:
                f_args += v1_data
        f_args += args

        return f_args, True
    
    def _force_close_thread(self, thread: threading.Thread):
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
    
    def _execute_plan(self, chosen_plan: Plan, trigger: Event, args: tuple[Any, ...]):
        if self.__running_intentions.__len__() >= self.max_intentions:
            self.__intentions.insert(0,(chosen_plan, trigger, args))
            self.logger.debug(f"Plan {chosen_plan} not executed", extra=self.agent_info) if self.logging else ...
            return None
        try:
            assert trigger is not None, f"Unexpected None Trigger with {chosen_plan}:{args}"
            self.__running_intentions.append((chosen_plan, trigger, args))
            
            plan_thread = threading.Thread(target=self._run_plan, args=(chosen_plan,trigger,args))
            plan_thread.start()
            
        except RunPlanError:
            self.logger.warning(f"Plan {chosen_plan} failed", extra=self.agent_info) if self.logging else ...

    def _run_plan(self, plan: Plan, trigger: Event, args: tuple, instant_flag: bool = False):
        self.logger.debug(f"Executing Intention", extra=self.agent_info) if self.logging else ...
        self.print(f"Running {plan}")  if self.show_exec or self.show_cycle else ...
        try:     
            result = plan.body(self, trigger.data.source, *args)
                
            self.last_event = trigger
            trigger_type = trigger.data    
            if result == "Error" or result == -1:
                self.logger.warning(f"{plan} did not complete successfully", extra=self.agent_info) if self.logging else ...
            else:
                for intention in self.__intentions:
                    if trigger_type == intention[1].data:
                        self.__intentions.remove(intention)
                if not instant_flag:
                    self.__running_intentions.remove((plan,trigger,args))
                    self.last_intention = (plan,trigger,args)

                if type(trigger_type) is Goal:
                    self.last_goal = trigger_type
                    if self.has(trigger_type) and result == False:
                        self._new_event(gain, trigger_type, instant=False)
                    elif self.has(trigger_type) and result != False:
                        self.rm(trigger_type)
                        self.logger.info(f"{trigger_type} cleared", extra=self.agent_info) if self.logging else ...
                    else:
                        self.logger.warning(f"{trigger_type} already cleared by another plan's execution", extra=self.agent_info) if self.logging else ...
            self.last_plan = plan
            return result
        except Exception as e:
            buffer = f"<{self.my_name}> Error while executing {plan}:\n\tTrigger={trigger} | Context={args}\n\t{repr(e)}\n"
            _, _, exc_traceback = sys.exc_info()
            tb_entries = extract_tb(exc_traceback)
            
            #excluded_files = ['agent.py', 'communication.py', 'admin.py', 'environment.py']
            
            filtered_entries = [
                entry for entry in tb_entries 
                #if not any(excluded_file in entry.filename for excluded_file in excluded_files)
            ]
            
            if filtered_entries:
                buffer += "  Filtered Traceback (most recent call last):\n"
                for entry in filtered_entries:
                    buffer +=f'\tFile "{entry.filename}", line {entry.lineno}, in {entry.name}, during cycle {self.cycle_counter}\n'
                    if entry.line:
                        buffer += f'\t\t{entry.line}'
                if "positional argument" in str(e):
                    buffer += f"\n\tCheck Plan '{plan.body.__name__}' for self, src, and trigger/context args"
            else:
                buffer += " No matching traceback entries found."
            print(buffer)
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
    
    # TODO: implement stoping plan
    def _stop_plan(self, plan):
        self.print(f"Stoping {plan})")  if self.show_exec else ...
        pass    
    
    def _format_data(self, decision: str, chosen_plan: Plan | None = None, trgr: Event | None = None, args: tuple | None = None, data_type: Iterable[Belief | Goal] | Belief | Goal | None = None, instant: bool | None = False) -> str:
        match decision:
            case "Adding Info" | "Removing Info" | "Testing Info":
                return f'{data_type}  -  instant[{instant}]'
            case "Execute Intention" | "Running Intention" | "Instant Plan":
                assert trgr is not None
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
                type_dicts[type(data_type)].update({data_type.source: {data_type.key: {data_type}}})
            case Iterable():
                for typ in data_type:
                    if not isinstance(typ, Belief) and not isinstance(typ, Goal):
                        raise InvalidBeliefError(
                            f"Expected data type to be Iterable[Belief | Goal] | Belief | Goal, recieved Iterable[{type(typ).__name__}]"
                        )
                    # Dict[ source, Dict[ key, Set[ Belief | Goal ]]]
                    type_dict: Dict[str | tuple[str,int], Dict[str, Set]] = type_dicts[type(typ)]
                    if typ.source in type_dict:
                        if typ.key in type_dict[typ.source]:
                            type_dict[typ.source][typ.key].add(typ)
                        else:
                            type_dict[typ.source].update({typ.key: {typ}})
                    else:
                        type_dict.update({typ.source: {typ.key: {typ}}})
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

