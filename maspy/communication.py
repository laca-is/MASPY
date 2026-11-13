from threading import Lock
from typing import Dict, Set, List, TYPE_CHECKING, Union, Any, Optional
from maspy.utils import bcolors
from logging import getLogger, INFO
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

    def __call__(cls, *args: Any, **kwargs: Any):
        ch_name = args[0] if args else "default"
        if not isinstance(ch_name, str): ch_name = cls.__name__
        with cls._lock:
            if ch_name not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[ch_name] = instance
        
        return cls._instances[ch_name]


class Channel(metaclass=CommsMultiton):
    """
    The channels and protocols for communication between Agents
    
    Each Instance with a unique name is a distinct channel
    """
    def __init__(self, 
                 comm_name: str = "default",
                 *,
                 show_exec: bool = False,
                 printing: bool = True
                ):
        self.lock = Lock()
        
        self.tcolor = ""
        from maspy.admin import Admin
        self.print_queue = Admin().print_queue
        self.my_name = comm_name
        self.sys_time = Admin().sys_time
        Admin()._add_channel(self)
        self.show_exec = show_exec
        self.printing = printing
        
        self.logger = getLogger("maspy")
        
        from maspy.agent import Belief, Goal, Ask, Plan
        self.data_types = {Belief,Goal,Ask,Plan}
        self.my_name = comm_name
        self.agent_list: Dict[str, Dict[str, Set[str]]] = dict()
        self._agents: Dict[str, 'Agent'] = dict()
        
        # What the send path reads for every message. `_targets` and `_names` are replaced, never mutated (copy-on-write,
        # under self.lock, see _refresh_targets), so senders and log records can use them without a lock and without copying
        self._targets: tuple[tuple[str, str, 'Agent'], ...] = ()    # (full name, name before the first "_", agent)
        self._names: list[str] = []
        self._src_types = (Belief, Goal)
        self._Ask = Ask
        self._act_types: Dict[Any, type] = {        # the kind of data each Act may carry
            tell: Belief, untell: Belief, achieve: Goal, unachieve: Goal,
            askOne: Ask, askOneReply: Ask, askAll: Ask, askAllReply: Ask, askHow: Ask,
            tellHow: Plan, untellHow: Plan,
        }
        
        self._name = f"{type(self).__name__}:{self.my_name}"
        self.send_counter = 0
        self.send_counter_agent: Dict[str,int] = dict()
        self.messages_log: Dict[float, List[Dict[str, Any]]] = dict()
        self._name = f"{type(self).__name__}:{self.my_name}"

        if self.show_exec: self.print(f"Channel {self.my_name} created")
        self.logger.info(f"Channel {self.my_name} created", extra=self.ch_info)
        
    def print(self,*args, **kwargs):
        """Formatted MASPY Print Function"""
        f_args = "".join(map(str, args))
        f_kwargs = "".join(f"{key}={value}" for key, value in kwargs.items())
        msg = f"{self.tcolor}{self._name}> {f_args}{f_kwargs}{bcolors.ENDCOLOR}"
        self.print_queue.put(msg)
        self.logger.info(msg, extra=self.ch_info)
    
    @property
    def get_info(self):
        return {"connected_agents": list(self._names)}
    
    @property
    def ch_info(self):
        return {
                "class_name": "Channel",
                "my_name": self.my_name,
                "connected_agents": self._names
            }

    def _refresh_targets(self) -> None:
        """
        Rebuilds the read-only snapshots used for sending (the caller holds self.lock)
        
        Broadcasts walk `_targets` instead of the live `_agents` dict, so an agent connecting or disconnecting
        in another thread cannot break them, and the name used to skip the sender is split once here, not per message
        """
        self._targets = tuple((name, name.split("_")[0], agent) for name, agent in self._agents.items())
        self._names = [name for name, _, _ in self._targets]    

    def add_agents(self, agents: Union[List['Agent'],'Agent']):
        if isinstance(agents, list):
            for agent in agents:
                self._add_agent(agent)
        else:
            self._add_agent(agents)

    def _add_agent(self, agent: 'Agent'):
        assert isinstance(agent.tuple_name, tuple)
        ag_name = f'{agent.tuple_name[0]}_{str(agent.tuple_name[1])}'
        # if type(agent).__name__ in self.agent_list:
        #     if agent.tuple_name[0] in self.agent_list[type(agent).__name__]:
        #         self.agent_list[type(agent).__name__][agent.tuple_name[0]].update({ag_name})
        #         self._agents[ag_name] = agent
        #     else:
        #         self.agent_list[type(agent).__name__].update({agent.tuple_name[0] : {ag_name}})
        #         self._agents[ag_name] = agent
        # else:
        #     self.agent_list[type(agent).__name__] = {agent.tuple_name[0] : {ag_name}}
        with self.lock:
            self.agent_list.setdefault(type(agent).__name__, {}).setdefault(agent.tuple_name[0], set()).add(ag_name)
            self._agents[ag_name] = agent
            self._refresh_targets()
            
        if self.show_exec: self.print(f"Connecting Agent {type(agent).__name__}:{'_'.join(str(x) for x in agent.tuple_name)}")
        self.logger.info(f"Connecting Agent {type(agent).__name__}:{'_'.join(str(x) for x in agent.tuple_name)}", extra=self.ch_info)

    def rm_agents(self, agents: Union[List['Agent'],'Agent']):
        if isinstance(agents, list):
            for agent in agents:
                self._rm_agent(agent)
        else:
            self._rm_agent(agents)

    def _rm_agent(self, agent: 'Agent'):
        assert isinstance(agent.tuple_name, tuple)
        ag_name = f'{agent.tuple_name[0]}_{str(agent.tuple_name[1])}'
        # if agent.tuple_name in self._agents:
        #     del self._agents[ag_name]
        #     self.agent_list[type(agent).__name__][agent.tuple_name[0]].remove(ag_name)
        with self.lock:
            if self._agents.pop(ag_name, None) is not None:    # was `tuple_name in _agents`: a tuple is never a key, so agents were never removed
                self.agent_list.get(type(agent).__name__, {}).get(agent.tuple_name[0], set()).discard(ag_name)
                self._refresh_targets()

        if self.show_exec: self.print(f"Desconnecting Agent {type(agent).__name__}:{'_'.join(str(x) for x in agent.tuple_name)}")
        self.logger.info(f"Desconnecting Agent {type(agent).__name__}:{'_'.join(str(x) for x in agent.tuple_name)}", extra=self.ch_info)

    def _check_msg(self, act: Act, msg: Any) -> None:
        """Raises AssertionError when `msg` is not the kind of data the Act carries"""
        expected = self._act_types.get(act)
        if expected is not None and not isinstance(msg, expected):
            raise AssertionError(f'Act {act.name} must send {expected.__name__}, sent {msg}')

    def _sendf(self, sender: str, target: str | List[str] | broadcast,  message: Union['Belief', 'Goal', 'Plan', 'Ask'] | List[Union['Belief', 'Goal', 'Plan']], typ: str): 
        if not isinstance(message, list):
            messages = [message]
        if isinstance(target,str) and target != "self" and not target.split("_")[-1].isdigit():
            target = f'{target}_1'
            
        try:
            for msg in messages:
                object.__setattr__(msg, 'source', sender)
                if isinstance(target,list):
                    if self.show_exec: self.print(f'{sender} sending {typ}:{msg} to list {target}')
                    self.logger.info(f'{sender} sending {typ}:{msg} to list {target}', extra=self.ch_info)
                    for trgt in target:
                        assert isinstance(trgt, str) 
                        self._agents[trgt]._save_msg(typ,msg, True)
                        
                elif is_broadcast(target):
                    if self.show_exec: self.print(f'{sender} broadcasting {typ}:{msg}')
                    self.logger.info(f'{sender} broadcasting {typ}:{msg}', extra=self.ch_info) 
                    for agent_name in self._agents.keys():
                        if agent_name != sender and agent_name.split("_")[0] != sender:
                            self._agents[agent_name]._save_msg(typ,msg, True)
                            
                elif isinstance(target, str):
                    if self.show_exec: self.print(f'{sender} sending {typ}:{msg} to {target}')
                    self.logger.info(f'{sender} sending {typ}:{msg} to {target}', extra=self.ch_info) 
                    self._agents[target]._save_msg(typ,msg, True)
        except AssertionError:
            raise
        except KeyError:
            self.logger.warning(f'Agent {target} not connected to {self.my_name} channel', extra=self.ch_info)
        self.logger.info(f'Message Sent', extra=self.ch_info)

    def _send(self, sender: str, target: str | List[str] | type[broadcast], act: Act, message: Union['Belief', 'Goal', 'Ask', 'Plan'] | List[Union['Belief', 'Goal', 'Plan']]) -> None:  
        if isinstance(message, list):
            messages = [self._parse_sent_msg(sender,act,m) for m in message]
        else:
            messages = [self._parse_sent_msg(sender,act,message)]
        
        broadcasting = False
        if isinstance(target,list):
            for trgt in target:
                assert isinstance(trgt, str)
            recipients: Any = target
        elif is_broadcast(target):
            broadcasting = True
            recipients = [name for name, base, _ in self._targets if name != sender and base != sender]
        elif isinstance(target, str):
            recipients = (target,)
        else:
            recipients = ()
        
        log = self.logger.isEnabledFor(INFO)
        for msg in messages:
            if broadcasting:
                if log:
                    extra = self.ch_info
                    extra.update({
                            "sender": sender,
                            "target": "broadcast",
                            "act": act.name if act is not None else None,
                            "information": msg.info if msg is not None else None})
                    self.logger.info(f'{sender} broadcasting {act.name}:{msg}', extra=extra)
                if self.show_exec: self.print(f'{sender} broadcasting {act.name}:{msg}')
            for trgt in recipients:
                self._sending(sender,trgt,act,msg, not broadcasting)
        if log: self.logger.info(f'Message Sent', extra=self.ch_info)
    
    def _sending(self, sender: str, target: str, act: Act, msg: Union['Belief', 'Goal', 'Ask', 'Plan'], broadcast_flag: bool = True) -> None:
        if self.logger.isEnabledFor(INFO):      # the record (and the msg.info dict) is only built when somebody is going to read it
            extra = self.ch_info
            extra.update({
                    "sender": sender,
                    "target": target,
                    "act": act.name if act is not None else None,
                    "information": msg.info if msg is not None else None})
            self.logger.info(f'{sender} sending {act.name}:{msg} to {target}', extra=extra)   
        if self.show_exec: 
            if act.name in ['tell', 'untell', 'achieve', 'unachieve']:
                self.print(f'{sender} sending {act.name}:{msg} to {target}')
            elif act.name in ['askOne', 'askOneReply', 'askAll', 'askAllReply', 'askHow']:
                self.print(f'{sender} asking {act.name}:{msg} from {target}')
        self._check_msg(act, msg)
        agent = self._agents.get(target)
        if agent is None:
            if self.show_exec: self.print(f'Agent {target} not connected')
            self.logger.warning(f'Agent {target} not connected', extra=self.ch_info)
            return
        agent._save_msg(act, msg, False)
    
    def _parse_sent_msg(self, sender: str, act: Act, msg: Union['Belief', 'Goal', 'Ask', 'Plan']) -> Union['Belief', 'Goal', 'Ask', 'Plan']:
        if msg is not None and isinstance(msg, self._src_types):
            object.__setattr__(msg, 'source', sender)
            if act is askOne or act is askAll:
                msg = Ask(msg, source=sender)
        return msg