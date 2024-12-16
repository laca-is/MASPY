from threading import Lock, Thread
from typing import Any, Dict, List, Union, Optional, TypeVar
from collections.abc import Iterable
from maspy.environment import Environment
from maspy.communication import Channel
from maspy.agent import Agent
from maspy.utils import bcolors
from maspy.learning.modelling import EnvModel
import pprint
import signal
import pandas as pd # type: ignore
from time import sleep, time
import os
import sys

TAgent = TypeVar('TAgent', bound=Agent)
TEnv = TypeVar('TEnv', bound=Environment)
TChannel = TypeVar('TChannel', bound=Channel)

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
        self.print("Starting MASPY Program")
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
        self._agent_class_color: Dict[str, str] = dict()
        self._channels: Dict[str, Channel] = dict()
        self._environments: Dict[str, Environment] = dict()
        self._models: Dict[str, EnvModel] = dict()
        
        self.full_report = False
        self.report = False
        self._report_lock = False
        self.recording = False
        self.record_rate = 5
        self.start_time: float|None = None
        self.system_info: Dict[str, Any] = dict()
        
    def print(self,*args, **kwargs):
        f_args = "".join(map(str, args))
        f_kwargs = "".join(f"{key}={value}" for key, value in kwargs.items())
        return print(f"{bcolors.GOLD}{self._name}> {f_args}{f_kwargs}{bcolors.ENDCOLOR}")
    
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
        name: Optional[str | tuple] = agent.my_name
        # if agent.tuple_name == ("",0) :
        #     name = type(agent).__name__
        # else:
        #     name = agent.tuple_name[0]
            
        assert isinstance(name,str), f"Agent name must be a string, got {type(name)}"
        if name in self._num_agent:
            self._agents[(name,1)].my_name = f'{name}_1'
            self._num_agent[name] += 1
            agent.tuple_name = (name, self._num_agent[name])
            agent.my_name = f'{name}_{str(self._num_agent[name])}'
        else:
            self._num_agent[name] = 1
            agent.tuple_name = (name, 1)

        
        #agent.my_name = ("").join(str(x) for x in agent.name_tag)
        
        self._agent_list[agent.tuple_name] = type(agent).__name__
        self._agents[agent.tuple_name] = agent
        agent.show_exec = self.agt_sh_exec
        agent.show_cycle = self.agt_sh_cycle
        agent.show_prct = self.agt_sh_prct
        agent.show_slct = self.agt_sh_slct
        if type(agent).__name__ in self._agent_class_color:
            agent.tcolor = self._agent_class_color[type(agent).__name__]
        else:
            color = bcolors.get_color("Agent")
            self._agent_class_color[type(agent).__name__] = color
            agent.tcolor = color

        self.print(
            f"Registering Agent {type(agent).__name__}:{agent.tuple_name}"
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
        if agent.tuple_name in self._agents:
            assert isinstance(agent.tuple_name, tuple)
            del self._agents[agent.tuple_name]
            del self._agent_list[agent.tuple_name]
        self.print(
            f"Removing agent {type(agent).__name__}:{agent.tuple_name} from List"
        ) if self.show_exec else ...

    def _add_channel(self, channel: Channel) -> None:
        self._channels[channel.my_name] = channel
        channel.show_exec = self.ch_sh_exec
        channel.tcolor = bcolors.get_color("Channel")
        self.print(
            f"Registering {type(channel).__name__}:{channel.my_name}"
        ) if self.show_exec else ...

    def _add_model(self, model: EnvModel) -> None:
        self._models[model.name] = model
        self.print(
            f"Registering {type(model).__name__}:{model.name}"
        ) if self.show_exec else ...

    def _add_environment(self, environment: Environment) -> None:
        self._environments[environment.my_name] = environment
        environment.show_exec = self.env_sh_exec
        environment.tcolor = bcolors.get_color("Env")
        self.print(
            f"Registering Environment {type(environment).__name__}:{environment.my_name}"
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
            agent_info.update({agent.my_name: agent.get_info})
        
        env_info = dict()
        for env_name, env in self._environments.items():
            env_info.update({env_name: env.get_info})
            
        ch_info = dict()    
        for ch_name, ch in self._channels.items():
            ch_info.update({ch_name: ch.get_info})
               
        self.system_info[current_time]["agent"].update(agent_info)
        self.system_info[current_time]["Environment"].update(env_info)
        self.system_info[current_time]["Communication"].update(ch_info)
    
    def sys_time(self):
        if self.start_time is None:
            return 0.000000
        return round(time() - self.start_time,6)

    def start_system(self:'Admin') -> None:
        no_agents = True
        for model in self._models.values():
            model.reset_percepts()
                
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
            self.print(e)
            pass
    
    def running_class_agents(self, cls) -> bool:
        for agent in self._agents.values():
            if agent.tuple_name[0] == cls and agent.running:
                return True
        return False
    
    def running_agents(self:'Admin') -> bool:
        for agent in self._agents.values():
            if agent.running:
                return True
        return False

    def print_running(self:'Admin', cls=None) -> bool:
        buffer = "Still running agent(s):\n"
        flag = False
        for agent in self._agents.values():
            if agent.running and (cls is None or agent.tuple_name[0] == cls):
                flag = True
                buffer += f"{agent.my_name} | "
        if flag:
            self.print(buffer)
            return True
        return False 

    def start_agents(
        self, agents: Union[List[TAgent], TAgent]
    ) -> None:
        if isinstance(agents, list):
            self.print("Starting listed agents")
            for agent in agents:
                assert isinstance(agent.tuple_name, tuple)
                self._start_agent(agent.tuple_name)
        else:
            assert isinstance(agents, Agent)
            self.print(f"Starting agent {type(agents).__name__}:{agents.tuple_name}")
            assert isinstance(agents.tuple_name, tuple)
            self._start_agent(agents.tuple_name)

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
        if self._report_lock:
            return
        self.elapsed_time = time() - self.start_time
        self.print("[Closing System]")
        self.print_running()
        for agent in self._agents.values():
            if agent.running:
                agent.stop_cycle(False)
            
        self.print("Ending MASPY Program")
        if self.recording:
            #json_string = json.dumps(self.system_info, indent=2)
            pprint.pprint(self.system_info, indent=2, sort_dicts=False)
        if (self.full_report or self.report) and not self._report_lock:
            self._report_lock = True
            self.print("Making System Report...")
            self._print_report()
            self.print("System Report Completed")
        os._exit(0)
    
    def _print_report(self) -> None:
        # buffer = "\n# System Report #\n"
        # #print(f'Confirmation (spots_sold): {self._environments["Parking"].print_percepts}')
        # buffer += f'Elapsed Time: {round(self.elapsed_time,4)} seconds\n'
        # buffer += f'Total Agents: {len(self._agents)}\n'
        # for name, counter in self._num_agent.items():
        #     buffer += f'  {name}: {counter}\n'
        # buffer += f'Total Msgs: {self._channels["Parking"].send_counter}\n'
        # for sender, counter in self._channels["Parking"].send_counter_agent.items():
        #     buffer += f'  By {sender}\'s: {counter} msgs\n'
        # print(buffer)
        log_dict: Dict[float, Dict[str, Dict[str, Any]]] = dict() 
        for instance in self._agents.values():
            for key, value in instance.cycle_log.items():
                for idx, log in enumerate(value):
                    if len(value) > 1:
                        instance_name = f"{instance.my_name} ({idx})"
                    else:
                        instance_name = instance.my_name
                    if key in log_dict:
                        log_dict[key][instance_name] = log
                    else:
                        log_dict[key] = {instance_name: log}

        main_name = os.path.basename(sys.argv[0]).split(".py")[0]
        self.dict_to_excel(log_dict, f"{main_name}_report")
    
    def dict_to_excel(self, data_dict: Dict, output_file):
        rows = []
        total_iterations = sum(len(instances) for instances in data_dict.values())
        processed_iterations = 0
        self.print("Managing Data...")
        for sys_time, instances in data_dict.items():
            assert isinstance(instances, dict)
            for instance, instance_data in instances.items():
                assert isinstance(instance_data, dict)
                processed_iterations += 1
                percentage = (processed_iterations / total_iterations) * 100
                #self.print_progress_bar(percentage)
                row = {
                    "Time": sys_time,
                    "Instance": instance,
                    "Cycle": instance_data.get("cycle", None),
                    "Operation": instance_data.get("decision", None),
                    "Description": instance_data.get("description", None),
                    "Completed Goal": instance_data.get("running_goal", None),
                    "Received Msgs": instance_data.get("last_recv", None),
                    "Event": instance_data.get("event", None),
                    "Completed Event": instance_data.get("last_event", None),
                    "Retrieved Plans": instance_data.get("retrieved_plans", None),
                    "Events": instance_data.get("events", None),
                    "Connected Envs": instance_data.get("connected_envs", None),
                    "Connected Chs": instance_data.get("connected_chs", None),
                    "Intentions": instance_data.get("intentions", None),
                    "Beliefs": instance_data.get("beliefs", None),
                    "Goals": instance_data.get("goals", None),
                }
                rows.append(row)
        if self.full_report:
            df = pd.DataFrame(rows, columns=["Time", "Instance", "Cycle", "Operation", "Description", "Received Msgs", "Event", "Retrieved Plans", "Events","Intentions", "Completed Event", "Connected Envs", "Connected Chs", "Beliefs", "Goals"])
        elif self.report:
            df = pd.DataFrame(rows, columns=["Time", "Instance", "Cycle", "Operation", "Description"])
            
        df['Instance_numeric'] = df['Instance'].str.extract(r'_(\d+)$').fillna(0).astype(int)
        df = df.sort_values(by=["Time","Instance_numeric"]).drop(columns='Instance_numeric')

        
        if not os.path.exists("reports"):
            os.makedirs("reports")
        counter = 1
        filename = f"{output_file}_{counter}"
        while os.path.exists(f"reports/{filename}.xlsx"):
            counter += 1
            filename = f"{output_file}_{counter}"
            
        self.print("Writing to Excel...")
        #self.to_excel_with_progress(df, f"reports/{filename}.xlsx")    
        df.to_excel(f"reports/{filename}.xlsx", index=False)
    
    def print_progress_bar(self, percentage, bar_length=40):
        percentage = min(max(percentage, 0), 100)
        filled_length = int(bar_length * percentage // 100)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        sys.stdout.write(f'\r|{bar}| {percentage:.2f}% Complete')
        sys.stdout.flush()
        if percentage >= 100:
            print()

    def write_to_excel(self, df, file_path):
        df.to_excel(file_path, index=False)
    
    def estimate_duration(self, df):
        sample_size = min(10, len(df)) 
        sample_df = df.iloc[:sample_size]
        
        start_time = time()
        sample_df.to_excel("sample_output.xlsx", index=False)
        duration = time() - start_time
    
        return (duration / sample_size) * len(df)
    
    def to_excel_with_progress(self, df, file_path): 
        estimated_duration = self.estimate_duration(df)  
        
        thread = Thread(target=self.write_to_excel, args=(df, file_path))
        thread.start()
        start_time = time()
        
        while thread.is_alive():
            elapsed = time() - start_time
            if elapsed < estimated_duration:
                estimated_duration = (1 - 0.05) * estimated_duration + 0.05 * elapsed
            percentage = min((elapsed / estimated_duration) * 100, 100)
            self.print_progress_bar(percentage)
        
            sleep(0.1)  
            
        self.print_progress_bar(100)
            
    def connect_to(self, agents: list[TAgent] | TAgent, targets: list[TEnv | Environment | TChannel | Channel | str] | Environment | Channel | str) -> None:
        if not isinstance(agents, list): 
            agents = [agents]
        if not isinstance(targets, list): 
            targets = [targets]
        for agent in agents:
            for target in targets:
                agent.connect_to(target)

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
    
    def block_prints(self):
        self.printing = False
        for agent in self._agents.values():
            agent.printing = False
        for env in self._environments.values():
            env.printing = False
        for ch in self._channels.values():
            ch.printing = False

    def slow_cycle_by(self, time: int | float) -> None:
        for agent in self._agents.values():
            agent.delay = time
