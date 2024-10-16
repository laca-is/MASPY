import threading
import ctypes
from dataclasses import dataclass, field
from maspy.environment import Environment, Percept	
from maspy.communication import Channel, Act
#from maspy.learning.core import Learning
from maspy.error import (
    InvalidBeliefError,
    InvalidPlanError,
    RunPlanError,
)
from maspy.utils import set_changes, merge_dicts, manual_deepcopy
from typing import List, Optional, Dict, Set, Any, Union, Type, cast
from collections.abc import Iterable, Callable
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
    
    def __str__(self) -> str:
        return f'Belief{self.key,self.args,self.source}'
    
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
        return f"Goal{self.key,self.args,self.source}"
    
    def __repr__(self):
        return self.__str__()
    
@dataclass
class Event:
    change: Event_Change = field(default_factory=lambda:gain)
    data: Belief | Goal = field(default_factory=Belief)
    
    def __str__(self) -> str:
        return f"Event( {self.change.name}, {self.data})"
    
    def __repr__(self):
        return self.__str__()
    
@dataclass
class Plan:
    trigger: Event = field(default_factory=Event)
    context: List[Belief | Goal] = field(default_factory=list)
    body: Callable = lambda _: {}
    ev_ctrl: threading.Event = threading.Event()
    
    def __str__(self) -> str:
        return f"Plan( {self.trigger}, {self.context}, {self.body.__name__}() )"
    
    def __repr__(self):
        return self.__str__()
    
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

def pl(change: Event_Change, data: Belief | Goal, context: Belief | Goal | List[Belief | Goal] = []):
    class decorator:
        def __init__(self,func):
            self.func = func
                
        def __set_name__(self, instance: Agent, name: str):
            if not isinstance(data, Belief | Goal):
                raise TypeError
            if isinstance(context, Belief | Goal):
                list_context = [context]
            if isinstance(context, Iterable):
                list_context = context
                for ctxt in list_context:
                    if isinstance(ctxt, Belief | Goal):
                        continue
                    else:
                        raise Exception(f'Invalid type {type(ctxt)}:{ctxt} - was expecting Belief or Goal')
            
            event = Event(change,data)
            plan = Plan(event,list_context,self.func)
            try:
                instance._plans += [plan]
            except AttributeError:
                instance._plans = [plan]
    return decorator

class Agent:
    def __init__(
        self,
        name: str = "",
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
        self.cycle_log: Dict[int, tuple] = dict()
        
        from maspy.admin import Admin
        self.unique: bool = False
        if name is None:
            name = ""
        self.my_name: tuple[str, int] = (name, 0)
        Admin().add_agents(self)
        self.str_name = '_'.join([self.my_name[0],str(self.my_name[1])])
        
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
        
        # self._learning_models: Dict[str, Learning] = dict()
        #, "Learning":self._learning_models}

        self.max_intentions: int = nax_intentions
        self.last_intention: tuple[Plan, tuple] = (Plan(), tuple())
        self.__intentions: list[tuple[Plan, tuple]] = []
        self.__supended_intentions: list[tuple[Plan, tuple, str, Event | None]] = []
        self.__running_intentions: list[tuple[Plan, tuple]] = []
        
        
        self.__events: List[Event] = []
        self.last_event: Event | None = None
        self.__beliefs: Dict[str | tuple[str, int], Dict[str, Set[Belief]]] = dict()
        self.__goals: Dict[str | tuple[str, int], Dict[str, Set[Goal]]] = dict()
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
        self.last_plan: Plan | None = None

        self.instant_mail = instant_mail
        self.read_all_mail = read_all_mail
        self.last_msg: tuple[str, str | List[str], Act.name, MSG] | None = None
        self.connect_to(Channel())
        self.paused_agent = False

    def start(self):
        self.reasoning()
    
    def print(self,*args, **kwargs):
        if self.unique:
            return print(f"Agent:{self.my_name[0]}>",*args,**kwargs)
        else:
            return print(f"Agent:{self.str_name}>",*args,**kwargs)
        
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
    
    @property
    def get_info(self):
        beliefs = manual_deepcopy(self.__beliefs)
        beliefs_list = []
        for sources_dict in beliefs.values():
            for belief_set in sources_dict.values():
                for belief in belief_set:
                    beliefs_list.append(belief)
                    
        goals = manual_deepcopy(self.__goals)
        goals_list = []
        for group_keys in goals.values():
            for goal_set in group_keys.values():
                for goal in goal_set:
                    goals_list.append(goal)
        
        return {"beliefs": beliefs_list, "goals": goals_list,  "intentions": self.__intentions.copy(), "running_intention": self.__running_intentions.copy(), "last_intention": self.last_intention, "connected_envs": list(self._environments.keys()).copy(), "connected_chs": list(self._channels.keys()).copy()}
    
    def connect_to(self, target: Environment | Channel | str):
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
                    self._environments[target._my_name] = target
            case Channel():
                with self.lock:
                    self._channels[target._my_name] = target
            case _:
                raise Exception(f'Invalid type {type(target)}:{target} - was expecting Channel or Environment')
        
        target.add_agents(self)
        return target

    def disconnect_from(self, target: Channel | Environment):
        
        match target:
            case Environment():
                with self.lock:
                    target._rm_agent(self)
                    del self._environments[target._my_name]
            case Channel():
                with self.lock:
                    target._rm_agent(self)
                    del self._channels[target._my_name]
                
    def get_env(self, env_name: str):
        return self._environments[env_name]
    
    def add_plan(self, plan: Plan | List[Plan]):
        plans = self._clean_plans(plan)
        self._plans += plans

    def rm_plan(self, plan: Plan | List[Plan]):
        if type(plan) is list:
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
    
    def add(self, data_type: Belief | Goal | Iterable[Belief | Goal], synchronous: bool = True):
        if self.running is False:
            synchronous = False
        self.print(f"Adding {data_type}") if self.show_exec else ...
        cleaned_data = self._clean(data_type)
        
        for type_data, data in cleaned_data.items():
            if len(data) == 0: 
                continue
            type_base = self._get_type_base(type_data)
            if isinstance(type_base,dict):
                merge_dicts(data,type_base)
        
        self._new_event(gain,data_type,synchronous)
    
    def rm(self, data_type: Belief | Goal | Iterable[Belief | Goal], synchronous: bool = True):
        if self.running is False:
            synchronous = False
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
                
        self._new_event(lose,data_type,synchronous)

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
            if caller_function_name in {'_retrieve_plans','recieve_msg','_select_plan'}:
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
            
            intention: tuple[Plan, tuple]
            
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
            #self.print("rm ",self.__running_intentions)
            self.__running_intentions.remove(intention)
            self.__supended_intentions.append(intention_reason)
        
        intention[0].ev_ctrl.wait(timeout)
        
        with self.lock:
            self.__supended_intentions.remove(intention_reason)

        while len(self.__running_intentions) > self.max_intentions:
            sleep(0.01)
        with self.lock:
            self.__running_intentions.append(intention)
            #sleep(0.1)
        #self.print("add ",self.__running_intentions)
    
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
            if isinstance(arg1,str) and (arg1[0].isupper()):
                #if arg1 == arg2 and :
                continue
            elif isinstance(arg2,str) and (arg2[0].isupper()):
                continue
            elif arg1 == arg2:
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
            if msg_act.name in [Act.askOneReply, Act.askAllReply]:
                with self.lock:
                    assert isinstance(msg, Belief | Goal)
                    msg = Ask(msg, self.str_name)
                    
                self._channels[channel]._send(self.str_name,target,msg_act,msg)
                self.last_msg = (self.str_name,target,msg_act.name,msg)
                msg.reply_event.wait()
                
                if msg.reply_content is not None:
                    self.add(msg.reply_content, False)
                    return msg.reply_content
                else:
                    self.print(f"Timeout while waiting for reply for {msg}")
                    return None
            else:
                self._channels[channel]._send(self.str_name,target,msg_act,msg)
                self.last_msg = (self.str_name,target,msg_act.name,msg)
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
        match act:
            case Act.tell:
                assert isinstance(msg, Belief),f'Act tell must receive Belief not {type(msg).__qualname__}'
                self.add(msg, False)
                
            case Act.achieve:
                assert isinstance(msg, Goal),f'Act achieve must receive Goal not {type(msg).__qualname__}'
                self.add(msg, False)
                
            case Act.untell:
                assert isinstance(msg, Belief),f'Act untell must receive Belief not {type(msg).__qualname__}'
                self.rm(msg, False)
                
            case Act.unachieve:
                assert isinstance(msg, Goal),f'Act unachieve must receive Goal not {type(msg).__qualname__}'
                self.rm(msg, False)
                
            case Act.askOne:
                assert isinstance(msg, Ask), f'Act askOne must request an Ask not {type(msg).__qualname__}'
                found_data = self.get(msg.data_type,ck_src=False)
                assert isinstance(found_data, Belief)
                self.send(msg.source, Act.tell, found_data)
            
            case Act.askOneReply:
                assert isinstance(msg, Ask), f'Act askOneReply must request an Ask not {type(msg).__qualname__}'
                found_data = self.get(msg.data_type,ck_src=False)
                assert isinstance(found_data, Belief)
                msg.reply_content = found_data
                msg.reply_event.set()
                
            case Act.askAll:
                assert isinstance(msg, Ask), f'Act askAll must request an Ask not {type(msg).__qualname__}'
                found_data = self.get(msg.data_type,all=True,ck_src=False)
                assert isinstance(found_data, list)
                for data in found_data:
                    assert isinstance(data, Belief)
                    self.send(msg.source, Act.tell, data)
                    
            case Act.askAllReply:
                assert isinstance(msg, Ask), f'Act askAllReply must request an Ask not {type(msg).__qualname__}'
                found_data = self.get(msg.data_type,all=True,ck_src=False)
                assert isinstance(found_data, list)
                msg.reply_content = cast(List[Belief|Goal], found_data)
                msg.reply_event.set()
                    
            case Act.tellHow:
                assert isinstance(msg, Plan), f'Act tellHow must receive a Plan not {type(msg).__qualname__}'
                self.add_plan(msg)

            case Act.untellHow:
                assert isinstance(msg, Plan), f'Act untellHow must receive a Plan not {type(msg).__qualname__}'
                self.rm_plan(msg)

            case Act.askHow:
                assert isinstance(msg, Ask), f'Act askHow must request an Ask not {type(msg).__qualname__}'
                found_plans = self.get(Plan(Event(test,msg.data_type)),all=True,ck_chng=False)
                assert isinstance(found_plans, list)
                for plan in found_plans:
                    assert isinstance(plan, Plan)
                    self.send(msg.source, Act.tellHow, plan)
            case _:
                TypeError(f"Unknown type of message {act}:{msg}")
    
    def find_in(self, 
            agent_name: str | List[str], 
            cls_type: str = "channel", 
            cls_name: str = "default", 
            cls_instance: Environment | Channel | None = None
        ) -> dict | Set[tuple] | None:
        if isinstance(cls_type, str) and cls_type != "channel":
            cls_type = cls_type.lower()
            if cls_type in _type_env_set:
                cls_type = "environment"
            elif cls_type in _type_ch_set:
                cls_type = "channel"
            else:
                return None               
            
        agents: Dict[str, Dict[str, Set[tuple]]]
        if cls_instance:
            agents = manual_deepcopy(cls_instance.agent_list)
        else:
            try:
                agents = manual_deepcopy(self._dicts[cls_type.lower()][cls_name].agent_list)
            except KeyError as ke:
                self.print(f"Not connected to {cls_type}:{cls_name}:{ke}")
                return None
        
        match agent_name:
            case list():
                assert len(agent_name) == 2, "Agent name list must be two: [class name and instance name]"
                agt_dict = agents[agent_name[0]]
                return agt_dict[agent_name[1]]
            case str():
                return agents[agent_name]
            case _:
                return None
            
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
                    return method(self.str_name, *args, **kwargs)
                return wrapper
        raise AttributeError(f"{self.str_name} doesnt have the method '{name}' and is not connected to any environment with the method '{name}'.")
    
    def reasoning(self) -> None:
        self.running = True
        self.stop_flag = threading.Event()
        self.thread = threading.Thread(target=self.cycle,args=(self.stop_flag,))
        self.thread.start()
    
    def stop_cycle(self, log_flag=False) -> None:
        self.print("Shutting Down...") if log_flag else ...
        self.running = False
        if self.stop_flag is not None:
            self.stop_flag.set()
        self.paused_agent = True
        
            
    def cycle(self, stop_flag: threading.Event) -> None:
        cycle_counter = 0
        while not stop_flag.is_set():   
            self.print("#### New cycle ####") if self.show_cycle else ...
            self._perception()   
            self._mail() 
            self.print(f"Last sent Message: {self.last_msg}") if self.show_cycle else ... 
            event = self._select_event()
            self.print(f"Selected event: {event} in {self.__events} (last event: {self.last_event})") if self.show_cycle else ...
            plans = self._retrieve_plans(event)
            self.print(f"Selected plans: {plans} in {self._plans}") if self.show_cycle else ...
            chosen_plan, args = self._select_intention(plans,event)
            self.print(f"Selected intention to run: {chosen_plan} with {args} arguments (last intention: {self.last_intention})") if self.show_cycle else ...
            
            #self.cycle_log[cycle_counter] = (self.last_msg, event, self.last_event, plans, chosen_plan, args)
            #cycle_counter += 1
            
            if stop_flag.is_set():
                break
            self._execute_plan(chosen_plan, event, args)
            self.print("#### End of cycle ####") if self.show_cycle else ...
            if self.delay: 
                sleep(self.delay)
    
    def _perception(self) -> None:
        percept_dict: Dict[str, dict] = dict()
        with self.lock:
            for env_name in self._environments:
                self.print(f"Percepting '{env_name}'") if self.show_cycle and not self.show_prct else ...
                percepts = self._environments[env_name].perception()
                self.print(f"Percepting {env_name} : {percepts}") if self.show_prct else ...
                merge_dicts(percepts,percept_dict)
            belief_dict: Dict[str, Dict[str, Set[Belief]]] = self._percepts_to_beliefs(percept_dict)
            self._revise_beliefs(belief_dict)
    
    def perceive(self, env_name: str | List[str]) -> None:
        if env_name == "all":
            self._perception()
            return
        
        percept_dict: Dict[str, dict] = dict()
        if isinstance(env_name, list):
            for name in env_name:
                try:
                    percepts = self._environments[name].perception()
                    self.print(f"Percepting '{name}'") if not self.show_prct else self.print(f"Percepting '{name}'")
                    merge_dicts(percepts,percept_dict)
                except KeyError:
                    self.print(f"Not Connected to Environment:{name}")
        else:
            try:
                percept_dict = self._environments[env_name].perception()
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
        self.last_event = event
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
            self._run_plan(plan,event.data,args,True)
        elif type(event.data) is Goal:
            self.print(f"Found no applicable plan for {event.change.name}:{event.data}")
    
    def _retrieve_plans(self, event: Event | None) -> List[Plan] | None: 
        if event is None: 
            return None
        retrieved = self.get(Plan,event,all=True,ck_src=False)
        assert isinstance(retrieved, list | None), f"Unexpected Retrieved Plan: {type(retrieved)}, Expected List[Plan] | None"
        return cast(List[Plan] | None, retrieved) 
    
    def _select_intention(self, plans: List[Plan] | None, event: Event | None) -> tuple[Plan, tuple] | tuple[None, tuple]:
        if plans is None:
            if event is not None and isinstance(event.data,Goal):
                self.print(f"No applicable Plan found for {event}")
            try:
                plan, args = self.__intentions.pop(0)
                return plan, args
            except IndexError:
                return None, tuple()
        while plans:
            plan = plans.pop(0)
            ctxt = self._retrieve_context(plan)
            if ctxt is not None:
                self.__intentions.append((plan,ctxt))
                break 
        try:
            plan, args = self.__intentions.pop(0)
            return plan, args
        except IndexError:
            self.print(f"Found no applicable plan for {event.change.name}:{event.data}") if self.show_exec and event is not None else ...
            return None, tuple()
    
    def _retrieve_context(self, plan: Plan) -> tuple | None:
        args: tuple = tuple()
        for context in plan.context:
            ctxt = self.get(context,ck_src=False) # Returns the first context variable found
            if ctxt is None: 
                break
            assert isinstance(ctxt, Belief | Goal), f"Unexpected Context Type: {type(ctxt)}, Expected Belief | Goal" 
            for x in ctxt._args:
                args += (x,)  
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
    
    def _execute_plan(self, chosen_plan: Plan | None, event: Event | None, args: tuple[Any, ...]):
        if not chosen_plan or len(self.__running_intentions) >= self.max_intentions:
            return None
        try:
            assert event is not None
            plan_thread = threading.Thread(target=self._run_plan, args=(chosen_plan,event.data,args))
            self.__running_intentions.append((chosen_plan, args))
            plan_thread.start()
            
        except RunPlanError:
            self.print(f"{chosen_plan} failed")

    def _run_plan(self, plan: Plan, trigger: Belief | Goal, args: tuple, instant_flag: bool = False):
        self.print(f"Running {plan}")  if self.show_exec or self.show_cycle else ...
        try:
            result = plan.body(self, trigger.source, *trigger._args, *args)
            if not instant_flag:
                self.__running_intentions.remove((plan, args))
                self.last_intention = (plan, args)
            if type(trigger) is Goal:
                self.__goals[trigger.source][trigger.key].remove(trigger)
            self.last_plan = plan
            return result
        except Exception as e:
            self.print(f"Error while executing {plan}:\n\tTrigger={trigger} | Context={args}\n\t{repr(e)}")
            _, _, exc_traceback = sys.exc_info()
            tb_entries = traceback.extract_tb(exc_traceback)
            
            excluded_files = ['agent.py', 'communication.py', 'admin.py', 'environment.py']
            
            filtered_entries = [
                entry for entry in tb_entries 
                if not any(excluded_file in entry.filename for excluded_file in excluded_files)
            ]
            
            if filtered_entries:
                buffer = "  Filtered Traceback (most recent call last):\n"
                for entry in filtered_entries:
                    buffer +=f'  File "{entry.filename}", line {entry.lineno}, in {entry.name}\n'
                    if entry.line:
                        buffer += f'    {entry.line}'
                print(buffer)
            else:
                print("No matching traceback entries found.")
            exit(1) 
            

    # TODO: implement stoping plan
    def _stop_plan(self, plan):
        self.print(f"Stoping {plan})")  if self.show_exec else ...
        pass    
    
    # TODO: should invalid arguments be an error or a warning?
    def _clean(
        self, data_type: Iterable[Belief | Goal] | Belief | Goal 
    ) -> Dict:
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

