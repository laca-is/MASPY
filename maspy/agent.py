from dataclasses import dataclass, field, astuple
from maspy.environment import Environment
from maspy.error import (
    InvalidBeliefError,
    InvalidObjectiveError,
    InvalidPlanError,
    RunPlanError,
)
from maspy.coordinator import Control
from typing import List, Optional, Union, Dict, Set, Tuple, Any
from collections.abc import Iterable, Callable
from time import sleep
import importlib as implib
import inspect


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
        self._type_belief_set = {Belief, "belief" , "belf" , "bel" , "b"}
        self._type_objective_set = {Objective, "objective", "objtv", "obj", "o"}
        self.full_log = full_log
        self.my_name = name
        Control().add_agents(self)

        self.__environments: Dict[str, Any] = {}

        self.__beliefs = self._clean(beliefs)
        self.__new_beliefs = self._clean(None)
        self.__objectives = self._clean(objectives)
        self.__plans = self._clean_plans(plans)

        self.__default_channel = None
        self.paused_agent = False
        print(f"{self.my_name}> Initialized")

    def set_default_channel(self, channel):
        self.__default_channel = channel

    def add_focus_env(self, env_instance, env_name: str = 'env'):
        self.__environments[env_name] = env_instance

    def add_focus(self, environment: str, env_name: str = 'env') -> Environment:
        classes = []
        try:
            env = implib.import_module(environment)
        except ModuleNotFoundError:
            print(f"{self.my_name}> No environment named '{env_name}'")
            return
        self.__environments = {env_name: {}}
        for name, obj in inspect.getmembers(env):
            if inspect.isclass(obj) and name != "Environment":
                lineno = inspect.getsourcelines(obj)[1]
                classes.append((lineno, obj))
        classes.sort()
        self.__environments[env_name] = classes[0][1](env_name)
        del env
        print(f"{self.my_name}> Connected to environment {env_name}")
        return self.__environments[env_name]

    def rm_focus(self, environment: str):
        del self.__environments[environment]

    def get_env(self, env_name: str):
        return self.__environments[env_name]
    
    def add_plan(self, plan: List[Plan] | Plan):
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
        print(f"{self.my_name}> Adding {data_type}") if self.full_log else ...
        for key, value in data_type.items():
            if key in type_base and isinstance(value, dict):
                for inner_key, inner_value in value.items():
                    if inner_key in type_base[key] and isinstance(inner_value, set):
                        #print(f"{inner_value} {type(inner_value)}")
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
            print(f"{self.my_name}> {data_type} doesn't exist | purge({purge_source})")
      
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
            print(f"{self.my_name}> Error in Central Typing for {type(data_type)}:{data_type}")
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
        print(f"{self.my_name}> Running {plan}")  if self.full_log else ...
        try:
            return plan.body(self, trigger.source, *trigger.args)
        except KeyError:
            print(f"{self.my_name}> {plan} doesn't exist")
            raise RunPlanError

    # TODO: implement stoping plan
    def _stop_plan(self, plan):
        print(f"{self.my_name}> Stoping {plan})")  if self.full_log else ...
        pass

    def recieve_msg(self, sender, act, msg: MSG):
        if not act == "env_tell":
            print(f"{self.my_name}> Received from {sender} : {act} -> {msg}")  if self.full_log else ...
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

    def send(self, target: str, act: str, msg: MSG, channel: str = None):
        channel = self.__default_channel
        msg = msg.update(source = self.my_name)
        match (act, msg):
            case ("askOne" | "askAll", belief) if isinstance(belief, Belief):
                msg = Ask(belief, source=self.my_name)

        print(f"{self.my_name}> Sending to {target} : {act} -> {msg}") if self.full_log else ...
        self.send_msg(target, act, msg, channel)

    def send_msg(self, target: str, act: str, msg: MSG, channel: str):
        pass

    def reasoning_cycle(self):
        while self.__objectives:
            self._perception()
            #self.mail() #TODO better organized way of checking messages
            chosen_plan, trigger = self._deliberation()
            result = self._execution(chosen_plan, trigger)
            sleep(1)
        self.paused_agent = True

    def _perception(self):
        for env_name in self.__environments:
            print(f"{self.my_name}> Percepting '{env_name}'") if self.full_log else ...
            perceived = self.__environments[env_name].perception()

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
            
            trigger = self.search(Objective,plan.trigger,num_args)
            if not trigger:
                trigger = self.search(Belief,plan.trigger,num_args)
                if not trigger:
                    continue
            
            for context in plan.context:
                if not self.has_close(*context):
                    break
            else:        
                return plan, trigger
        return None, None
    
    def _execution(self, chosen_plan, trigger):
        if not chosen_plan:
            print("No plan found")
            return None
        print(f"{self.my_name}> Execution of {chosen_plan.trigger}:{trigger}") if self.full_log else ...
        try:
            if type(trigger) is Objective:
                self.rm(trigger)
            return self._run_plan(chosen_plan, trigger)
        except RunPlanError:
            print(f"{self.my_name}> {chosen_plan} failed")

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
                        
                return plan_list
            case _:
                raise InvalidPlanError(
                    f"Expected plans to have type Dict[str, Callable] | Iterable[Tuple[str, Callable]] | Tuple(str, Callable), recieved {type(plans).__name__}"
                )

