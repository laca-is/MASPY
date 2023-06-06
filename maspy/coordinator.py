from threading import Lock
from typing import Any, Dict, List, Union
from collections.abc import Iterable
import maspy.agent
from maspy.environment import Environment
from maspy.communication import Channel
import signal
import random

class CoordinatorMeta(type):
    _instances: Dict[str, Any] = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]


class Coordinator(metaclass=CoordinatorMeta):
    def __init__(self, ctrl_name="Crdnt") -> None:
        signal.signal(signal.SIGINT, self.stop_all_agents)
        self._my_name = ctrl_name
        self._name = f"{type(self).__name__}:{self._my_name}"
        self._started_agents: List["maspy.agent.Agent"] = []
        self._agent_list: Dict[str, str] = {}
        self._agents: Dict[str, "maspy.agent.Agent"] = {}

    def print(self,*args, **kwargs):
        return print(f"{self._name}>",*args,**kwargs)

    def get_agents(self) -> Dict[str, str]:
        return self._agent_list

    def add_agents(
        self, agents: Union[Iterable["maspy.agent.Agent"], "maspy.agent.Agent"]
    ):
        try:
            for agent in agents:
                self._add_agent(agent)
        except TypeError:
            self._add_agent(agents)

    def _add_agent(self, agent: "maspy.agent.Agent"):
        agent.my_name = (agent.my_name,random.randint(1000,9999))
        while agent.my_name in self._agents:
            agent.my_name[1] = random.randint(1000, 9999)

        self._agent_list[agent.my_name] = type(agent).__name__
        self._agents[agent.my_name] = agent
        self.print(
            f"Adding Agent {type(agent).__name__}:{agent.my_name} to List"
        )

    def rm_agents(
        self, agents: Union[Iterable["maspy.agent.Agent"], "maspy.agent.Agent"]
    ):
        try:
            for agent in agents:
                self._rm_agent(agent)
        except TypeError:
            self._rm_agent(agents)

    def _rm_agent(self, agent: "maspy.agent.Agent"):
        if agent.my_name in self._agents:
            del self._agents[agent.my_name]
            del self._agent_list[agent.my_name]
        self.print(
            f"Removing agent {type(agent).__name__}:{agent.my_name} from List"
        )

    def start_all_agents(self):
        no_agents = True

        self.print(f"Starting all connected agents")
        for agent_name in self._agents:
            no_agents = False
            self._start_agent(agent_name)

        if no_agents:
            self.print(f"No agents are connected")

    def start_agents(
        self, agents: Union[Iterable["maspy.agent.Agent"], "maspy.agent.Agent"]
    ):
        try:
            self.print(f"Starting listed agents")
            for agent in agents:
                self._start_agent(agent.my_name)
        except TypeError:
            self.print(f"Starting agent {type(agents).__name__}:{agents.my_name}")
            self._start_agent(agents.my_name)

    def _start_agent(self, agent_name: "maspy.agent.Agent") -> None:
        try:
            if agent_name in self._started_agents:
                self.print(f"'maspy.agent.Agent' {agent_name} already started")
                return
            self._started_agents.append(agent_name)
            agent = self._agents[agent_name]
            agent.reasoning()
        except KeyError:
            self.print(f"'maspy.agent.Agent' {agent_name} not connected to environment")
            
    def stop_all_agents(self,signal,frame):
        for agent in self._started_agents:
            agent.stop_cycle()
    
    def connect_to(self, agents: Iterable, targets: Iterable[Environment | Channel]):
        for agent in agents:
            if type(agent) not in (tuple,list):
                agent =  [agent,"any"]
            for target in targets:
                match target:
                    case Environment():
                        agent[0]._environments[target._my_name] = [target,agent[1]]
                    case Channel():
                        agent[0]._channels[target._my_name] = target
                           
                target._add_agent(agent[0])

