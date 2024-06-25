import threading
from dataclasses import dataclass, field
from maspy.environment import Environment
from maspy.communication import Channel
#from maspy.learning.core import Learning
from maspy.error import (
    InvalidBeliefError,
    InvalidPlanError,
    RunPlanError,
)
from maspy.utils import set_changes, merge_dicts, manual_deepcopy
from typing import TypeVar, List, Optional, Dict, Set, Any, Union
from collections.abc import Iterable, Callable
from time import sleep
import importlib as implib
import inspect
import traceback
import sys

gain = TypeVar('gain')
lose = TypeVar('lose')
test = TypeVar('test')

DEFAULT_SOURCE = "self"
DEFAULT_CHANNEL = "default"

@dataclass(eq=True, frozen=True)
class Belief:
    key: str
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

    # implementing hash for Belief is fine, it is impossible to change something inside
    # without creating a new object therefore, Belief can be used in dict and sets
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
        return f"Belief{self.key,self.args,self.source}"
    
    def __repr__(self):
        return self.__str__()

@dataclass
class Goal:
    key: str
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
    change: str | TypeVar
    data: Belief | Goal 
    intention: str = "" # not implemented
    
    def __post_init__(self):
        if type(self.change)==TypeVar: 
            self.change = self.change.__name__ 
    
    def __str__(self) -> str:
        return f"Event({self.change}, {self.data})"
    
    def __repr__(self):
        return self.__str__()
    
@dataclass
class Plan:
    trigger: Event
    context: list[Belief | Goal] = field(default_factory=list)
    body: Callable = lambda _: {}
    
    def __str__(self) -> str:
        return f"Plan({self.trigger}, {self.context}, {self.body.__name__}() )"
    
    def __repr__(self):
        return self.__str__()
    
@dataclass
class Ask:
    data_type: Belief | Goal
    reply: list = field(default_factory=list)
    source: str = "unknown"

MSG = Belief | Ask | Goal | Plan | List[Belief | Ask | Goal | Plan]

_type_env_set = {Environment, "environment", "envrmnt", "env"}
_type_ch_set = {Channel, "channel", "chnnl", "ch", "c"}

def pl(change, data: Belief | Goal, context: Belief | Goal | list[Belief | Goal] = []):
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
        name: Optional[str] = None,
        beliefs: Optional[Iterable[Belief] | Belief] = None,
        goals: Optional[Iterable[Goal] | Goal] = None,
        show_exec = False,
        show_cycle = False,
        show_prct = False,
        show_slct = False,
        log_type = "Default",
        instant_mail = False
    ):              
        self.show_exec = show_exec
        self.show_cycle = show_cycle
        self.show_prct = show_prct
        self.show_slct = show_slct
        self.log_type = log_type
        
        from maspy.admin import Admin
        self.my_name: Optional[str | tuple] = name
        Admin().add_agents(self)
        
        self.delay: Optional[int|float] = None
        self.stop_flag: threading.Event | None = None
        self.running = False
        self.thread: threading.Thread | None = None
        self.saved_msgs: List = []
        
        self._ml_models: List = []
        self.policies: List = []
        
        self._name = f"Agent:{self.my_name}"
        
        self._environments: dict[str, Environment] = dict()
        self._channels: dict[str, Channel] = dict()
        self._dicts: dict[str, Union[dict[str, Environment], dict[str, Channel]]] = {"environment":self._environments, "channel":self._channels}
        
        # self._learning_models: Dict[str, Learning] = dict()
        #, "Learning":self._learning_models}

        self.__events: List[Event] = []
        self.__beliefs: Dict[str, Dict[str, Set[Belief]]] = dict()
        self.__goals: Dict[str, Dict[str, Set[Goal]]] = dict()
        if beliefs: 
            self.add(beliefs)
        if goals: 
            self.add(goals)
            
        self._plans: List[Plan]
        try:    
            if not self._plans:
                self._plans = []
        except AttributeError:
            self._plans = []
        
        self.instant_mail = instant_mail
        self.connect_to(Channel())
        self.paused_agent = False
        
        #self.strategies: Dict[str, Dict] = dict()
         

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
    
    def connect_to(self, target: Environment | Channel | str):
        if isinstance(target, str):
            classes = []
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
                self._environments[target._my_name] = target
            case Channel():
                self._channels[target._my_name] = target
            case _:
                raise Exception(f'Invalid type {type(target)}:{target} - was expecting Channel or Environment')
        
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
    
    def add_plan(self, plan: list[Plan] | Plan):
        plans = self._clean_plans(plan)
        self._plans += plans

    def rm_plan(self, plan: Plan):
        self._plans.remove(plan)
    
    def _new_event(self,change: str,data: Belief | Goal | Iterable[Belief | Goal], intention=None):
        if isinstance(data, Iterable):
            for dt in data:
                if isinstance(dt,Belief) and not dt.adds_event: 
                    continue
                self.print(f"New Event: {change},{dt}")  if self.show_exec else ...
                self.__events.append(Event(change,dt,intention))
        else:
            assert isinstance(data, Belief | Goal)
            if isinstance(data,Belief) and not data.adds_event: 
                return
            self.print(f"New Event: {change},{data}")  if self.show_exec else ...
            self.__events.append(Event(change,data,intention))
    
    def _get_type_base(self, 
            data_type: Belief | Goal | Plan | Event
        ) -> Union[dict[str, dict[str, set[Belief]]],
                dict[str, dict[str, set[Goal]]],
                list[Plan], list[Event]] | None:
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
    
    def add(self, data_type: Belief | Goal | Iterable[Belief | Goal]):
        
        self.print(f"Adding {data_type}") if self.show_exec else ...
        cleaned_data = self._clean(data_type)
        
        for type_data, data in cleaned_data.items():
            if len(data) == 0: 
                continue
            type_base = self._get_type_base(type_data)
            if isinstance(type_base,dict):
                merge_dicts(data,type_base)
            
        self._new_event("gain",data_type)
                 
    def rm(self, data_type: Belief | Goal | Iterable[Belief | Goal]):
        self.print(f"Removing {data_type}") if self.show_exec else ...
        
        if not isinstance(data_type, Iterable): 
            data_type = [data_type]
            
        for typ in data_type:
            type_base = self._get_type_base(typ)
            assert isinstance(typ, Belief | Goal), f"\nUnexpected type {type(typ)}, expected Belief | Goal"
            assert isinstance(type_base,dict), f'\nUnexpected type {type(type_base)}, expected dict'
            type_base[typ.source][typ.key].remove(typ) # type: ignore
        
        self._new_event("lose",data_type)

    def has(self, data_type: Belief | Goal | Plan | Event):
        return self.get(data_type) is not None

    def get(self, data_type: Belief | Goal | Plan | Event,
        search_with:  Optional[Belief | Goal | Plan | Event] = None,
        all = False, ck_chng=True, ck_type=True, ck_args=True, ck_src=True
    ) -> List[Belief | Goal | Plan | Event] | Belief | Goal | Plan | Event | None:
        if type(data_type) is type: 
            data_type = data_type("_")
        type_base = self._get_type_base(data_type)
        if type_base is None:
            return None
        if search_with is None: 
            search_with = data_type

        change, data = self._to_belief_goal(search_with)
        
        found_data: list[Belief | Goal | Plan | Event] = []
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
                self.print(f'Unable to get {type(data_type).__qualname__} like {data_type} during {caller_function_name}()')
            else:
                self.print(f'Unable to get {type(data_type).__qualname__} like {search_with} during {caller_function_name}()')
            return None

    def _to_belief_goal(self, data_type: Belief | Goal | Plan | Event):
        change: Optional[str | TypeVar] = None
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
        if ck_type and type(data1) != type(data2):
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
                      
    def _run_plan(self, plan: Plan, trigger: Belief | Goal, args: tuple):
        self.print(f"Running {plan}")  if self.show_exec or self.show_cycle else ...
        try:
            return plan.body(self, trigger.source, *trigger._args, *args)
        except Exception as e:
            self.print(f"Error while executing {plan}:\n\ttrigger={trigger}  |  args={args}  |  Error={repr(e)}")
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
    
    def send(self, target: str | tuple | List, act: TypeVar, msg: MSG, channel: str = DEFAULT_CHANNEL):  
        if isinstance(target,str): 
            target = (target,1) 
        try:
            assert isinstance(self.my_name, tuple)
            self._channels[channel]._send(self.my_name,target,act,msg)
        except KeyError:
            self.print(f"Not Connected to Selected Channel:{channel}")
        except AssertionError:
            raise
    
    def save_msg(self, act: TypeVar | str, msg: MSG) -> None:
        if self.instant_mail: 
            try:
                self.recieve_msg(act,msg)
            except AssertionError:
                raise
        else:
            self.saved_msgs.append((act,msg))

    def _mail(self, selection_function: str | Callable | None = "ALL") -> None:
        if callable(selection_function):
            selection_function(self.saved_msgs)
        else:
            while self.saved_msgs:
                act,msg = self.saved_msgs.pop()
                try:
                    self.recieve_msg(act,msg)
                except AssertionError as ae:
                    print(f"\t{repr(ae)}")
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    last_frame = traceback.extract_tb(exc_traceback)[-1]
        
                    # Format the last frame
                    formatted_last_frame = f"File \"{last_frame.filename}\", line {last_frame.lineno}, in {last_frame.name}\n  {last_frame.line}"
                    
                    # Print the formatted last frame
                    print("Error originated from:")
                    print(formatted_last_frame)
                if selection_function != "ALL":
                    break

    def recieve_msg(self, act: TypeVar | str, msg: MSG) -> None:
        #self.print(f"Received from {sender} : {act} -> {msg}")  if self.full_log else ...
        match act:
            case "tell":
                assert isinstance(msg, Belief),f'Act tell must receive Belief not {type(msg).__qualname__}'
                self.add(msg)
            case "achieve":
                assert isinstance(msg, Goal),f'Act achieve must receive Goal not {type(msg).__qualname__}'
                self.add(msg)
            case "untell":
                assert isinstance(msg, Belief),f'Act untell must receive Belief not {type(msg).__qualname__}'
                self.rm(msg)
            case "unachieve":
                assert isinstance(msg, Goal),f'Act unachieve must receive Goal not {type(msg).__qualname__}'
                self.rm(msg)

            case "askOne":
                assert isinstance(msg, Ask), f'Act askOne must request an Ask not {type(msg).__qualname__}'
                found_data = self.get(msg.data_type,ck_src=False)
                assert isinstance(found_data, Belief)
                self.send(msg.source, TypeVar('tell'), found_data)

            case "askAll":
                assert isinstance(msg, Ask), f'Act askAll must request an Ask not {type(msg).__qualname__}'
                found_data = self.get(msg.data_type,all=True,ck_src=False)
                assert isinstance(found_data, list)
                for data in found_data:
                    assert isinstance(data, Belief)
                    self.send(msg.source, TypeVar('tell'), data)

            case "tellHow":
                assert isinstance(msg, Plan), f'Act tellHow must receive a Plan not {type(msg).__qualname__}'
                self.add_plan(msg)

            case "untellHow":
                assert isinstance(msg, Plan), f'Act untellHow must receive a Plan not {type(msg).__qualname__}'
                self.rm_plan(msg)

            case "askHow":
                assert isinstance(msg, Ask), f'Act askHow must request an Ask not {type(msg).__qualname__}'
                found_plans = self.get(Plan(Event(TypeVar(''),msg.data_type)),all=True,ck_chng=False)
                assert isinstance(found_plans, list)
                for plan in found_plans:
                    assert isinstance(plan, Plan)
                    self.send(msg.source, TypeVar('tellHow'), plan)
            case _:
                TypeError(f"Unknown type of message {act}:{msg}")
    
    def find_in(self, 
            agent_name: str | list[str], 
            cls_type: str = "channel", 
            cls_name: str = "default", 
            cls_instance: Environment | Channel | None = None
        ) -> dict | set[tuple] | None:
        if isinstance(cls_type, str) and cls_type != "channel":
            cls_type = cls_type.lower()
            if cls_type in _type_env_set:
                cls_type = "environment"
            elif cls_type in _type_ch_set:
                cls_type = "channel"
            else:
                return None               
            
        agents: dict[str, dict[str, set[tuple]]]
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

    def send_msg(self, target: str, act: str, msg: MSG, channel: str):
        pass

    def reasoning(self) -> None:
        self.running = True
        self.stop_flag = threading.Event()
        self.thread = threading.Thread(target=self.cycle,args=(self.stop_flag,))
        self.thread.start()
    
    def stop_cycle(self) -> None:
        self.print("Shutting Down...")
        assert self.stop_flag is not None
        self.stop_flag.set()
        self.paused_agent = True
        self.running = False
            
    def cycle(self, stop_flag: threading.Event) -> None:
        while not stop_flag.is_set():   
            self.print("#### New cycle ####") if self.show_cycle else ...
            self._perception()   
            self._mail()  
            #self._strategy()
            event = self._select_event()
            self.print(f"Selected event: {event} in {self.__events}") if self.show_cycle else ...
            plans = self._retrieve_plans(event)
            self.print(f"Selected plans: {plans} in {self._plans}") if self.show_cycle else ...
            chosen_plan, args = self._select_plan(plans,event)
            self.print(f"Selected chosen_plan: {chosen_plan} with {args} arguments") if self.show_cycle else ...
            if stop_flag.is_set():
                break
            _ = self._execute_plan(chosen_plan,event,args)
            if self.delay: 
                sleep(self.delay)

    # def _strategy(self) -> None:
    #     for model_name in self._learning_models:
    #         self.print(f"Updating strategies '{model_name}'") if self.show_cycle else ...
    #         strategy = self._learning_models[model_name].strategy()
    #         self.strategies[model_name] = strategy 
    
    def _perception(self) -> None:
        percept_dict: dict[str, dict] = dict()
        for env_name in self._environments:
            self.print(f"Percepting '{env_name}'") if self.show_cycle and not self.show_prct else ...
            percepts = self._environments[env_name].perception()
            self.print(f"Percepting {env_name} : {percepts}") if self.show_prct else ...
            merge_dicts(percepts,percept_dict)
        belief_dict: dict[str, Dict[str, Set[Belief]]] = self._percepts_to_beliefs(percept_dict)
        self._revise_beliefs(belief_dict)
    
    def perceive(self, env_name: str | list[str]) -> None:
        if env_name == "all":
            self._perception()
            return
        
        percept_dict: dict[str, dict] = dict()
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
                self.print(f"Percepting '{env_name}'") if not self.show_prct else self.print(f"Percepting '{env_name}' : {percept_dict}")
            except KeyError:
                self.print(f"Not Connected to Environment:{env_name}")
        
        belief_dict = self._percepts_to_beliefs(percept_dict)
        self._revise_beliefs(belief_dict)
    
    def _percepts_to_beliefs(self,percepts: dict) -> dict:
        # TODO make use of percepts group
        for source, keys in percepts.copy().items():
            for key,percepts_set in keys.items():
                belief_set = set()
                for percept in percepts_set:
                    belief_set.add(Belief(percept.key,percept.args,source,percept.adds_event))
                percepts[source][key] = belief_set
        return percepts
     
    def _revise_beliefs(self, belief_dict: dict[str, Dict[str, Set[Belief]]]) -> None:
        for source, keys in self.__beliefs.copy().items():
            if source == DEFAULT_SOURCE: 
                continue # Does not remove "self"
            if type(source) == tuple: 
                continue # Does not remove messages
            if source in belief_dict:
                for key, beliefs in keys.copy().items():
                    if key in belief_dict[source]: 
                        new, gain, lose = set_changes(beliefs,belief_dict[source][key])
                        self.__beliefs[source][key] = new
                        self._new_event("gain",gain) # Gained new specific belief
                        self._new_event("lose",lose) # Lost an old specific belief
                        del belief_dict[source][key]
                        if self.show_prct and gain:
                            self.print(f"Specific Beliefs gained in revision: {gain}")
                        if self.show_prct and lose:
                            self.print(f"Specific Beliefs lost in revision: {lose}") 
                    else:
                        self._new_event("lose",self.__beliefs[source][key]) # Lost whole key belief
                        self.print(f"Key Beliefs lost in revision: {self.__beliefs[source][key]}") if self.show_prct else ...
                        del self.__beliefs[source][key]
                        
                if belief_dict[source] == {}:
                    del belief_dict[source]
            else:
                for beliefs in keys.values():
                    self.print(f"{source} Beliefs lost in revision: {beliefs}") if self.show_prct and beliefs else ...
                    self._new_event("lose",beliefs) # Lost whole source of belief (env)
                del self.__beliefs[source]
        
        for source,keys in belief_dict.items():
            for beliefs in keys.values():
                self.print(f"Rest of {source} Beliefs gained in revision: {beliefs}") if self.show_prct and beliefs else ...
                self._new_event("gain",beliefs) # Gained beliefs of new sources/keys
                
        self.print(f"Updating beliefs: {belief_dict}") if self.show_prct else ...
        merge_dicts(belief_dict,self.__beliefs)
    
    def _select_event(self) -> Event | None:
        if self.__events == []: 
            return None
        return self.__events.pop(0)
    
    def _retrieve_plans(self, event) -> List[Plan] | None: 
        if event is None: 
            return None
        return self.get(Plan,event,all=True,ck_src=False) # type: ignore
    
    def _select_plan(self, plans: list[Plan] | None, event: Event | None) -> tuple[Plan, tuple] | tuple[None, tuple]:
        if plans is None:
            if event is not None and isinstance(event.data,Goal):
                self.print(f"No applicable Plan found for {event}")
            return None, tuple()
        
        args: tuple = tuple()
        for plan in plans:
            assert isinstance(plan, Plan), f"Unexpected Type: {type(plan)}, Expected Plan"
            for context in plan.context:
                ctxt = self.get(context,ck_src=False)
                if not ctxt:
                    break
                assert isinstance(ctxt, Belief | Goal), f"Unexpected Context Type: {type(ctxt)}, Expected Belief | Goal" 
                for x in ctxt._args:
                    args += (x,)
            else:    
                return plan, args
        self.print(f"Found no applicable plan for {event.change}:{event.data}") if self.show_exec and event is not None else ...
        return None, tuple()
    
    def _execute_plan(self, chosen_plan: Plan | None, event: Event | None, args: tuple[Any, ...]) -> Any | None:
        if not chosen_plan:
            return None
        try:
            assert event is not None
            return self._run_plan(chosen_plan,event.data,args)
        except RunPlanError:
            self.print(f"{chosen_plan} failed")
            return None

    # TODO: should invalid arguments be an error or a warning?
    def _clean(
        self, data_type: Iterable[Belief | Goal] | Belief | Goal 
    ) -> Dict:
        type_dicts: dict = {Belief: dict(), Goal: dict()}
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

