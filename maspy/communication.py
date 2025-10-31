from threading import Lock
from typing import Dict, Set, List, TYPE_CHECKING, Union, Any, Optional
from maspy.utils import bcolors
from logging import getLogger
from enum import Enum

if TYPE_CHECKING:
    from maspy.agent import Agent, Belief, Goal, Ask, Plan

Act = Enum('tell | untell | tellHow | untellHow | achieve | unachieve | askOne | askOneReply | askAll | askAllReply | askHow', ['tell', 'untell', 'tellHow', 'untellHow', 'achieve', 'unachieve', 'askOne', 'askOneReply', 'askAll', 'askAllReply', 'askHow']) # type: ignore[misc]

tell = Act.tell
untell = Act.untell
tellHow = Act.tellHow
untellHow = Act.untellHow
achieve = Act.achieve
unachieve = Act.unachieve
askOne = Act.askOne
askOneReply = Act.askOneReply
askAll = Act.askAll
askAllReply = Act.askAllReply
askHow = Act.askHow

broadcast = Enum('broadcast', ['broadcast'])

def is_broadcast(target: Any) -> bool:
    return target == broadcast

class CommsMultiton(type):
    _instances: Dict[str, "Channel"] = {}
    _lock: Lock = Lock()
    
    @classmethod
    def get_instance(cls, ch_name: str) -> Optional["Channel"]:
        if ch_name in cls._instances:
            return cls._instances[ch_name]
        return None

    def __call__(cls, __my_name="default"):
        with cls._lock:
            if __my_name not in cls._instances:
                instance = super().__call__(__my_name)
                cls._instances[__my_name] = instance
        return cls._instances[__my_name]


class Channel(metaclass=CommsMultiton):
    def __init__(self, comm_name:str="default"):
        self.show_exec = False
        self.printing = True
        self.lock = Lock()
        
        self.tcolor = ""
        from maspy.admin import Admin
        self.print_queue = Admin().print_queue
        self.my_name = comm_name
        self.sys_time = Admin().sys_time
        Admin()._add_channel(self)
        self.logger = getLogger("maspy")
        
        from maspy.agent import Belief, Goal, Ask, Plan
        self.data_types = {Belief,Goal,Ask,Plan}
        self.my_name = comm_name
        self.agent_list: Dict[str, Dict[str, Set[str]]] = dict()
        self._agents: Dict[str, 'Agent'] = dict()
        self._name = f"{type(self).__name__}:{self.my_name}"
        self.send_counter = 0
        self.send_counter_agent: Dict[str,int] = dict()
        self.messages_log: Dict[float, List[Dict[str, Any]]] = dict()
        self.logger.info(f"Channel {self.my_name} created", extra=self.ch_info)
        
    def print(self,*args, **kwargs):
        if not self.printing: 
            return
        f_args = "".join(map(str, args))
        f_kwargs = "".join(f"{key}={value}" for key, value in kwargs.items())
        msg = f"{self.tcolor}{self._name}> {f_args}{f_kwargs}{bcolors.ENDCOLOR}"
        self.print_queue.put(msg)
    
    @property
    def get_info(self):
        return {"connected_agents": list(self._agents.keys()).copy()}
    
    @property
    def ch_info(self):
        return {
            "class_name": "Channel",
            "my_name": self.my_name,
            "connected_agents": list(self._agents.keys())
        }
    
    def add_agents(self, agents: Union[List['Agent'],'Agent']):
        if isinstance(agents, list):
            for agent in agents:
                self._add_agent(agent)
        else:
            self._add_agent(agents)

    def _add_agent(self, agent: 'Agent'):
        assert isinstance(agent.tuple_name, tuple)
        ag_name = f'{agent.tuple_name[0]}_{str(agent.tuple_name[1])}'
        if type(agent).__name__ in self.agent_list:
            if agent.tuple_name[0] in self.agent_list[type(agent).__name__]:
                self.agent_list[type(agent).__name__][agent.tuple_name[0]].update({ag_name})
                self._agents[ag_name] = agent
            else:
                self.agent_list[type(agent).__name__].update({agent.tuple_name[0] : {ag_name}})
                self._agents[ag_name] = agent
        else:
            self.agent_list[type(agent).__name__] = {agent.tuple_name[0] : {ag_name}}
            self._agents[ag_name] = agent
        
        self.print(f"Agent {type(agent).__name__}:{agent.tuple_name} added to channel {self.my_name}") if self.show_exec else None
        if self.my_name != "default":
            self.logger.info(f'Connecting Agent {type(agent).__name__}:{agent.tuple_name}', extra=self.ch_info)

    def _rm_agents(self, agents: Union[List['Agent'],'Agent']):
        if isinstance(agents, list):
            for agent in agents:
                self._rm_agent(agent)
        else:
            self._rm_agent(agents)

    def _rm_agent(self, agent: 'Agent'):
        assert isinstance(agent.tuple_name, tuple)
        ag_name = f'{agent.tuple_name[0]}_{str(agent.tuple_name[1])}'
        if agent.tuple_name in self._agents:
            del self._agents[ag_name]
            self.agent_list[type(agent).__name__][agent.tuple_name[0]].remove(ag_name)
        
        self.print(f"Agent {type(agent).__name__}:{agent.tuple_name} removed from channel {self.my_name}") if self.show_exec else None
        self.logger.info(f'Desconnecting Agent {type(agent).__name__}:{agent.tuple_name}', extra=self.ch_info)

    def _sendf(self, sender: str, target: str | List[str] | broadcast,  message: Union['Belief', 'Goal', 'Plan'] | List[Union['Belief', 'Goal', 'Plan']], typ: str): 
        if not isinstance(message, list):
            messages = [message]
        if isinstance(target,str) and target != "self" and not target.split("_")[-1].isdigit():
            target = f'{target}_1'
            
        try:
            for msg in messages:
                object.__setattr__(msg, 'source', sender)
                if isinstance(target,list):
                    self.print(f'{sender} sending {typ}:{msg} to list {target}') if self.show_exec else None
                    self.logger.info(f'{sender} sending {typ}:{msg} to list {target}', extra=self.ch_info) 
                    for trgt in target:
                        assert isinstance(trgt, str) 
                        self._agents[trgt]._save_msg(typ,msg, True)
                        
                elif is_broadcast(target):
                    self.print(f'{sender} broadcasting {typ}:{msg}') if self.show_exec else None
                    self.logger.info(f'{sender} broadcasting {typ}:{msg}', extra=self.ch_info)  
                    for agent_name in self._agents.keys():
                        if agent_name != sender and agent_name.split("_")[0] != sender:
                            self._agents[agent_name]._save_msg(typ,msg, True)
                            
                elif isinstance(target, str):
                    self.print(f'{sender} sending {typ}:{msg} to {target}') if self.show_exec else None
                    self.logger.info(f'{sender} sending {typ}:{msg} to {target}', extra=self.ch_info)  
                    self._agents[target]._save_msg(typ,msg, True)
        except AssertionError:
            raise
        except KeyError:
            self.logger.warning(f'Agent {target} not connected to {self.my_name} channel', extra=self.ch_info)
        self.logger.info(f'Message Sent', extra=self.ch_info) 

    def _send(self, sender: str, target: str | List[str] | broadcast, act: Act, message: Union['Belief', 'Goal', 'Ask', 'Plan'] | List[Union['Belief', 'Ask', 'Goal', 'Plan']]):  
        messages = []
        if isinstance(message, list):
            for m in message:
                messages.append(self.parse_sent_msg(sender,act,m))
        else:
            messages.append(self.parse_sent_msg(sender,act,message))
        try:
            for msg in messages:
                if isinstance(target,list):
                    for trgt in target:
                        assert isinstance(trgt, str)
                        self._sending(sender,trgt,act,msg)
                elif is_broadcast(target):
                    for agent_name in self._agents.keys():
                        if agent_name != sender and agent_name.split("_")[0] != sender:
                            self._sending(sender,agent_name,act,msg)
                elif isinstance(target, str):
                    self._sending(sender,target,act,msg)
        except AssertionError:
            raise
        self.logger.info(f'Message Sent', extra=self.ch_info) 
    
    def _sending(self, sender: str, target: str, act: Act, msg: Union['Belief', 'Goal', 'Ask', 'Plan']):
        self.print(f'{sender} sending {act.name}:{msg} to {target}') if self.show_exec else None
        self.logger.info(f'{sender} sending {act.name}:{msg} to {target}', extra=self.ch_info)   

        from maspy.agent import Belief, Goal, Ask, Plan
        try:
            if act in [tell,untell]: 
                assert isinstance(msg, Belief),f'Act {act.name} must send Belief, sent {msg}'
            elif act in [achieve, unachieve]: 
                assert isinstance(msg, Goal),f'Act {act.name} must send Goal, sent {msg}'
            elif act in [askOne,askOneReply,askAll,askAllReply,askHow]: 
                assert isinstance(msg, Ask),f'Act {act.name} must send Ask, sent {msg}' 
            elif act in [tellHow,untellHow]: 
                assert isinstance(msg, Plan),f'Act {act.name} must send Plan, sent {msg}'
            self._agents[target]._save_msg(act,msg, False)
        except KeyError:
            self.logger.warning(f'Agent {target} not connected', extra=self.ch_info)
        except AssertionError:
            raise
    
    def parse_sent_msg(self, sender: str, act: Act, msg: Union['Belief', 'Goal', 'Ask', 'Plan']):
        from maspy.agent import Belief, Goal, Ask
        if isinstance(msg, Belief | Goal) and msg is not None:
            object.__setattr__(msg, 'source', sender)
        if act in [askOne,askAll] and isinstance(msg, Belief | Goal):
            msg = Ask(msg, source=sender)
        return msg