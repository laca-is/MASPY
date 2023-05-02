from dataclasses import dataclass, field
from maspy.environment import Environment
from maspy.error import (
    InvalidBeliefError,
    InvalidObjectiveError,
    InvalidPlanError,
    RunPlanError,
)
from maspy.system_control import Control
from typing import List, Optional, Dict, Set, Tuple, Any
from collections.abc import Iterable, Callable
from time import sleep
import importlib as implib
import inspect


@dataclass(eq=True, frozen=True)
class Belief:
    key: str
    args: tuple = field(default_factory=tuple)
    source: str = "percept"

    def __post_init__(self):
        match self.args:
            case list() | dict() | str():
                object.__setattr__(self, "args", tuple([self.args]))
            case tuple():
                pass
            case Iterable():
                object.__setattr__(self, "args", tuple(self.args))
            case _:
                object.__setattr__(self, "args", tuple([self.args]))

    def weak_eq(self, other: "Belief"):
        return (
            self.key == other.key
            and len(self.args) == len(other.args)
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
            new_args = self.args

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
        for arg in self.args:
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
class Ask:
    belief: Belief
    reply: list = field(default_factory=list)
    source: str = "unknown"


@dataclass
class Objective:
    key: str
    args: list = field(default_factory=list)
    source: str = "percept"


MSG = Belief | Ask | Objective


class Agent:
    def __init__(
        self,
        name: str,
        beliefs: Optional[Iterable[Belief] | Belief],
        objectives: Optional[Iterable[Objective] | Objective],
        plans: Optional[
            Dict[str, Callable[..., Any]]
            | Iterable[Tuple[str, Callable[..., Any]]]
            | Tuple[str, Callable[..., Any]]
        ],
    ):
        self.my_name = name
        Control().add_agents(self)

        self.__environments: Dict[str, Any] = {}

        self.__beliefs = self._clean_beliefs(beliefs)
        self.__objectives = self._clean_objectives(objectives)
        self.__plans = self._clean_plans(plans)
        self.__plans.update({"reasoning": self.reasoning})

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

    def add_belief(self, belief: Iterable[Belief] | Belief):
        beliefs = self._clean_beliefs(belief)
        print(f"{self.my_name}> Adding {belief}")
        for key, value in beliefs.items():
            if key in self.__beliefs and isinstance(value, dict):
                for inner_key, inner_value in value.items():
                    if inner_key in self.__beliefs[key] and isinstance(inner_value, set):
                        self.__beliefs[key][inner_key].update(inner_value)
            else:
                self.__beliefs[key] = value

    def rm_belief(self, belief: Iterable[Belief] | Belief, purge_source=False):
        try:
            match belief:
                case Iterable():
                    for bel in belief:
                        try:
                            self.__beliefs[bel.source][bel.key].remove(bel)
                        except KeyError:
                            pass
                case _:
                    if purge_source:
                        del self.__beliefs[belief.source]
                    else:
                        self.__beliefs[belief.source][belief.key].remove(belief)
        except KeyError:
            print(f"{self.my_name}> {belief} doesn't exist | purge({purge_source})")

    def add_objective(self, objective: Iterable[Objective] | Objective):
        objectives = self._clean_objectives(objective)

        if objectives not in self.__objectives:
            self.__objectives.append(objective)

            if self.paused_agent:
                self.paused_agent = False
                self.__plans["reasoning"]()

    def rm_objective(self, objective: Objective):
        self.__objectives.remove(objective)

    def add_plan(self, plan: Tuple[str, Callable] | Dict[str, Callable]):
        new_plans = self._clean_plans(plan)
        self.__plans.update(new_plans)

    def rm_plan(self, plan):
        del self.__plans[plan.key]

    def print_beliefs(self):
        print(self.__beliefs)

    def get_like_belief(self, belf, n_args=0):
        if type(belf) == Belief:
            belf_key = belf.key
            n_args = len(belf.args)
        elif type(belf) == str:
            belf_key = belf
        else:
            print(f"{self.my_name}> data type {type(belf)} not accepted")
            return
        try:
            for belief in self.__beliefs[belf_key]:
                if len(belief.args) == n_args:
                    return belief
        except KeyError:
            return None

    # TODO: Return How close it is to an existing belief
    def has_belief(self, belief: Belief):
        return belief in self.__beliefs.get(Belief.source, {}).get(belief.key, {})
        
    def search_beliefs(
        self,
        name: str,
        arg_size=0,
        source="percept",
        all=False,
    ):
        belief = Belief(name, tuple([None for _ in range(arg_size)]), source)
        
        found_beliefs = []

        if belief.source in self.__beliefs and belief.key in self.__beliefs[belief.source]:
            for bel in self.__beliefs[belief.source][belief.key]:
                if bel.weak_eq(belief):
                    if all:
                        found_beliefs.append(bel)
                    else:
                        return bel
                
        return found_beliefs

    def _run_plan(self, plan):
        sleep(0.2)
        print(
            f"{self.my_name}> Running plan(key='{plan.key}', args={plan.args}, source={plan.source})"
        )
        try:
            return self.__plans[plan.key](self, plan.source, *plan.args)
        except (TypeError, KeyError):
            print(f"{self.my_name}> Plan {plan} doesn't exist")
            raise RunPlanError

    # TODO: implement stoping plan
    def _stop_plan(self, plan):
        print(
            f"{self.my_name}> Stoping plan(key='{plan.key}', args={plan.args}, source={plan.source})"
        )
        pass

    def recieve_msg(self, sender, act, msg: MSG):
        if not act == "env_tell":
            print(f"{self.my_name}> Received from {sender} : {act} -> {msg}")
        match (act, msg):
            case ("tell", belief) if isinstance(belief, Belief):
                self.add_belief(belief)
                print(f"{self.my_name}> Adding {belief}")

            case ("env_tell", belief) if isinstance(belief, Belief):
                self.add_belief(belief)
                print(f"{self.my_name}> Adding Env Belief")

            case ("untell", belief) if isinstance(belief, Belief):
                self.rm_belief(belief)
                print(f"{self.my_name}> Removing {belief}")

            case ("achieve", objective) if isinstance(objective, Objective):
                print(f"{self.my_name}> Adding {objective}")
                self.add_objective(objective)

            case ("unachieve", objective) if isinstance(objective, Objective):
                self.rm_objective(objective)
                print(f"{self.my_name}> Removing {objective}")

            case ("askOne", ask) if isinstance(ask, Ask):
                found_belief = self.search_beliefs(ask.belief)
                self.prepare_msg(ask.source, "tell", found_belief)

            case ("askAll", ask) if isinstance(ask, Ask):
                found_beliefs = self.search_beliefs(ask.belief, True)
                for bel in found_beliefs:
                    self.prepare_msg(ask.source, "tell", bel)

            case ("tellHow", belief):
                pass

            case ("untellHow", belief):
                pass

            case ("askHow", belief):
                pass

            case _:
                TypeError(f"Unknown type of message {act} | {msg}")

    def prepare_msg(self, target: str, act: str, msg: MSG, channel: str = None):
        channel = self.__default_channel
        msg = msg.update(source = self.my_name)
        match (act, msg):
            case ("askOne" | "askAll", belief) if isinstance(belief, Belief):
                msg = Ask(belief, source=self.my_name)

        print(f"{self.my_name}> Sending to {target} : {act} -> {msg}")
        self.send_msg(target, act, msg, channel)

    def send_msg(self, target: str, act: str, msg: MSG, channel: str):
        pass

    def reasoning(self):
        while self.__objectives:
            self.perception()
            # Adicionar guard para os planos
            #  -funcao com condicoes para o plano rodar
            #  -um plano eh (guard(),plano())
            self.execution()
            sleep(1)
        self.paused_agent = True

    def perception(self):
        for env_name in self.__environments:
            print(f"{self.my_name}> Percepting env {env_name}")
            perceived = self.__environments[env_name].perception()

            self.rm_belief(Belief(None,None,env_name),True)
            for key, value in perceived.items():
                self.add_belief(Belief(key,value,env_name))
               
    def execution(self):
        if not self.__objectives:
            return None
        objective = self.__objectives[-1]
        print(f"{self.my_name}> Execution of {objective}")
        try:
            result = self._run_plan(objective)
            if objective in self.__objectives:
                self.rm_objective(objective)

        except RunPlanError:
            print(f"{self.my_name}> {objective} failed")

    # TODO: should invalid arguments be an error or a warning?
    def _clean_beliefs(
        self, beliefs: Optional[Iterable[Belief] | Belief]
    ) -> Set[Belief]:
        match beliefs:
            case None:
                return dict()
            case Belief():
                return {beliefs.source: {beliefs.key: beliefs}}
            case Iterable():
                belief_dict = dict()
                for belief in beliefs:
                    if not isinstance(belief, Belief):
                        raise InvalidBeliefError(
                            f"Expected beliefs to have type Iterable[Belief] | Belief, recieved Iterable[{type(belief).__name__}]"
                        )
                    if belief.source in belief_dict:
                        if belief.key in belief_dict[belief.source]:
                            belief_dict[belief.source][belief.key].add(belief)
                        else:
                            belief_dict[belief.source].update({belief.key: {belief}})
                    else:
                        belief_dict.update({belief.source: {belief.key: {belief}}})

                return belief_dict
            case _:
                raise InvalidBeliefError(
                    f"Expected beliefs to have type Iterable[Belief] | Belief, recieved {type(beliefs).__name__}"
                )    

    def _clean_objectives(
        self, objectives: Optional[Iterable[Objective] | Objective]
    ) -> List[Objective]:
        match objectives:
            case None:
                return []
            case Objective():
                return [objectives]
            case Iterable():
                for objective in objectives:
                    if not isinstance(objective, Objective):
                        raise InvalidObjectiveError(
                            f"Expected objectives to have type Iterable[Objectives] | Objectives, recieved {type(objective).__name__}"
                        )
                return list(objectives)
            case _:
                raise InvalidObjectiveError(
                    f"Expected beliefs to have type Iterable[Objectives] | Objectives, recieved {type(objectives).__name__}"
                )

    def _clean_plans(
        self,
        plans: Optional[
            Dict[str, Callable[..., Any]]
            | Tuple[str, Callable[..., Any]]
            | Iterable[Tuple[str, Callable[..., Any]]]
        ],
    ) -> Dict[str, Callable[..., Any]]:
        match plans:
            case None:
                return {}
            case tuple() if len(plans) == 2 and isinstance(plans[0], str) and callable(
                plans[1]
            ):
                return {plans[0]: plans[1]}
            case tuple():
                type_list = tuple(map(lambda x: type(x).__name__, plans))
                types = ", ".join(type_list)
                raise InvalidPlanError(
                    f"Expected plans to have type Tuple[str, Callable], recieved Tuple[{types}]"
                )

            case dict():
                for key, plan in plans.items():
                    if not (isinstance(key, str) or callable(plan)):
                        raise InvalidPlanError(
                            f"Expected plans to have type Dict[str, Callable], recieved Dict[{type(key).__name__}, {type(plan).__name__}]"
                        )
                return plans

            case Iterable():
                try:
                    for key, plan in plans:  # type: ignore
                        if not (isinstance(key, str) or callable(plan)):
                            raise InvalidPlanError(
                                f"Expected plans to have type Iterable[Tuple[str, Callable]], recieved Iterable[Tuple[{type(key).__name__}, {type(plan).__name__}"
                            )
                    return dict(plans)
                except TypeError:
                    type_set = set(map(lambda x: type(x).__name__, plans))
                    types = " | ".join(type_set)
                    raise InvalidPlanError(
                        f"Expected plans to have type Iterable[Tuple[str, Callable]], recieved Iterable[{types}]"
                    )
            case _:
                raise InvalidPlanError(
                    f"Expected plans to have type Dict[str, Callable] | Iterable[Tuple[str, Callable]] | Tuple(str, Callable), recieved {type(plans).__name__}"
                )
        return {}

