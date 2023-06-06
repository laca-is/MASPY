import threading
from dataclasses import dataclass, field, astuple
from maspy.environment import Environment
from maspy.communication import Channel
from maspy.error import (
    InvalidBeliefError,
    InvalidObjectiveError,
    InvalidPlanError,
    RunPlanError,
)
from maspy.coordinator import Coordinator
from typing import List, Optional, Union, Dict, Set, Tuple, Any
from collections.abc import Iterable, Callable
from time import sleep
import importlib as implib
import inspect
import signal

@dataclass(eq=True, frozen=True)
class Belief:
    key: str
    _args: tuple = field(default_factory=tuple)
    source: str = "percept"

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

@dataclass
class Objective:
    key: str
    _args: tuple = field(default_factory=tuple)
    source: str = "percept"

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

    def weak_eq(self, other: "Objective"):
        return (
            self.key == other.key
            and len(self._args) == len(other._args)
            and self.source == other.source
        )

    def update(self, key: str = None, args=None, source=None) -> "Objective":
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

        return Objective(new_name, new_args, new_source)

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
    
@dataclass
class Plan:
    trigger: str
    context: list = field(default_factory=list)
    body: Callable = None
        
@dataclass
class Ask:
    belief: Belief
    reply: list = field(default_factory=list)
    source: str = "unknown"

MSG = Belief | Ask | Objective 

class Agent:
    def __init__(
        self,
        name: str,
        beliefs: Optional[Iterable[Belief] | Belief] = None,
        objectives: Optional[Iterable[Objective] | Objective] = None,
        plans: Optional[Iterable[Plan] | Plan] = None,
        full_log = False
    ):
        self.stop_flag = None
        self.thread = None
        
        self._type_belief_set = {Belief, "belief" , "belf" ,"blf", "bel" , "b"}
        self._type_objective_set = {Objective, "objective", "objtv", "obj", "ob", "o"}
        self._type_env_set = {Environment, "environment", "envrmnt", "env", "e"}
        self._type_ch_set = {Channel, "channel", "chnnl", "ch", "c"}
        self._data_types = {Belief,Objective,Ask,Plan}
        self.full_log = full_log
        
        self.my_name = name
        Coordinator().add_agents(self)
        self._name = f"Agent:{self.my_name}"
        
        self._environments: Dict[str, Any] = {}
        self._channels: Dict[str, Any] = {}

        self.__beliefs = self._clean(beliefs)
        self.__old_beliefs = self._clean(beliefs)
        self.__objectives = self._clean(objectives)
        self.__plans = self._clean_plans(plans)

        self.__default_channel = "comm"
        self.paused_agent = False
        self.print(f"Initialized")

    def print(self,*args, **kwargs):
        return print(f"{self._name}>",*args,**kwargs)

    def set_default_channel(self, channel):
        self.__default_channel = channel

    def connect(self, target: Channel | Environment | str, target_name: str = "default", role_on_env: str = None):
        match target:
            case Environment():
                self._environments[target._my_name] = [target,role_on_env]
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

    def add_focus_env(self, env_instance: Environment, role_on_env: str = None):
        self._environments[env_instance._my_name] = [env_instance,role_on_env]

    def add_focus(self, environment: str, env_name: str = 'env', role_on_env: str = None) -> Environment:
        classes = []
        try:
            env = implib.import_module(environment)
        except ModuleNotFoundError:
            self.print(f"No environment named '{env_name}'")
            return
        self._environments = {env_name: {}}
        for name, obj in inspect.getmembers(env):
            if inspect.isclass(obj) and name != "Environment":
                lineno = inspect.getsourcelines(obj)[1]
                classes.append((lineno, obj))
        classes.sort()
        self._environments[env_name] = classes[0][1](env_name)
        del env
        self.print(f"Connected to environment {env_name}")
        return self._environments[env_name]

    def rm_focus(self, environment: str):
        del self._environments[environment]

    def get_env(self, env_name: str):
        return self._environments[env_name]
    
    def add_plan(self, plan: List[Plan | Tuple] | Plan | Tuple):
        plans = self._clean_plans(plan)
        self.__plans += plans

    def rm_plan(self, plan: Plan):
        self.__plans.pop(plan)

    @property
    def print_beliefs(self):
        print("Beliefs:",self.__beliefs)

    @property
    def print_objectives(self):
        print("Objectives:",self.__objectives)
    
    @property
    def print_plans(self):
        print("Plans:",self.__plans)

    def has_close(
        self, 
        data_type: Belief | Objective | str,
        key: str, 
        args: int | Any = None, 
        source: str = None
    ):
        if self.search(data_type, key, args, source) is not None:
            return True
        return False 

    def has_objective(self, objective: Objective):
        return objective in self.__objectives.get(objective.source, {}).get(objective.key, {})

    def has_belief(self, belief: Belief):
        return belief in self.__beliefs.get(belief.source, {}).get(belief.key, {})
    
    def has_old_belief(self, belief: Belief):
        return belief in self.__old_beliefs.get(belief.source, {}).get(belief.key, {})
    
    def add(
        self, 
        data_type: Belief | Objective | str, 
        key: str = str(), 
        args: Any = tuple(), 
        source: str = "percept"
    ):
        self._central("add",data_type,key,args,source)
        
    def _adding(
        self, 
        type_base: Dict,
        data_type: Iterable[Belief | Objective] | Belief | Objective
    ):
        data_type = self._clean(data_type)
        self.print(f"Adding {data_type}") if self.full_log else ...
        for key, value in data_type.items():
            if key in type_base and isinstance(value, dict):
                for inner_key, inner_value in value.items():
                    if inner_key in type_base[key] and isinstance(inner_value, set):
                        type_base[key][inner_key].update(inner_value)
                    else:
                        type_base[key][inner_key] = inner_value 
            else:
                type_base[key] = value
                
    def rm(
        self, 
        data_type: Belief | Objective | str, 
        key: str = str(), 
        args: Any = tuple(), 
        source: str = "percept",
        purge_source = False
    ):
        if purge_source:
            self._central("rm-source",data_type,key,args,source)
        else:
            self._central("rm",data_type,key,args,source)

    def _removing(
        self, 
        type_base: Dict,
        data_type: Iterable[Belief | Objective] | Belief | Objective, 
        purge_source=False
    ):
        try:
            match data_type:
                case Iterable():
                    for typ in data_type:
                        try:
                            type_base[typ.source][typ.key].remove(typ)
                        except KeyError:
                            pass
                case _:
                    if purge_source:
                        del type_base[data_type.source]
                    else:
                        type_base[data_type.source][data_type.key].remove(data_type)
        except KeyError:
            self.print(f"{data_type} doesn't exist | purge({purge_source})")
      
    def search(
        self, data_type: Belief | Objective | str, 
        key: str = None, args: int | Any = None, 
        source: str = None,
        all = False
    ) -> Optional[Belief | Objective]:
        if all:
            return self._central("search-all",data_type,key,args,source)
        else:    
            return self._central("search",data_type,key,args,source)
                             
    def _searching(
        self,type_base: list,
        key: str, args: int | Any,
        source: str,
        all = False
    ) -> Optional[Belief | Objective]:
        found_data = []
        match(args,source):
            case None,None:
                for src in type_base:
                    for data_type in type_base[src].get(key, {}):
                        if data_type:
                            if all:
                                found_data.append(data_type)
                            else:
                                found_data = data_type
                                break
                    else:
                        continue
                    break
            
            case _,None:
                for src in type_base:
                    for data_type in type_base[src].get(key, {}):
                        if (type(args) is int and data_type.args_len == args)\
                            or data_type.args == args:
                            if all:
                                found_data.append(data_type)
                            else:
                                found_data = data_type
                                break
                    else:
                        continue
                    break
            
            case None,str():
                data_type = type_base.get(source, {}).get(key, {})
                if data_type:
                    if all:
                        found_data.append(data_type)
                    else:
                        found_data = data_type
            
            case _,str():
                for data_type in type_base.get(source, {}).get(key, {}):
                    if (type(args) is int and data_type and data_type.args_len == args)\
                        or (data_type and data_type.args == args):
                            if all:
                                found_data.append(data_type)
                            else:
                                found_data = data_type
                                break
            
        return found_data

    def _central(self,def_type,data_type,key,args,source):
        if type(data_type) is str:
            data_type = data_type.lower()
        elif type(data_type) is type:
            data_type = data_type.__name__.lower()
        elif type(data_type) is Belief or type(data_type) is Objective:
            key,args,source = (data_type.key,data_type.args,data_type.source)
            data_type = type(data_type)
        else:
            self.print(f"Error in Central Typing for {type(data_type)}:{data_type}")
            return None
        
        if data_type in self._type_belief_set:
            type_base = self.__beliefs
            data_type = Belief(key,args,source)
            
        elif data_type in self._type_objective_set:
            type_base = self.__objectives
            data_type = Objective(key,args,source)

        elif type(data_type) not in {Belief,Objective}:
            print("Error")
            return None
        
        match def_type:
            case "add":
                return self._adding(type_base,data_type)
            case "rm":
                return self._removing(type_base,data_type)
            case "rm-source":
                return self._removing(type_base,data_type,True)
            case "search":
                return self._searching(type_base,key,args,source)
            case "search-all":
                return self._searching(type_base,key,args,source,True)

    def _run_plan(self, plan: Plan, trigger: Belief | Objective):
        sleep(0.2)
        self.print(f"Running {plan}")  if self.full_log else ...
        try:
            return plan.body(self, trigger.source, *trigger._args)
        except KeyError:
            self.print(f"{plan} doesn't exist")
            raise RunPlanError

    # TODO: implement stoping plan
    def _stop_plan(self, plan):
        self.print(f"Stoping {plan})")  if self.full_log else ...
        pass

    def recieve_msg(self, sender, act, msg: MSG):
        if not act == "env_tell":
            self.print(f"Received from {sender} : {act} -> {msg}")  if self.full_log else ...
        match (act, msg):
            case ("tell", belief) if isinstance(belief, Belief):
                self.add(belief)

            case ("env_tell", belief) if isinstance(belief, Belief):
                self.add(belief)

            case ("untell", belief) if isinstance(belief, Belief):
                self.rm(belief)

            case ("achieve", objective) if isinstance(objective, Objective):
                self.add(objective)

            case ("unachieve", objective) if isinstance(objective, Objective):
                self.rm(objective)

            case ("askOne", ask) if isinstance(ask, Ask):
                found_belief = self.search(ask.belief)
                self.send(ask.source, "tell", found_belief)

            case ("askAll", ask) if isinstance(ask, Ask):
                found_beliefs = self.search(ask.belief, all=True)
                for bel in found_beliefs:
                    self.send(ask.source, "tell", bel)

            case ("tellHow", belief):
                pass

            case ("untellHow", belief):
                pass

            case ("askHow", belief):
                pass

            case _:
                TypeError(f"Unknown type of message {act}:{msg}")

    def as_data_type(self, act, data):
        match act:
            case "tell" | "env_tell" | "untell":
                return Belief(*data)
            case "achieve" | "unachieve":
                return Objective(*data)
    
    def send(self, target: str | tuple, act: str, msg: MSG | Tuple, channel: str = None):            
        if msg not in self._data_types:
            msg = self.as_data_type(act,msg)
  
        if channel is None:
            channel = self.__default_channel
        msg = msg.update(source = self.my_name)
        match (act, msg):
            case ("askOne" | "askAll", belief) if isinstance(belief, Belief):
                msg = Ask(belief, source=self.my_name)

        self.print(f"Sending to {target} : {act} -> {msg}") if self.full_log else ...
        try:
            self._channels[channel]._send(self.my_name,target,act,msg)
        except KeyError:
            self.print(f"Not Connected to Selected Channel: {channel}")
        #self.send_msg(target, act, msg, channel)
    
    def find_in(self, list_type, class_name, agent_name):
        list_type = list_type.lower()
        try:
            if list_type in self._type_env_set:
                return self._environments[class_name][0].agent_list[agent_name]
            if list_type in self._type_ch_set:
                return self._channels[class_name].agent_list[agent_name]
        except KeyError as ke:
            self.print(f"Not connected to {list_type}:{class_name}:{ke}")
            
    def execute(self,env_name):
        try:
            return self._environments[env_name][0]
        except KeyError:
            self.print(f"Not Connected to Environment:{env_name}")

    def send_msg(self, target: str, act: str, msg: MSG, channel: str):
        pass

    def reasoning(self):
        self.print(f"Starting Reasoning")
        self.stop_flag = threading.Event()
        self.thread = threading.Thread(target=self.cycle,args=(self.stop_flag,))
        self.thread.start()
        
    def stop_cycle(self):
        #sleep(3)
        self.print("Shutting Down...")
        self.stop_flag.set()
        self.paused_agent = True
            
    def cycle(self, stop_flag):
        while not stop_flag.is_set():            
            self._perception()
            #self.mail() #TODO better organized way of checking messages
            chosen_plan, trigger = self._deliberation()
            #self.print(f"{chosen_plan}")
            if chosen_plan is not None:
                result = self._execution(chosen_plan, trigger)
            sleep(1)

    def _perception(self):
        for env_name in self._environments:
            self.print(f"Percepting '{env_name}'") if self.full_log else ...
            role_in_env = self._environments[env_name][1]
            perceived = self._environments[env_name][0].perception(role_in_env)
            #self.print(f"Perceiving: {perceived}")
            self.rm(Belief(None,None,env_name),purge_source=True)
            for key, value in perceived.items():
                self.add(Belief(key,value,env_name))
    
    def _deliberation(self):
        for plan in self.__plans:
            trigger = None
            num_args = sum(
                1 for param in inspect.signature(plan.body).parameters.values()
                if param.default is param.empty and param.name != 'self'
            ) - 1
            #self.print(f"Checking {plan} {num_args}")
            trigger = self.search(Objective,plan.trigger,num_args)
            if not trigger:
                trigger = self.search(Belief,plan.trigger,num_args)
                if not trigger or self.has_old_belief(trigger):
                    continue
            
            for context in plan.context:
                if not self.has_close(*context):
                    break
            else:        
                return plan, trigger
        return None, None
    
    def _execution(self, chosen_plan, trigger):
        if not chosen_plan:
            self.print(f"No plan found")
            return None
        self.print(f"Execution of {chosen_plan.trigger}:{trigger}") if self.full_log else ...
        try:
            if type(trigger) is Objective:
                self.rm(trigger)
            if type(trigger) is Belief:
                self._adding(self.__old_beliefs,trigger) #TODO : Also remove beliefs form OLD when removing from normal
            return self._run_plan(chosen_plan, trigger)
        except RunPlanError:
            self.print(f"{chosen_plan} failed")

    # TODO: should invalid arguments be an error or a warning?
    def _clean(
        self, data_type: Iterable[Belief | Objective] | Belief | Objective 
    ) -> Dict:
        match data_type:
            case None:
                return dict()
            case Belief() | Objective():
                return {data_type.source: {data_type.key: {data_type}}}
            case Iterable():
                type_dict = dict()
                for typ in data_type:
                    if not isinstance(typ, Belief) and not isinstance(typ, Objective):
                        raise InvalidBeliefError(
                            f"Expected data type to be Iterable[Belief | Objective] | Belief | Objective, recieved Iterable[{type(typ).__name__}]"
                        )
                    if typ.source in type_dict:
                        if typ.key in type_dict[typ.source]:
                            type_dict[typ.source][typ.key].add(typ)
                        else:
                            type_dict[typ.source].update({typ.key: {typ}})
                    else:
                        type_dict.update({typ.source: {typ.key: {typ}}})

                return type_dict
            case _:
                raise InvalidBeliefError(
                    f"Expected data type to have be Iterable[Belief | Objective] | Belief | Objective, recieved {type(data_type).__name__}"
                )    

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

