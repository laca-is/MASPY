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


@dataclass(eq=True, frozen=True, unsafe_hash=True)
class Belief:
    key: str
    args: tuple = field(default_factory=tuple)
    source: str = "percept"

    def __post_init__(self):
        match self.args:
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

        self.paused_agent = False
        print(f"{self.my_name}> Initialized")

    def add_focus(self, environment_name: str) -> Environment:
        self.__environments[environment_name] = implib.import_module(environment_name)
        return self.__environments[environment_name]

    def rm_focus(self, environment: str):
        del self.__environments[environment]

    def add_belief(self, belief: Iterable[Belief] | Belief):
        beliefs = self._clean_beliefs(belief)
        for belief in beliefs:
            self.__beliefs.add(belief)

    def rm_belief(self, belief: Iterable[Belief] | Belief):
        match belief:
            case Iterable():
                for b in belief:
                    try:
                        self.__beliefs.remove(b)
                    except KeyError:
                        pass
            case _:
                self.__beliefs.remove(belief)

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
        for belief in self.__beliefs:
            print(belief)

    def search_beliefs(
        self,
        name: Optional[str] = None,
        belief: Optional[Belief] = None,
        arg_size=0,
        source="percept",
        all=False,
    ):
        if name is not None:
            belief = Belief(name, [None for _ in range(arg_size)], source)
        elif belief is not None:
            belief = belief
        else:
            raise TypeError("Expected either name or belief, found none")

        found_beliefs = []

        for bel in self.__beliefs:
            if belief == bel:
                if not all:
                    return belief
                else:
                    found_beliefs.append(belief)
            elif bel.weak_eq(belief):
                if not all:
                    return bel
                else:
                    found_beliefs.append(bel)
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

    def prepare_msg(self, target: str, act: str, msg: MSG):
        msg.source = self.my_name
        match (act, msg):
            case ("askOne" | "askAll", belief) if isinstance(belief, Belief):
                msg = Ask(belief, source=self.my_name)

        print(f"{self.my_name}> Sending to {target} : {act} -> {msg}")
        self.send_msg(target, act, msg)

    def send_msg(self, target: str, act: str, msg: MSG):
        pass

    def reasoning(self):
        while self.__objectives:
            self.perception()
            # Adicionar guard para os planos
            #  -funcao com condicoes para o plano rodar
            #  -um plano eh (guard(),plano())
            self.execution()
        self.paused_agent = True

    def perception(self):
        pass

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
                return {}
            case Belief():
                return {beliefs}
            case Iterable():
                for belief in beliefs:
                    if not isinstance(belief, Belief):
                        raise InvalidBeliefError(
                            f"Expected beliefs to have type Iterable[Belief] | Belief, recieved Iterable[{type(belief).__name__}]"
                        )
                return set(beliefs)
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
