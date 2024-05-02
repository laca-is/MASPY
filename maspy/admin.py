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
    def __init__(self) -> None:
        signal.signal(signal.SIGINT, self.stop_all_agents)
        self.end_of_execution = False
        self._name = f"# {type(self).__name__} #"
        print("Starting MASPY Program")
        self.full_log = False
        self.agt_full_log = False
        self.agt_sh_cycle = False
        self.agt_sh_prct = False
        self.agt_sh_slct = False
        self.ch_full_log = False
        self.env_full_log = False
        self._started_agents: List[Agent] = list()
        self._agent_list: Dict[str, str] = dict()
        self._num_agent: Dict[str, int] = dict()
        self._agents: Dict[str, Agent] = dict()
        self._channels: Dict[str, Channel] = dict()
        self._environments: Dict[str, Environment] = dict()
        
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
        if agent.my_name == None :
            name = type(agent).__name__
        else:
            name = agent.my_name
        if name in self._num_agent:
            self._num_agent[name] += 1
            agent.my_name = (name, self._num_agent[name])
        else:
            self._num_agent[name] = 1
            agent.my_name = (name, 1)
        
        #agent.my_name = ("").join(str(x) for x in agent.name_tag)
        
        self._agent_list[agent.my_name] = type(agent).__name__
        self._agents[agent.my_name] = agent
        agent.full_log = self.agt_full_log
        agent.show_cycle = self.agt_sh_cycle
        agent.show_prct = self.agt_sh_prct
        agent.show_slct = self.agt_sh_slct
        self.print(
            f"Registering Agent {type(agent).__name__}:{agent.my_name}"
        ) if self.full_log else ...

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
        ) if self.full_log else ...

    def _add_channel(self, channel: Channel):
        self._channels[channel._my_name] = channel
        channel.full_log = self.ch_full_log
        self.print(
            f"Registering {type(channel).__name__}:{channel._my_name}"
        ) if self.full_log else ...

    def _add_environment(self, environment: Environment):
        self._environments[environment._my_name] = environment
        environment.full_log = self.env_full_log
        self.print(
            f"Registering Environment {type(environment).__name__}:{environment._my_name}"
        ) if self.full_log else ...
    
    def start_system(self):
        no_agents = True
        try:
            self.print(f"Starting Agents")
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
        print("Ending MASPY Program")
        
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
    
    def connect_to(self, agents: Iterable | Agent, targets: Iterable[Environment | Channel] | Environment | Channel):
        if not isinstance(agents, Iterable): agents = [agents]
        if not isinstance(targets, Iterable): targets = [targets]
        for agent in agents:
            for target in targets:
                match target:
                    case Environment():
                        agent._environments[target._my_name] = target
                    case Channel():
                        agent._channels[target._my_name] = target
                
                target._add_agent(agent)

    def set_logging(self, full_log: bool, show_cycle: bool=False,
                    show_prct: bool=False, show_slct: bool=False, 
                     set_admin=True,
                     set_agents=True,
                     set_channels=True,
                     set_environments=True
                    ):
        self.full_log = True if full_log and set_admin else False
        self.agt_full_log = True if full_log and set_agents else False
        self.agt_sh_cycle = True if show_cycle and set_agents else False
        self.agt_sh_prct = True if show_prct and set_agents else False
        self.agt_sh_slct  = True if show_slct and set_agents else False
        self.ch_full_log = True if full_log and set_channels else False
        self.env_full_log = True if full_log and set_environments else False

    def slow_cycle_by(self, time: int | float):
        for agent in self._agents.values():
            agent.sleep = time
