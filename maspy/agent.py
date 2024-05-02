import threading
from dataclasses import dataclass, field
from maspy.environment import Environment
from maspy.communication import Channel
from maspy.error import (
    InvalidBeliefError,
    InvalidPlanError,
    RunPlanError,
)
from maspy.utils import utils
from typing import TypeVar, List, Optional, Dict, Set, Tuple, Any
from collections.abc import Iterable, Callable
from time import sleep
import importlib as implib
import inspect

gain = TypeVar('gain')
lose = TypeVar('lose')
test = TypeVar('test')

DEFAULT_SOURCE = "self"
DEFAULT_CHANNEL = "default"

@dataclass(eq=True, frozen=True)
class Belief:
    key: str
    _args: tuple = field(default_factory=tuple)
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

    def update(self, key: str = None, args=None, source=None) -> "Belief":
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

    # implementing hash for Belief is fine, it is impossible to change something inside
    # without creating a new object therefore, Belief can be used in dict and sets
    def __hash__(self) -> int:
        args_hashable = []
        unhashable_types = {}
        for arg in self._args:
            arg_dict = type(arg).__dict__
            if arg_dict.get("__hash__"):
                args_hashable.append(arg)
            elif isinstance(arg, (List, Dict, Set)):
                args_hashable.append(repr(arg))
            else:
                raise TypeError(f"Unhashable type: {type(arg)}")
        args_hashable = tuple(args_hashable)

        return hash((self.key, args_hashable, self.source))
    
    def __str__(self) -> str:
        return f"Belief{self.key,self.args,self.source}"

@dataclass
class Goal:
    key: str
    _args: tuple = field(default_factory=tuple)
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

    def update(self, key: str = None, args=None, source=None) -> "Goal":
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
        unhashable_types = {}
        for arg in self._args:
            arg_dict = type(arg).__dict__
            if arg_dict.get("__hash__"):
                args_hashable.append(arg)
            elif isinstance(arg, (List, Dict, Set)):
                args_hashable.append(repr(arg))
            else:
                raise TypeError(f"Unhashable type: {type(arg)}")
        args_hashable = tuple(args_hashable)

        return hash((self.key, args_hashable, self.source))
    
    def __str__(self) -> str:
        return f"Goal{self.key,self.args,self.source}"
    
@dataclass
class Event:
    change: str # ( + or add, - or rm, ~ or test )
    data: Belief | Goal 
    intention: str = None # still don't understand how it works
    
    def __post_init__(self):
        if type(self.change)==TypeVar: self.change = self.change.__name__ 
    
    def __str__(self) -> str:
        return f"Event{self.change,self.data,self.intention}"
    
@dataclass
class Plan:
    trigger: Event
    context: list = field(default_factory=list)
    body: Callable = None
    
    def __str__(self) -> str:
        return f"Plan{self.trigger,self.context,self.body.__name__}"
    
@dataclass
class Ask:
    data_type: Belief | Goal | str
    reply: list = field(default_factory=list)
    source: str = "unknown"

MSG = Belief | Ask | Goal | Plan

_type_env_set = {Environment, "environment", "envrmnt", "env"}
_type_ch_set = {Channel, "channel", "chnnl", "ch", "c"}

def pl(change, data: Belief | Goal, context: Belief | Goal | Iterable = []):
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
        name: str = None,
        beliefs: Optional[Iterable[Belief] | Belief] = None,
        goals: Optional[Iterable[Goal] | Goal] = None,
        full_log = False,
        show_cycle = False,
        show_prct = False,
        show_slct = False,
        log_type = "Default",
        instant_mail = False
    ):              
        self.full_log = full_log
        self.show_cycle = show_cycle
        self.show_prct = show_prct
        self.show_slct = show_slct
        self.log_type = log_type
        
        from maspy.admin import Admin
        self.my_name = name
        Admin().add_agents(self)
        
        self.sleep = None
        self.stop_flag = None
        self.running = False
        self.thread = None
        self.saved_msgs = []
        
        self._name = f"Agent:{self.my_name}"
        
        self._environments: Dict[str, Environment] = dict()
        self._channels: Dict[str, Channel] = dict()

        self.__events: List[Event] = []
        self.__beliefs: Dict[str, Dict[str, Set[Belief]]] = dict()
        self.__goals: Dict[str, Dict[str, Set[Goal]]] = dict()
        if beliefs: self.add(beliefs)
        if goals: self.add(goals)
        
        self.instant_mail = instant_mail
        self.connect_to(Channel())
        self.paused_agent = False
        
        try: 
            self._plans
        except AttributeError:
            self._plans = []
         
        #self.print(f"Initialized") 

    def start(self):
        self.reasoning()
    
    def print(self,*args, **kwargs):
        return print(f"{self._name}>",*args,**kwargs)
    
    @property
    def print_beliefs(self):
        print("Beliefs:",self.__beliefs)

    @property
    def print_goals(self):
        print("Goals:",self.__goals)
    
    @property
    def print_plans(self):
        print("Plans:",self._plans)
    
    @property
    def print_events(self):
        print("Events:",self.__events)
    
    def connect_to(self, target: Channel | Environment | str, target_name: str = None):
        match target:
            case Environment():
                self._environments[target._my_name] = target
            case Channel():
                self._channels[target._my_name] = target
            case str():
                classes = []
                try:
                    imported = implib.import_module(target)
                except ModuleNotFoundError:
                    self.print(f"No File named '{target_name}'")
                    return
                for name, obj in inspect.getmembers(imported):
                    if inspect.isclass(obj) and name != "Environment" and name != "Channel":
                        lineno = inspect.getsourcelines(obj)[1]
                        classes.append((lineno, obj))
                    if name == "Environment":
                        connect_list = self._environments
                    if name == "Channel":
                        connect_list = self._channels
                classes.sort()
                target = classes[0][1](target_name)
                connect_list[target_name] = target
                del imported
                
        target.add_agents(self)
        return target

    def disconnect_from(self, target: Channel | Environment):
        match target:
            case Environment():
                del self._environments[target._my_name]
            case Channel():
                del self._channels[target._my_name]
                
    def get_env(self, env_name: str):
        return self._environments[env_name]
    
    def add_plan(self, plan: List[Plan | Tuple] | Plan | Tuple):
        plans = self._clean_plans(plan)
        self._plans += plans

    def rm_plan(self, plan: Plan):
        self._plans.pop(plan)
    
    def _new_event(self,change,data,intention=None):
        try:
            for dt in data:
                if isinstance(dt,Belief) and not dt.adds_event: continue
                self.print(f"New Event: {change}:{dt}")  if self.full_log else ...
                self.__events.append(Event(change,dt,intention))
        except(TypeError):
            if isinstance(data,Belief) and not data.adds_event: return
            self.print(f"New Event: {change}:{data}")  if self.full_log else ...
            self.__events.append(Event(change,data,intention))
    
    def _get_type_base(self, data_type):
        if data_type == Belief:
            return self.__beliefs
        elif data_type == Goal:
            return self.__goals
        elif data_type == Plan:
            return self._plans
        elif data_type == Event:
            return self.__events
        else:
            print(f"Type is neither Belief | Goal | Plan | Event : {data_type}")
            return None
    
    def add(self, data_type: Belief | Goal | Iterable[Belief | Goal]):
        self.print(f"Adding {data_type}") if self.full_log else ...
        cleaned_data = self._clean(data_type)
        
        for type_data, data in cleaned_data.items():
            if len(data) == 0: continue
            type_base = self._get_type_base(type_data)
            utils.merge_dicts(data,type_base)
            
        self._new_event("gain",data_type)
                 
    def rm(self, data_type: Belief | Goal | Iterable[Belief | Goal]):
        self.print(f"Removing {data_type}") if self.full_log else ...
        
        if not isinstance(data_type, Iterable): data_type = [data_type]
            
        for typ in data_type:
            type_base = self._get_type_base(type(typ))
            type_base[typ.source][typ.key].remove(typ)
        
        self._new_event("lose",data_type)

    def has(self, data_type: Belief | Goal | Plan | Event):
        return self.get(data_type) != None

    def get(self, data_type: Belief | Goal | Plan | Event,
        search_with:  Belief | Goal | Plan | Event = None,
        all = False, ck_chng=True, ck_type=True, ck_args=True, ck_src=True
    ) -> List[Belief | Goal | Plan | Event] | Belief | Goal | Plan | Event:
        if type(data_type) is type: data_type = data_type(0,0,0)
        type_base = self._get_type_base(type(data_type))
        if search_with is None: search_with = data_type

        change, data = self._to_belief_goal(search_with)
        
        found_data = []
        match data_type:
            case Belief() | Goal(): 
                for keys in type_base.values():
                    for values in keys.values():
                        for value in values:
                            if self._compare_data(value,data,ck_type,ck_args,ck_src):
                                found_data.append(value)
                                if not all: return value
                                
            case Plan() | Event(): 
                for plan_event in type_base:
                    chng, belf_goal = self._to_belief_goal(plan_event)
                    
                    if change and ck_chng and chng != change:
                        continue
                    if self._compare_data(belf_goal,data,ck_type,ck_args,ck_src):
                        found_data.append(plan_event)
                        if not all: return plan_event

            case _: pass
        return found_data if found_data else None

    def _to_belief_goal(self, data_type: Belief | Goal | Plan | Event):
        change = None
        belief_goal:Belief | Goal = None
        match data_type:
            case Belief() | Goal():
                belief_goal = data_type
            case Plan(): 
                change: str = data_type.trigger.change
                belief_goal = data_type.trigger.data
            case Event(): 
                change = data_type.change
                belief_goal = data_type.data
            case _: 
                self.print(f"Error in _to_belief_goal: {type(data_type)}:{data_type}")
                return None, None
        return change,belief_goal
    
    def _compare_data(self, data1, data2, ck_type,ck_args,ck_src):
        self.print(f"Comparing: \n\t{data1} and {data2}") if self.show_slct else ...
        if ck_type and type(data1) != type(data2):
            self.print("Failed at type") if self.show_slct else ...
            return False
        if data1.key != data2.key:
            self.print("Failed at key") if self.show_slct else ...
            return False
        if ck_src and data2.source != DEFAULT_SOURCE and data1.source != data2.source:
            self.print("Failed at source") if self.show_slct else ...
            return False
        if not ck_args:
            return True
        if data1.args_len != data2.args_len:
            self.print("Failed at args_len") if self.show_slct else ...
            return False
        for arg1,arg2 in zip(data1._args,data2._args):
            if isinstance(arg1,str) and (arg1[0].isupper()):
                continue
            elif isinstance(arg2,str) and (arg2[0].isupper()):
                continue
            elif arg1 == arg2:
                continue
            else:
                self.print(f"Failed at args {arg1} x {arg2}") if self.show_slct else ...
                return False
        else:
            self.print("Data is Compatible") if self.show_slct else ...
            return True
                      
    def _run_plan(self, plan: Plan, trigger: Belief | Goal, args: tuple):
        self.print(f"Running {plan}")  if self.full_log else ...
        try:
            #self.print(f'running with {trigger._args} {args}')
            return plan.body(self, trigger.source, *trigger._args, *args)
        except KeyError:
            self.print(f"{plan} doesn't exist")
            raise RunPlanError

    # TODO: implement stoping plan
    def _stop_plan(self, plan):
        self.print(f"Stoping {plan})")  if self.full_log else ...
        pass
    
    def send(self, target: str | tuple | List, act: TypeVar, msg: MSG | str, channel: str = DEFAULT_CHANNEL):  
        if type(target) == str: target = (target,1) 
        try:
            self._channels[channel]._send(self.my_name,target,act,msg)
        except KeyError:
            self.print(f"Not Connected to Selected Channel:{channel}")
    
    def save_msg(self, act, msg):
        if self.instant_mail: 
            self.recieve_msg(act,msg)
        else:
            self.saved_msgs.append((act,msg))

    def _mail(self, selection_function="ALL"):
        if selection_function not in {None,"ALL"}:
            selection_function(self.saved_msgs)
        else:
            while self.saved_msgs:
                act,msg = self.saved_msgs.pop()
                self.recieve_msg(act,msg)
                if selection_function != "ALL":
                    break

    def recieve_msg(self, act, msg: MSG):
        #self.print(f"Received from {sender} : {act} -> {msg}")  if self.full_log else ...
        match act:
            case "tell" | "achieve":
                self.add(msg)

            case "untell" | "unachieve":
                self.rm(msg)

            case "askOne":
                found_data = self.get(msg.data_type,ck_src=False)
                self.send(msg.source, TypeVar('tell'), found_data)

            case "askAll":
                found_data = self.get(msg.data_type,all=True,ck_src=False)
                for data in found_data:
                    self.send(msg.source, TypeVar('tell'), data)

            case "tellHow":
                self.add_plan(msg)

            case "untellHow":
                self.rm_plan(msg)

            case "askHow":
                found_plans = self.get(Plan,msg.data_type,all=True)
                for plan in found_plans:
                    self.send(msg.source, TypeVar('tellHow'), plan)
            case _:
                TypeError(f"Unknown type of message {act}:{msg}")
    
    def find_in(self, agent_name, cls_type=None, cls_name=["env","default"], cls_instance=None):
        cls_type = cls_type.lower()
        try:
            if cls_instance:
                return cls_instance.agent_list[agent_name]
            if cls_type in _type_env_set:
                cls_name = cls_name[0] if type(cls_name) == list else cls_name  
                return self._environments[cls_name].agent_list[agent_name]
            if cls_type in _type_ch_set:
                cls_name = cls_name[1] if type(cls_name) == list else cls_name  
                return self._channels[cls_name].agent_list[agent_name]
        except KeyError as ke:
            self.print(f"Not connected to {cls_type}:{cls_name}:{ke}")
            
    def action(self,env_name):
        try:
            env = self._environments[env_name]
            #print(f"\n {env}   {Environment(env_name)}")
            return env
        except KeyError:
            self.print(f"Not Connected to Environment:{env_name}")

    def send_msg(self, target: str, act: str, msg: MSG, channel: str):
        pass

    def reasoning(self):
        #self.print(f"Starting Reasoning")
        self.running = True
        self.stop_flag = threading.Event()
        self.thread = threading.Thread(target=self.cycle,args=(self.stop_flag,))
        self.thread.start()
    
    def stop_cycle(self):
        self.print("Shutting Down...")
        self.stop_flag.set()
        self.paused_agent = True
        self.running = False
            
    def cycle(self, stop_flag):
        while not stop_flag.is_set():   
            self.print(f"#### New cycle ####") if self.show_cycle else ...
            self._perception()   
            self._mail()  
            event = self._select_event()
            self.print(f"Selected event: {event} in {self.__events}") if self.show_cycle else ...
            plans = self._retrieve_plans(event)
            self.print(f"Selected plans: {plans} in {self._plans}") if self.show_cycle else ...
            chosen_plan, args = self._select_plan(plans,event)
            self.print(f"Selected chosen_plan: {chosen_plan} with {args} arguments") if self.show_cycle else ...
            result = self._execute_plan(chosen_plan,event,args)
            if self.sleep: sleep(self.sleep)

    def _perception(self):
        percept_dict = dict()
        for env_name in self._environments:
            self.print(f"Percepting '{env_name}'") if self.show_cycle else ...
            percept_dict.update(self._environments[env_name].perception())
        percept_dict = self._percepts_to_beliefs(percept_dict)
        self._revise_beliefs(percept_dict)
    
    def _percepts_to_beliefs(self,percepts: dict) -> dict:
        # TODO make use of percepts group
        for source, keys in percepts.copy().items():
            for key,percepts_set in keys.items():
                belief_set = set()
                for percept in percepts_set:
                    belief_set.add(Belief(percept.key,percept.args,source,percept.adds_event))
                percepts[source][key] = belief_set
        return percepts
     
    def _revise_beliefs(self, percept_dict: dict):
        for source, keys in self.__beliefs.copy().items():
            if source == DEFAULT_SOURCE: continue # Does not remove "self"
            if type(source) == tuple: continue # Does not remove messages
            if source in percept_dict:
                for key, beliefs in keys.copy().items():
                    if key in percept_dict[source]: 
                        new, gain, lose = utils.set_changes(beliefs,percept_dict[source][key])
                        self.__beliefs[source][key] = new
                        self._new_event("gain",gain) # Gained new specific belief
                        self._new_event("lose",lose) # Lost an old specific belief
                        del percept_dict[source][key]
                        if self.show_prct:
                            self.print(f"Beliefs gained in revision: {gain}")
                            self.print(f"Beliefs lost in revision: {lose}") 
                    else:
                        self._new_event("lose",self.__beliefs[source][key]) # Lost whole key belief
                        self.print(f"Beliefs lost in revision: {self.__beliefs[source][key]}") if self.show_prct else ...
                        del self.__beliefs[source][key]
                        
                if percept_dict[source] == {}:
                    del percept_dict[source]
            else:
                for beliefs in keys.values():
                    self.print(f"Beliefs lost in revision: {beliefs}") if self.show_prct else ...
                    self._new_event("lose",beliefs) # Lost whole source of belief (env)
                del self.__beliefs[source]
        
        for keys in percept_dict.values():
            for beliefs in keys.values():
                self.print(f"Beliefs gained in revision: {beliefs}") if self.show_prct else ...
                self._new_event("gain",beliefs) # Gained beliefs of new sources/keys
        self.__beliefs.update(percept_dict)
    
    def _select_event(self):
        if self.__events == []: return None
        return self.__events.pop(0)
    
    def _retrieve_plans(self, event):
        if event is None: return None
        return self.get(Plan,event,all=True,ck_src=False)
    
    def _select_plan(self, plans, event:Event):
        if plans is None:
            self.print(f"No plans found for {event}") if self.show_cycle else ... 
            return None, None
        
        args = tuple()
        for plan in plans:
            for context in plan.context:
                ctxt = self.get(context,ck_src=False)
                if not ctxt:
                    break
                for x in ctxt._args:
                    args += (x,)
            else:    
                return plan, args
        self.print(f"Found no applicable plan for {event.change}:{event.data}") if self.full_log else ...
        return None, None
    
    def _execute_plan(self, chosen_plan:Plan, event: Event, args):
        if not chosen_plan:
            return None
        try:
            return self._run_plan(chosen_plan,event.data,args)
        except RunPlanError:
            self.print(f"{chosen_plan} failed")

    # TODO: should invalid arguments be an error or a warning?
    def _clean(
        self, data_type: Iterable[Belief | Goal] | Belief | Goal 
    ) -> Dict:
        type_dicts = {Belief: dict(), Goal: dict()}
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

                    type_dict = type_dicts[type(typ)]
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
        plans: Optional[Iterable[Plan] | Plan ],
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
                    if isinstance(plan,Tuple):
                        plan_list.append(Plan(*plan))
                        
                return plan_list
            case _:
                raise InvalidPlanError(
                    f"Expected plans to have type Dict[str, Callable] | Iterable[Tuple[str, Callable]] | Tuple(str, Callable), recieved {type(plans).__name__}"
                )

