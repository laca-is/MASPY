import threading
import ctypes
from dataclasses import dataclass, field
from maspy.environment import Environment, Percept	
from maspy.communication import Channel, Act
from maspy.learning import EnvModel
from maspy.error import (
    InvalidBeliefError,
    InvalidPlanError,
    RunPlanError,
)
from maspy.utils import set_changes, merge_dicts, manual_deepcopy, bcolors
from typing import List, Optional, Dict, Set, Any, Union, Type, cast
from collections.abc import Iterable, Callable, Sequence
from functools import wraps
from time import sleep
from enum import Enum
import importlib as implib
import inspect
import traceback
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
class Belief:
    key: str = field(default_factory=str)
    _args: tuple | Any = field(default_factory=tuple)
    source: str | tuple[str, int] = DEFAULT_SOURCE
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

    def update(self, key: Optional[str] = None, args=None, source=None) -> "Belief":
        if key is not None:
            new_name = key
        else:
            new_name = self.key

        if args is not None:
            new_args = args
        else:
            new_args = self._args

        if source is not None:
            new_source = source
        else:
            new_source = self.source

        return Belief(new_name, new_args, new_source)

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
    
    def __invert__(self):
        return False,self
    
    def __and__(self, other):
        print(self, "&", other)
        return 42
        
    def __or__(self, other):
        print(self, "|", other)
        return 27
    
    def __xor__(self, other):    
        print(self, "^", other)
        return 4
    
    def __lt__(self, other):
        return self.compare(other, "<")
        
    def compare(self, other, comp_t):
        if not isinstance(other, Sequence):
            other = [other]
        for x,y in zip(self._args, other):
            print(f"comparing {x} with {y}")
            match comp_t:
                case "<":
                    if x < y:
                        continue
            break
        else:
            return True
        return False
    
    def __ge__(self, other):
        print(self, ">=", other)
        return True
    
    
    
    def __str__(self) -> str:
        return f'Belief {self.key}({self.args})[{self.source}]'
    
    def __repr__(self):
        return self.__str__()

@dataclass
class Goal:
    key: str = field(default_factory=str)
    _args: tuple | Any = field(default_factory=tuple)
    source: str | tuple[str, int] = DEFAULT_SOURCE

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

    def update(self, key: Optional[str] = None, args=None, source=None) -> "Goal":
        if key is not None:
            new_name = key
        else:
            new_name = self.key

        if args is not None:
            new_args = args
        else:
            new_args = self._args

        if source is not None:
            new_source = source
        else:
            new_source = self.source

        return Goal(new_name, new_args, new_source)

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
        return f"Goal {self.key}({self.args})[{self.source}]"
    
    def __repr__(self):
        return self.__str__()
    
@dataclass
class Event:
    change: Event_Change = field(default_factory=lambda:gain)
    data: Belief | Goal = field(default_factory=Belief)
    
    def __str__(self) -> str:
        return f"{self.change.name} : {self.data}"
    
    def __repr__(self):
        return self.__str__()
    
@dataclass
class Plan:
    trigger: Event = field(default_factory=Event)
    context: List[tuple[bool, Belief | Goal]] = field(default_factory=list)
    body: Callable = lambda _: {}
    conditions: tuple[Callable[..., Any], ...] = (lambda _: {},)
    ev_ctrl: threading.Event = threading.Event()
    
    def __str__(self) -> str:
        return f"{self.trigger}, {self.context}, {self.body.__name__}() )"
    
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

def pl(change: Event_Change, data: Belief | Goal, context: Belief | Goal | List[Belief | Goal] = [], *condition: Callable):
    class decorator:
        def __init__(self,func):
            self.func = func
  
        def __set_name__(self, instance: Agent, name: str):
            if not isinstance(change, Event_Change) or not isinstance(data, Belief | Goal):
                raise TypeError
            
            list_context: List[tuple[bool, Belief | Goal]]
            
            if isinstance(context, Belief | Goal):
                list_context = [(True,context)]
            
            if isinstance(context, Iterable):
                list_context = []
                for ctxt in context:
                    if isinstance(ctxt, Belief | Goal):
                        list_context.append((True,ctxt))
                    elif isinstance(ctxt, tuple) and len(ctxt) == 2 and isinstance(ctxt[0], bool) and isinstance(ctxt[1], Belief | Goal):
                        list_context.append(ctxt)
                    elif ctxt is False:
                        list_context.append(context)
                        break
                    else:
                        raise Exception(f'Invalid type {type(ctxt)}:{ctxt} - was expecting Belief or Goal')
            
            event = Event(change,data)
            plan = Plan(event,list_context,self.func,condition)
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
        self.cycle_log: Dict[float, list[Dict[str, Any]]] = dict()
        self.cycle_counter = 0
        self.last_log: Dict[str, Any] = dict()
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
        
        self.delay: int|float = 0.000001
        self.stop_flag: threading.Event | None = None
        self.running: bool = False
        self.thread: threading.Thread | None = None
        self.saved_msgs: List = []
        self.lock = threading.Lock()
        self.reply_event: Dict[tuple, threading.Event] = {}
        
        self._ml_models: List = []
        self.policies: List = []
    
        self._environments: Dict[str, Environment] = dict()
        self._channels: Dict[str, Channel] = dict()
        self._dicts: Dict[str, Union[Dict[str, Environment], Dict[str, Channel]]] = {"environment":self._environments, "channel":self._channels}
        
        self._strategies: list[EnvModel] = []

        self.max_intentions: int = nax_intentions
        self.last_intention: tuple[Plan, Event, tuple] = (Plan(), Event(), tuple())
        self.__intentions: list[tuple[Plan, Event, tuple]] = []
        self.__supended_intentions: list[tuple[Plan, Event, tuple, str, Event | None]] = []
        self.__running_intentions: list[tuple[Plan, Event, tuple]] = []
        
        
        self.__events: List[Event] = []
        self.last_event: Event | None = None
        self.__beliefs: Dict[str | tuple[str, int], Dict[str, Set[Belief]]] = dict()
        self.__goals: Dict[str | tuple[str, int], Dict[str, Set[Goal]]] = dict()
        self.belief_list: List[Belief] = []
        self.goal_list: List[Goal] = []
        self.last_goal: Goal | None = None
        self.running_goal: Goal | None = None
        self.percept_filter: Dict[str, set[str]] = {ignore.name: set(), focus.name: set()}
        
        self.last_sent: list[tuple[str, str | List[str], str, MSG]] = []
        self.last_recv: list[tuple[str, MSG]] = []
        self.last_plan: Plan | None = None
        
        if beliefs: 
            self.add(beliefs, False)
        if goals: 
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
        self.reasoning()
    
    def print(self,*args, **kwargs):
        if not self.printing:
            return
        f_args = "".join(map(str, args))
        f_kwargs = "".join(f"{key}={value}" for key, value in kwargs.items())
        with self.lock:
            return print(f"{self.tcolor}Agent:{self.my_name}> {f_args}{f_kwargs}{bcolors.ENDCOLOR}")
        
    @property
    def print_beliefs(self):
        buffer = "Beliefs:"
        for sources_dict in self.__beliefs.values():
            for belief_set in sources_dict.values():
                for belief in belief_set:
                    buffer += f'\n\t{belief}'
        self.print(buffer)

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
    
    def filter_perceptions(self, operation: Operation, option: Option, group: str | list[str]):
        assert isinstance(operation,Operation), f"Invalid operation. Choose {Operation}."
        assert isinstance(option,Option), f"Invalid option. Choose {Option}."

        if isinstance(group, str):
            group = [group]
            
        option_str = option.name
        print(f'{operation} {option_str} {group} to filter.')
        for g in group:
            if operation == Operation.add:
                self.percept_filter[option_str].add(g)
            elif operation == Operation.rm and g in self.percept_filter[option_str]:
                self.percept_filter[option_str].remove(g)
            else:
                self.print(f"{g} not in {option_str} filter.")
    
    def connect_to(self, target: Environment | Channel | str):
        if isinstance(target, str):
            instance = Environment.get_instance(target) or Channel.get_instance(target)
            if instance:
                target = instance
                
        if isinstance(target, str):
            classes: List[tuple] = []
            try:
                imported = implib.import_module(target)
            except ModuleNotFoundError:
                self.print(f"No File named '{target}' found")
                return
            for name, obj in inspect.getmembers(imported):
                if inspect.isclass(obj) and name != "Environment" and name != "Channel":
                    lineno = inspect.getsourcelines(obj)[1]
                    classes.append((lineno, obj))
            classes.sort()
            target = classes[0][1](target)      
            del imported 
                    
        match target:
            case Environment():
                with self.lock:
                    self._environments[target.my_name] = target
            case Channel():
                with self.lock:
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
                with self.lock:
                    target._rm_agent(self)
                    del self._environments[target.my_name]
            case Channel():
                with self.lock:
                    target._rm_agent(self)
                    del self._channels[target.my_name]
                
    def add_policy(self, policy: EnvModel):
        self.print(f"Adding model for {policy.name}")
        self._strategies.append(policy)
        self.connect_to(Environment(policy.name))
    
    def add_plan(self, plan: Plan | List[Plan]):
        plans = self._clean_plans(plan)
        self._plans += plans

    def rm_plan(self, plan: Plan | List[Plan]):
        if isinstance(plan,list):
            for p in plan: 
                self._plans.remove(p)
        else:
            self._plans.remove(plan)
    
    def _new_event(self,change: Event_Change, data: Belief | Goal | Iterable[Belief | Goal], synchronous: bool = False):
        new_event: Event
        if isinstance(data, Iterable):
            for dt in data:
                if isinstance(dt,Belief) and not dt.adds_event: 
                    continue
                self.print(f"New Event: {change.name},{dt}")  if self.show_exec else ...
                new_event = Event(change,dt)
                if synchronous:
                    self._instant_plan(new_event)
                else:
                    self.__events.append(new_event)
                    self._check_event_supended(new_event)
                        
        else:
            assert isinstance(data, Belief | Goal)
            if isinstance(data,Belief) and not data.adds_event: 
                return
            self.print(f"New Event: {change.name},{data}")  if self.show_exec else ...
            new_event = Event(change,data)
            if synchronous:
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
        ) -> Dict[str | tuple[str, int], Dict[str, Set[Belief]]] | Dict[str | tuple[str, int], Dict[str, Set[Goal]]] | List[Plan] | List[Event] | None:
        if isinstance(data_type,Belief) or data_type == Belief:
            return self.__beliefs
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
        
    def add(self, data_type: Belief | Goal | Iterable[Belief | Goal], instant: bool = False):
        self.save_cycle_log("Adding Info", self._format_data("Adding Info", data_type=data_type,instant=instant))
        if self.running is False:
            instant = False
        self.print(f"Adding {data_type}") if self.show_exec else ...
        cleaned_data = self._clean(data_type)
        
        for type_data, data in cleaned_data.items():
            if len(data) == 0: 
                continue
            type_base = self._get_type_base(type_data)
            if isinstance(type_base,dict):
                merge_dicts(data,type_base)
            
            for src in data.values():
                for values in src.values():
                    for data_v in values:    
                        self.update_lists(data_v,"add")
                        
        self._new_event(gain,data_type,instant)
    
    def rm(self, data_type: Belief | Goal | Iterable[Belief | Goal], instant: bool = False):
        self.save_cycle_log("Removing Info",f'{data_type}:{instant}')  
        if self.running is False:
            instant = False
        self.print(f"Removing {data_type}") if self.show_exec else ...
        
        if not isinstance(data_type, Iterable): 
            data_type = [data_type]
            
        for typ in data_type:
            if isinstance(typ, Belief):
                self.__beliefs[typ.source][typ.key].remove(typ)
            elif isinstance(typ, Goal):
                self.__goals[typ.source][typ.key].remove(typ)
            else:
                self.print(f"Data_Type {typ} is neither Belief or Goal")
                
            self.update_lists(typ,"rm")
              
        self._new_event(lose,data_type,instant)

    def test(self, data_type: Belief | Goal):
        self._new_event(test,data_type)
    
    def has(self, data_type: Belief | Goal | Plan | Event):
        return self.get(data_type) is not None

    def get(self, data_type: Belief | Goal | Plan | Event | Type[Belief | Goal | Plan | Event],
        search_with:  Optional[Belief | Goal | Plan | Event] = None,
        all = False, ck_chng=True, ck_type=True, ck_args=True, ck_src=True
    ) -> Belief | Goal | Plan | Event | List[Belief | Goal | Plan | Event] | None:
        if isinstance(data_type, type): 
            data_type = data_type()
        type_base = self._get_type_base(data_type)
        if type_base is None:
            return None
        if search_with is None: 
            search_with = data_type

        change, data = self._to_belief_goal(search_with)
        
        found_data: List[Belief | Goal | Plan | Event] = []
        match data_type:
            case Belief() | Goal():  
                assert isinstance(type_base, dict)
                for keys in type_base.values():
                    for values in keys.values():
                        for value in values:
                            if self._compare_data(value,data,ck_type,ck_args,ck_src):
                                found_data.append(value)
                                if not all: 
                                    return value                
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
            if caller_function_name in {'_retrieve_plans','recieve_msg','_retrieve_context','_select_plan','has'}:
                return None
            if data_type == search_with:
                self.print(f'Does not contain {type(data_type).__qualname__} like {data_type}. Searched during {caller_function_name}()')
            else:
                self.print(f'Does not contain {type(data_type).__qualname__} like {search_with}. Searched during {caller_function_name}()')
            return None
         
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
        with self.lock:
            self.__running_intentions.remove(intention)
            self.__supended_intentions.append(intention_reason)
        
        intention[0].ev_ctrl.wait(timeout)
        
        with self.lock:
            self.__supended_intentions.remove(intention_reason)

        while len(self.__running_intentions) > self.max_intentions:
            sleep(0.01)
        with self.lock:
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
                change = data_type.trigger.change
                belief_goal = data_type.trigger.data
            case Event(): 
                change = data_type.change
                belief_goal = data_type.data
            case _: 
                self.print(f"Error in _to_belief_goal: {type(data_type)}:{data_type}")
                return None, None
        return change,belief_goal
    
    def _compare_data(self, data1: Belief | Goal, data2: Belief | Goal, ck_type: bool, ck_args: bool, ck_src: bool):
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
        if type(target) is str and not target.split("_")[-1].isdigit():
            target = f"{target}_1"
        try:
            if msg_act.name in ['askOneReply','askAllReply']:
                with self.lock:
                    assert isinstance(msg, Belief | Goal)
                    msg = Ask(msg, self.my_name)
                
                self._channels[channel]._send(self.my_name,target,msg_act,msg)
                self.last_sent.append((self.my_name,target,msg_act.name,msg))
                msg.reply_event.clear()
                was_set = msg.reply_event.wait()
                
                if msg.reply_content is not None:
                    self.add(msg.reply_content, False)
                    return msg.reply_content
                elif was_set:
                    self.print(f"No reply for {msg} from {target}") if self.show_exec else ...
                    return None
                else:
                    self.print(f"Timeout while waiting for reply for {msg}") if self.show_exec else ...
                    return None
            else:
                self._channels[channel]._send(self.my_name,target,msg_act,msg)
                self.last_sent.append((self.my_name,target,msg_act.name,msg))
            
            ch = "in the default channel"
            if channel != DEFAULT_CHANNEL:
                ch = f" in the channel {channel}"
            if type(target) is str: 
                self.save_cycle_log("Send Message", f' {self.my_name}  to  {target}  -  {msg_act.name} {msg}{ch}')
            else:
                self.save_cycle_log("Send Message", f' {self.my_name}  broadcasting  {msg_act.name} {msg}{ch}')
        except KeyError:
            self.print(f"Not Connected to Selected Channel:{channel}")
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
            self.saved_msgs.append((act,msg))

    def _mail(self, selection_function: Callable | None = None) -> None:
        if callable(selection_function):
            selection_function(self.saved_msgs)
        else:
            while self.saved_msgs:
                act,msg = self.saved_msgs.pop(0)
                try:
                    self.last_recv.append((act.name,msg))
                    self.recieve_msg(act,msg)
                except AssertionError as ae:
                    print(f"\t{repr(ae)}")
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    last_frame = traceback.extract_tb(exc_traceback)[-1]
        
                    formatted_last_frame = f"File \"{last_frame.filename}\", line {last_frame.lineno}, in {last_frame.name}\n  {last_frame.line}"
                    
                    print("Error originated from:")
                    print(formatted_last_frame)
                if not self.read_all_mail:
                    break

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
                found_data = self.get(msg.data_type,ck_src=False)
                if isinstance(found_data, Belief):
                    msg.reply_content = found_data
                else:
                    msg.reply_content = None
                msg.reply_event.set()
                
            case 'askAll':
                assert isinstance(msg, Ask), f'Act askAll must request an Ask not {type(msg).__qualname__}'
                found_data = self.get(msg.data_type,all=True,ck_src=False)
                assert isinstance(found_data, list)
                for data in found_data:
                    if isinstance(data, Belief):
                        self.send(msg.source, Act.tell, data)
                    
            case 'askAllReply':
                assert isinstance(msg, Ask), f'Act askAllReply must request an Ask not {type(msg).__qualname__}'
                found_data = self.get(msg.data_type,all=True,ck_src=False)
                if isinstance(found_data, list):
                    msg.reply_content = cast(List[Belief|Goal], found_data)
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
                found_plans = self.get(Plan(Event(test,msg.data_type)),all=True,ck_chng=False)
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
            if cls_type == "environment" or cls_type is None: 
                if cls_name is not None and cls_name in self._environments:
                    if ag_cls in self._environments[cls_name].agent_list :
                        agents.append(manual_deepcopy(self._environments[cls_name].agent_list)[ag_cls])
                else:
                    for env in self._environments.values():
                        if ag_cls in env.agent_list:
                            agents.append(manual_deepcopy(env.agent_list)[ag_cls])
                                    
            if cls_type == "channel" or cls_type is None:   
                if cls_name is not None and cls_name in self._channels:
                    if ag_cls in self._channels[cls_name].agent_list:
                        agents.append(manual_deepcopy(self._channels[cls_name].agent_list)[ag_cls])
                else:
                    for ch in self._channels.values():
                        if ag_cls in ch.agent_list:
                            agents.append(manual_deepcopy(ch.agent_list)[ag_cls])    
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
                    return method(self.my_name, *args, **kwargs)   
                return wrapper
        raise AttributeError(f"{self.my_name} doesnt have the method '{name}' and is not connected to any environment with the method '{name}'.")
    
    def reasoning(self) -> None:
        self.running = True
        self.stop_flag = threading.Event()
        self.thread = threading.Thread(target=self.cycle,args=(self.stop_flag,))
        self.thread.start()
    
    def stop_cycle(self, log_flag=False) -> None:
        self.print("Shutting Down...") if log_flag else ...
        self.save_cycle_log(decision="End of Reasoning")
        self.running = False
        if self.stop_flag is not None:
            self.stop_flag.set()
        self.paused_agent = True
                 
    def cycle(self, stop_flag: threading.Event) -> None:
        self.cycle_counter = 1
        while not stop_flag.is_set():   
            self.print("#### New cycle ####") if self.show_cycle else ...
            self._perception()   
            self._mail() 
            event = self._select_event()
            self.print(f"Selected event: {event} in {self.__events}") if self.show_cycle else ...
            plans = self._retrieve_plans(event)
            self.print(f"Selected plans: {plans} in {self._plans}") if self.show_cycle else ...
            
            if len(self.__running_intentions) < self.max_intentions:
                chosen_plan, trgr, args = self._select_intention(plans,event)
                self.print(f"Selected intention to run: {chosen_plan} with {args} arguments") if self.show_cycle else ...
            else:
                self.print(f"Running intention: {self.__running_intentions[0][0]} with {self.__running_intentions[0][2]} arguments") if self.show_cycle else ...
            
            description: Any
            if chosen_plan is not None and trgr is not None:
                decision = "Execute Intention"
                description = self._format_data(decision,chosen_plan,trgr,args)
            elif len(self.__running_intentions) >= 1:
                decision = "Running Intention"
                description = self._format_data(decision,*self.__running_intentions[0])
            elif self._strategies:
                for strat in self._strategies:
                    state = strat.get_state()
                    if state in strat.terminated_states:
                        continue
                    int_action = strat.get_action(state)
                    env = self._environments[strat.name]
                    str_action = strat.actions_list[int_action]
                    action = strat.actions_dict[str_action]
                    if action.act_type == 'single':
                        action.func(env, self.my_name)
                    else:
                        action.func(env, self.my_name, str_action)
                    decision = "Execute Strategy"
                    description = f'state: {state} action:{str_action}'
                    self.print(f"Executing Stretegy: action:{str_action} in state: {state}") if self.show_cycle else ...
                    break
                else:
                    decision = "No Intention"
                    description = self._format_data(decision,trgr=event)
            else:
                decision = "No Intention"
                description = self._format_data(decision,trgr=event)
                
            self.save_cycle_log(decision, description, event, plans)
            
            if stop_flag.is_set():
                break
            self._execute_plan(chosen_plan, trgr, args)
            self.print("#### End of cycle ####") if self.show_cycle else ...
            if self.delay: 
                sleep(self.delay)
            self.cycle_counter += 1
    
    def _perception(self) -> None:
        percept_dict: Dict[str, dict] = dict()
        with self.lock:
            for env_name in self._environments:
                self.print(f"Percepting '{env_name}'") if self.show_cycle and not self.show_prct else ...
                percepts = self._environments[env_name].perception()
                percepts = self._apply_filters(percepts,env_name)
                self.print(f"Percepting {env_name} : {percepts}") if self.show_prct else ...
                merge_dicts(percepts,percept_dict)
            if percept_dict == {}:
                return
            belief_dict: Dict[str, Dict[str, Set[Belief]]] = self._percepts_to_beliefs(percept_dict)
            self._revise_beliefs(belief_dict)
    
    def _apply_filters(self, percepts: Dict[str, Dict[str, Set[Percept]]], env_name: str):
        filtered_percepts: Dict[str, Dict[str, Set[Percept]]] = dict()
        focusing = True if len(self.percept_filter['focus']) > 0 else False
        for group, keys in percepts.items():
            if (focusing and group in self.percept_filter['focus']) or (not focusing and group not in self.percept_filter['ignore']):
                if env_name in filtered_percepts:
                    for key, value in keys.items():
                        filtered_percepts[env_name].setdefault(key, set()).update(value)
                else:
                    filtered_percepts[env_name] = keys
            
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
                    self.print(f"Percepting '{name}'") if not self.show_prct else self.print(f"Percepting '{name}'")
                    merge_dicts(percepts,percept_dict)
                except KeyError:
                    self.print(f"Not Connected to Environment:{name}")
        else:
            try:
                percept_dict = self._environments[env_name].perception()
                percept_dict = self._apply_filters(percept_dict,env_name)
                self.print(f"Percepting '{env_name}' : {percept_dict}") if self.show_prct else ...
            except KeyError:
                self.print(f"Not Connected to Environment:{env_name}")
        
        belief_dict = self._percepts_to_beliefs(percept_dict)
        self._revise_beliefs(belief_dict)
    
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
     
    def _revise_beliefs(self, belief_dict: Dict[str, Dict[str, Set[Belief]]]) -> None:
        for source, keys in self.__beliefs.copy().items():
            if source == DEFAULT_SOURCE: 
                continue # Does not remove "self"
            if isinstance(source, tuple): 
                continue # Does not remove messages
            if source in belief_dict:
                for key, beliefs in keys.copy().items():
                    if key in belief_dict[source]: 
                        new_beliefs, gained_beliefs, lost_beliefs = set_changes(beliefs,belief_dict[source][key])
                        self.__beliefs[source][key] = new_beliefs
                        self._new_event(gain, gained_beliefs) # Gained new specific belief
                        self._new_event(lose, lost_beliefs) # Lost an old specific belief
                        del belief_dict[source][key]
                        if self.show_prct and gained_beliefs:
                            self.print(f"Specific Beliefs gained in revision: {gained_beliefs}")
                        if self.show_prct and lost_beliefs:
                            self.print(f"Specific Beliefs lost in revision: {lost_beliefs}") 
                    else:
                        self._new_event(lose, self.__beliefs[source][key]) # Lost whole key belief
                        self.print(f"Key Beliefs lost in revision: {self.__beliefs[source][key]}") if self.show_prct else ...
                        del self.__beliefs[source][key]
                        
                if belief_dict[source] == {}:
                    del belief_dict[source]
            else:
                for beliefs in keys.values():
                    self.print(f"{source} Beliefs lost in revision: {beliefs}") if self.show_prct and beliefs else ...
                    self._new_event(lose, beliefs) # Lost whole source of belief (env)
                del self.__beliefs[source]
        
        for source,keys in belief_dict.items():
            for beliefs in keys.values():
                self.print(f"Rest of {source} Beliefs gained in revision: {beliefs}") if self.show_prct and beliefs else ...
                self._new_event(gain, beliefs) # Gained beliefs of new sources/keys
                
        self.print(f"Updating beliefs: {belief_dict}") if self.show_prct else ...
        merge_dicts(belief_dict,self.__beliefs)
    
    def _select_event(self) -> Event | None:
        if self.__events == []: 
            return None 
        event = self.__events.pop(0)
        return event
    
    def _instant_plan(self, event: Event):
        plans = self._retrieve_plans(event)
        if plans is None and isinstance(event.data,Goal):
            self.print(f"No applicable Plan found for {event}")
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
            self.save_cycle_log("Instant Plan", self._format_data("Instant Plan",plan,event,ev_args+args),event,plans)
            self._run_plan(plan,event,ev_args+args,True)
        elif type(event.data) is Goal:
            self.print(f"Found no applicable plan for {event.change.name}:{event.data}")
    
    def _retrieve_plans(self, event: Event | None) -> List[Plan] | None: 
        if event is None: 
            return None
        retrieved = self.get(Plan,event,all=True,ck_src=False)
        assert isinstance(retrieved, list | None), f"Unexpected Retrieved Plan: {type(retrieved)}, Expected List[Plan] | None"
        return cast(List[Plan] | None, retrieved) 
    
    def _select_intention(self, plans: List[Plan] | None, event: Event | None) -> tuple[Plan, Event, tuple] | tuple[None, None, tuple]:
        if plans is None:
            if event is not None and isinstance(event.data,Goal):
                self.print(f"No applicable Plan found for {event}")
            try:
                plan, trigger, args = self.__intentions.pop(0)
                return plan, trigger, args
            except IndexError:
                return None, None, tuple()
        retrieved_plans = plans.copy()
        while retrieved_plans:
            plan = retrieved_plans.pop(0)
            ctxt = self._retrieve_context(plan)
            if ctxt is not None and event is not None:
                if event.data.args_len < 2:
                    ev_args = event.data._args
                else:
                    ev_args = (event.data._args,)
                
                if ctxt == ((),):
                    args = ev_args
                else:
                    args = ev_args+ctxt
                    
                #print(f'{plan.trigger} {plan.executable(*args)}')
                
                if plan.executable(*args):
                    self.__intentions.append((plan,event,args))
                    break
        try:
            plan, trigger, args = self.__intentions.pop(0)
            return plan, trigger, args
        except IndexError:
            self.print(f"Found no applicable plan for {event.change.name}:{event.data}") if self.show_exec and event is not None else ...
            return None, None, tuple()
    
    def _retrieve_context(self, plan: Plan) -> tuple | None:
        args: tuple = tuple()
        for context in plan.context:
            ctxt = self.get(context[1],ck_src=False) 
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
    
    def _execute_plan(self, chosen_plan: Plan | None, trigger: Event | None, args: tuple[Any, ...]):
        if not chosen_plan or len(self.__running_intentions) >= self.max_intentions:
            return None
        try:
            assert trigger is not None, f"Unexpected None Trigger with {chosen_plan}:{args}"
            self.__running_intentions.append((chosen_plan, trigger, args))
            plan_thread = threading.Thread(target=self._run_plan, args=(chosen_plan,trigger,args))
            plan_thread.start()
        except RunPlanError:
            self.print(f"{chosen_plan} failed")

    def _run_plan(self, plan: Plan, trigger: Event, args: tuple, instant_flag: bool = False):
        self.print(f"Running {plan}")  if self.show_exec or self.show_cycle else ...
        try:
            trigger_type = trigger.data
            if type(trigger_type) is Goal:
                self.last_goal = trigger_type
                self.last_event = trigger
                if trigger_type in self.__goals[trigger_type.source][trigger_type.key]:
                    self.__goals[trigger_type.source][trigger_type.key].remove(trigger_type)
                    self.update_lists(trigger_type,"rm")
                else:
                    self.print(f"{trigger_type} lost before correct execution")
                    
            result = plan.body(self, trigger.data.source, *args)
            if not instant_flag:
                self.__running_intentions.remove((plan,trigger,args))
                self.last_intention = (plan,trigger,args)
                
            self.last_plan = plan
            return result
        except Exception as e:
            buffer = f"<{self.my_name}> Error while executing {plan}:\n\tTrigger={trigger} | Context={args}\n\t{repr(e)}\n"
            _, _, exc_traceback = sys.exc_info()
            tb_entries = traceback.extract_tb(exc_traceback)
            
            #excluded_files = ['agent.py', 'communication.py', 'admin.py', 'environment.py']
            
            filtered_entries = [
                entry for entry in tb_entries 
                #if not any(excluded_file in entry.filename for excluded_file in excluded_files)
            ]
            
            if filtered_entries:
                buffer += "  Filtered Traceback (most recent call last):\n"
                for entry in filtered_entries:
                    buffer +=f'  File "{entry.filename}", line {entry.lineno}, in {entry.name}, during cycle {self.cycle_counter}\n'
                    if entry.line:
                        buffer += f'    {entry.line}'
            else:
                buffer += " No matching traceback entries found."
            print(buffer)
            exit(1) 
    
    def save_cycle_log(self, decision: str, description: Any | None = None, event: Event | None = None, plans: List[Plan] | None = None) -> None:
        log: Dict[str, Any] = {"cycle":self.cycle_counter}
        info = {"decision":decision,"description":description,"beliefs":self.belief_list.copy(),"goals":self.goal_list.copy(),"running_goal":self.last_goal,"last_recv":self.last_recv,"event":event,"last_event":self.last_event,"retrieved_plans":plans,"intentions":self.__intentions.copy(),"events":self.__events.copy(),"connected_envs":list(self._environments.keys()), "connected_chs":list(self._channels.keys())}
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
            case "Adding Info" | "Removing Info":
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

