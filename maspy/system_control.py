import random
from threading import Lock
from typing import Any, Dict, List, Union
from collections.abc import Iterable

import maspy.agent

"""
    Class for abstract control of all agents
        -Unique Identification
        -Management
        -Initialization
"""


class ControlMeta(type):
    _instances: Dict[str, Any] = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]


class Control(metaclass=ControlMeta):
    def __init__(self, ctrl_name="ctrl") -> None:
        self.__my_name = ctrl_name
        self.__started_agents: List["maspy.agent.Agent"] = []
        self.__agent_list: Dict[str, str] = {}
        self.__agents: Dict[str, "maspy.agent.Agent"] = {}

    def get_agents(self) -> Dict[str, str]:
        return self.__agent_list

    def add_agents(
        self, agents: Union[Iterable["maspy.agent.Agent"], "maspy.agent.Agent"]
    ):
        try:
            for agent in agents:
                self._add_agent(agent)
        except TypeError:
            self._add_agent(agents)

    def _add_agent(self, agent: "maspy.agent.Agent"):
        agent.my_name = f"{agent.my_name}#{random.randint(1000,9999)}"
        if agent.my_name in self.__agents:
            aux = agent.my_name.split("#")
            while "#".join(aux) in self.__agents:
                aux[-1] = str(random.randint(1000, 9999))

            agent.my_name = "#".join(aux)
        self.__agent_list[agent.my_name] = type(agent).__name__
        self.__agents[agent.my_name] = agent
        print(
            f"{self.__my_name}> Adding agent {type(agent).__name__}:{agent.my_name} to System"
        )

    def rm_agents(
        self, agents: Union[Iterable["maspy.agent.Agent"], "maspy.agent.Agent"]
    ):
        try:
            for agent in agents:
                self._rm_agent(agent)
        except TypeError:
            self._rm_agent(agents)
        # self.send_agents_list()

    def _rm_agent(self, agent: "maspy.agent.Agent"):
        if agent.my_name in self.__agents:
            del self.__agents[agent.my_name]
            del self.__agent_list[agent.my_name]
        print(
            f"{self.__my_name}> Removing agent {type(agent).__name__}:{agent.my_name} from System"
        )

    def start_all_agents(self):
        no_agents = True

        # self.send_agents_list()
        print(f"{self.__my_name}> Starting all connected agents")
        for agent_name in self.__agents:
            no_agents = False
            self._start_agent(agent_name)

        if no_agents:
            print(f"{self.__my_name}> No agents are connected")

    def start_agents(
        self, agents: Union[Iterable["maspy.agent.Agent"], "maspy.agent.Agent"]
    ):
        # self.send_agents_list()
        try:
            print(f"{self.__my_name}> Starting listed agents")
            for agent in agents:
                self._start_agent(agent.my_name)
        except TypeError:
            print(
                f"{self.__my_name}> Starting agent {type(agents).__name__}:{agents.my_name}"
            )
            self._start_agent(agents.my_name)

    def _start_agent(self, agent_name: "maspy.agent.Agent") -> None:
        try:
            if agent_name in self.__started_agents:
                print(
                    f"{self.__my_name}> 'maspy.agent.Agent' {agent_name} already started"
                )
                return
            self.__started_agents.append(agent_name)
            agent = self.__agents[agent_name]
            agent.reasoning()
        except KeyError:
            print(
                f"{self.__my_name}> 'maspy.agent.Agent' {agent_name} not connected to environment"
            )
