from threading import Lock
from typing import Any, Dict, List, Union
from collections.abc import Iterable
from maspy.environment import Environment
from maspy.communication import Channel
from maspy.agent import Agent
import signal
from time import sleep

class AdminMeta(type):
    _instances: Dict[str, Any] = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]


class Admin(metaclass=AdminMeta):
    def __init__(self, ctrl_name="Crdnt") -> None:
        signal.signal(signal.SIGINT, self.stop_all_agents)
        self.end_of_execution = False
        self._my_name = ctrl_name
        self._name = f"{type(self).__name__}"
        self._started_agents: List[Agent] = []
        self._agent_list: Dict[str, str] = {}
        self._num_agent = {}
        self._agents: Dict[str, Agent] = {}
        
    def print(self,*args, **kwargs):
        return print(f"{self._name}>",*args,**kwargs)

    def get_agents(self) -> Dict[str, str]:
        return self._agent_list

    def add_agents(
        self, agents: Union[Iterable[Agent], Agent]
    ):
        try:
            for agent in agents:
                self._add_agent(agent)
        except TypeError:
            self._add_agent(agents)

    def _add_agent(self, agent: Agent):
        
        if agent.my_name in self._num_agent:
            self._num_agent[agent.my_name] += 1
            agent.my_name = (agent.my_name, self._num_agent[agent.my_name])
        else:
            self._num_agent[agent.my_name] = 1
            agent.my_name = (agent.my_name, 1)
        
        #agent.my_name = ("").join(str(x) for x in agent.name_tag)
        
        self._agent_list[agent.my_name] = type(agent).__name__
        self._agents[agent.my_name] = agent
        self.print(
            f"Registering Agent {type(agent).__name__}:{agent.my_name}"
        )

    def rm_agents(
        self, agents: Union[Iterable[Agent], Agent]
    ):
        try:
            for agent in agents:
                self._rm_agent(agent)
        except TypeError:
            self._rm_agent(agents)

    def _rm_agent(self, agent: Agent):
        if agent.my_name in self._agents:
            del self._agents[agent.my_name]
            del self._agent_list[agent.my_name]
        self.print(
            f"Removing agent {type(agent).__name__}:{agent.my_name} from List"
        )

    def start_all_agents(self):
        no_agents = True
        try:
            self.print(f"Starting all connected agents")
            for agent_name in self._agents:
                no_agents = False
                self._start_agent(agent_name)
            
            if no_agents:
                self.print(f"No agents are connected")
            
            sleep(1)
            while not self.end_of_execution and self.running_agents():
                sleep(1)
        except Exception:
            pass
        print("End of Execution")
        
    def running_agents(self):
        for agent in self._agents.values():
            if agent.running:
                return True
        return False

    def start_agents(
        self, agents: Union[Iterable[Agent], Agent]
    ):
        try:
            self.print(f"Starting listed agents")
            for agent in agents:
                self._start_agent(agent.my_name)
        except TypeError:
            self.print(f"Starting agent {type(agents).__name__}:{agents.my_name}")
            self._start_agent(agents.my_name)

    def _start_agent(self, agent_name: Agent) -> None:
        try:
            if agent_name in self._started_agents:
                self.print(f"'Agent' {agent_name} already started")
                return

            agent = self._agents[agent_name]
            self._started_agents.append(agent)
            agent.reasoning()
        except KeyError:
            self.print(f"'Agent' {agent_name} not connected to environment")
            
    def stop_all_agents(self,sig,frame):
        self.print(f"[Closing System]")
        for agent in self._started_agents:
            if agent.running:
                agent.stop_cycle()
        self.end_of_execution = True
    
    def connect_to(self, agents: Iterable, targets: Iterable[Environment | Channel]):
        for agent in agents:
            if type(agent) not in (tuple,list):
                agent =  [agent,"any"]
            for target in targets:
                match target:
                    case Environment():
                        agent[0]._environments[target._my_name] = target
                    case Channel():
                        agent[0]._channels[target._my_name] = target
                           
                target._add_agent(agent[0])

