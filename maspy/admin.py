from threading import Lock
from typing import Any, Dict, List, Union, Optional
from collections.abc import Iterable
from maspy.environment import Environment
from maspy.communication import Channel
from maspy.agent import Agent
import pprint
import signal
from time import sleep, time
import os

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
    def __init__(self:'Admin') -> None:
        signal.signal(signal.SIGINT, self.stop_all_agents)
        self.end_of_execution = False
        self._name = f"# {type(self).__name__} #"
        print("Starting MASPY Program")
        self.show_exec = False
        self.agt_sh_exec = False
        self.agt_sh_cycle = False
        self.agt_sh_prct = False
        self.agt_sh_slct = False
        self.ch_sh_exec = False
        self.env_sh_exec = False
        self._started_agents: List[Agent] = list()
        self._agent_list: Dict[tuple, str] = dict()
        self._num_agent: Dict[str, int] = dict()
        self._agents: Dict[tuple, Agent] = dict()
        self._channels: Dict[str, Channel] = dict()
        self._environments: Dict[str, Environment] = dict()
        self.system_report = False
        self.recording = False
        self.record_rate = 5
        self.start_time: float|None = None
        self.system_info: Dict[str, Any] = dict()
        
    def print(self,*args, **kwargs):
        return print(f"{self._name}>",*args,**kwargs)
    
    def get_agents(self) -> Dict[tuple, str]:
        return self._agent_list

    def add_agents(
        self, agents: Union[List[Agent], Agent]
    ) -> None:
        if isinstance(agents, list):
            for agent in agents:
                self._add_agent(agent)
        else:
            self._add_agent(agents)
    
    def _add_agent(self, agent: Agent) -> None:
        name: Optional[str | tuple] = None
        if agent.my_name == ("",0) :
            name = type(agent).__name__
        else:
            name = agent.my_name[0]
            
        assert isinstance(name,str), f"Agent name must be a string, got {type(name)}"
        if name in self._num_agent:
            self._num_agent[name] += 1
            agent.my_name = (name, self._num_agent[name])
        else:
            self._num_agent[name] = 1
            agent.my_name = (name, 1)
        
        #agent.my_name = ("").join(str(x) for x in agent.name_tag)
        
        self._agent_list[agent.my_name] = type(agent).__name__
        self._agents[agent.my_name] = agent
        agent.show_exec = self.agt_sh_exec
        agent.show_cycle = self.agt_sh_cycle
        agent.show_prct = self.agt_sh_prct
        agent.show_slct = self.agt_sh_slct
        self.print(
            f"Registering Agent {type(agent).__name__}:{agent.my_name}"
        ) if self.show_exec else ...

    def rm_agents(
        self, agents: Union[Iterable[Agent], Agent]
    ) -> None:
        if isinstance(agents, list):
            for agent in agents:
                self._rm_agent(agent)
        else:
            assert isinstance(agents, Agent)
            self._rm_agent(agents)

    def _rm_agent(self, agent: Agent):
        if agent.my_name in self._agents:
            assert isinstance(agent.my_name, tuple)
            del self._agents[agent.my_name]
            del self._agent_list[agent.my_name]
        self.print(
            f"Removing agent {type(agent).__name__}:{agent.my_name} from List"
        ) if self.show_exec else ...

    def _add_channel(self, channel: Channel) -> None:
        self._channels[channel._my_name] = channel
        channel.show_exec = self.ch_sh_exec
        self.print(
            f"Registering {type(channel).__name__}:{channel._my_name}"
        ) if self.show_exec else ...

    def _add_environment(self, environment: Environment) -> None:
        self._environments[environment._my_name] = environment
        environment.show_exec = self.env_sh_exec
        self.print(
            f"Registering Environment {type(environment).__name__}:{environment._my_name}"
        ) if self.show_exec else ...
    
    def record_info(self):
        if self.start_time is None:
            self.start_time = time()
            current_time = 0
        else:
            current_time = (time() - self.start_time)*1000
        current_time = round(current_time,2)
        self.print("### RECORDING CURRENT INFO ###")
        self.system_info[current_time] = {"agent":{},"Environment":{},"Communication":{}}
        
        agent_info = dict()
        for agent in self._agents.values():
            agent_info.update({agent.str_name: agent.get_info})
        
        env_info = dict()
        for env_name, env in self._environments.items():
            env_info.update({env_name: env.get_info})
            
        ch_info = dict()    
        for ch_name, ch in self._channels.items():
            ch_info.update({ch_name: ch.get_info})
               
        self.system_info[current_time]["agent"].update(agent_info)
        self.system_info[current_time]["Environment"].update(env_info)
        self.system_info[current_time]["Communication"].update(ch_info)
                    
    
    def start_system(self:'Admin') -> None:
        no_agents = True
        self.start_time = time()
        
        if self.recording:
            self.record_info()
            
        try:
            self.print("Starting Agents")
            for agent_name in self._agents:
                no_agents = False
                self._start_agent(agent_name)
            
            if no_agents:
                self.print("No agents are connected")
            
            sleep(1)
            while self.running_agents():
                if self.recording:
                    sleep(self.record_rate)
                    self.record_info()
                sleep(1)
            
            self.stop_all_agents()
        except Exception as e:
            print(e)
            pass
    
    def running_class_agents(self, cls) -> bool:
        for agent in self._agents.values():
            if agent.my_name[0] == cls and agent.running:
                return True
        return False
    
    def running_agents(self:'Admin') -> bool:
        for agent in self._agents.values():
            if agent.running:
                #print(f"Agent {agent.my_name} is running")
                return True
        return False

    def print_running(self:'Admin', cls=None) -> bool:
        buffer = "Agent(s):\n"
        for agent in self._agents.values():
            if agent.running and (cls is None or agent.my_name[0] == cls):
                buffer += f"{agent.str_name}: ({agent.get_info})\n"
        print(buffer)
        return False 

    def start_agents(
        self, agents: Union[List[Agent], Agent]
    ) -> None:
        if isinstance(agents, list):
            self.print("Starting listed agents")
            for agent in agents:
                assert isinstance(agent.my_name, tuple)
                self._start_agent(agent.my_name)
        else:
            assert isinstance(agents, Agent)
            self.print(f"Starting agent {type(agents).__name__}:{agents.my_name}")
            assert isinstance(agents.my_name, tuple)
            self._start_agent(agents.my_name)

    def _start_agent(self, agent_name: tuple) -> None:
        try:
            if agent_name in self._started_agents:
                self.print(f"'Agent' {agent_name} already started")
                return

            agent = self._agents[agent_name]
            self._started_agents.append(agent)
            agent.reasoning()
        except KeyError:
            self.print(f"'Agent' {agent_name} not connected to environment")
            
    def stop_all_agents(self,sig=None,frame=None):
        self.elapsed_time = time() - self.start_time
        self.print("[Closing System]")
        for agent in self._agents.values():
            agent.stop_cycle(False)
            
        print("Ending MASPY Program")
        if self.recording:
            #json_string = json.dumps(self.system_info, indent=2)
            pprint.pprint(self.system_info, indent=2, sort_dicts=False)
        if self.system_report:
            buffer = "\n# System Report #\n"
            #print(f'Confirmation (spots_sold): {self._environments["Parking"].print_percepts}')
            buffer += f'Elapsed Time: {round(self.elapsed_time,4)} seconds\n'
            buffer += f'Total Agents: {len(self._agents)}\n'
            for name, counter in self._num_agent.items():
                buffer += f'  {name}: {counter}\n'
            buffer += f'Total Msgs: {self._channels["Parking"].send_counter}\n'
            for sender, counter in self._channels["Parking"].send_counter_agent.items():
                buffer += f'  By {sender}\'s: {counter} msgs\n'
            print(buffer)
        os._exit(0)
    
    def connect_to(self, agents: list[Agent] | Agent, targets: list[Environment | Channel] | Environment | Channel) -> None:
        if not isinstance(agents, list): 
            agents = [agents]
        if not isinstance(targets, list): 
            targets = [targets]
        for agent in agents:
            for target in targets:
                match target:
                    case Environment():
                        agent._environments[target._my_name] = target
                    case Channel():
                        agent._channels[target._my_name] = target
                
                target._add_agent(agent)

    def set_logging(self, show_exec: bool, show_cycle: bool=False,
                    show_prct: bool=False, show_slct: bool=False, 
                     set_admin=True,
                     set_agents=True,
                     set_channels=True,
                     set_environments=True
                    ) -> None:
        self.show_exec = True if show_exec and set_admin else False
        self.agt_sh_exec = True if show_exec and set_agents else False
        self.agt_sh_cycle = True if show_cycle and set_agents else False
        self.agt_sh_prct = True if show_prct and set_agents else False
        self.agt_sh_slct  = True if show_slct and set_agents else False
        self.ch_sh_exec = True if show_exec and set_channels else False
        self.env_sh_exec = True if show_exec and set_environments else False
        
        for agent in self._agents.values():
            agent.show_exec = self.agt_sh_exec
            agent.show_cycle = self.agt_sh_cycle
            agent.show_prct = self.agt_sh_prct
            agent.show_slct = self.agt_sh_slct
        for env in self._environments.values():
            env.show_exec = self.ch_sh_exec
        for ch in self._channels.values():
            ch.show_exec = self.env_sh_exec
            

    def slow_cycle_by(self, time: int | float) -> None:
        for agent in self._agents.values():
            agent.delay = time
