from threading import Lock
from typing import Dict, Set, List, TYPE_CHECKING, Union, Any
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

    def __call__(cls, __my_name="default"):
        with cls._lock:
            if __my_name not in cls._instances:
                instance = super().__call__(__my_name)
                cls._instances[__my_name] = instance
        return cls._instances[__my_name]


class Channel(metaclass=CommsMultiton):
    def __init__(self, comm_name:str="default"):
        self.show_exec = False
        
        from maspy.admin import Admin
        self._my_name = comm_name
        Admin()._add_channel(self)
        
        from maspy.agent import Belief, Goal, Ask, Plan
        self.data_types = {Belief,Goal,Ask,Plan}
        self._my_name = comm_name
        self.agent_list: Dict[str, Dict[str, Set[tuple[str, int]]]] = dict()
        self._agents: Dict[str, 'Agent'] = dict()
        self._name = f"{type(self).__name__}:{self._my_name}"
        self.send_counter = 0
        self.send_counter_agent: Dict[str,int] = dict()
        
    def print(self,*args, **kwargs):
        return print(f"{self._name}>",*args,**kwargs)
    
    @property
    def get_info(self):
        return {"connected_agents": list(self._agents.keys()).copy()}
    
    def add_agents(self, agents: Union[List['Agent'],'Agent']):
        if isinstance(agents, list):
            for agent in agents:
                self._add_agent(agent)
        else:
            self._add_agent(agents)

    def _add_agent(self, agent: 'Agent'):
        assert isinstance(agent.my_name, tuple)
        if type(agent).__name__ in self.agent_list:
            if agent.my_name[0] in self.agent_list[type(agent).__name__]:
                self.agent_list[type(agent).__name__][agent.my_name[0]].update({agent.my_name})
                self._agents[agent.str_name] = agent
            else:
                self.agent_list[type(agent).__name__].update({agent.my_name[0] : {agent.my_name}})
                self._agents[agent.str_name] = agent
        else:
            self.agent_list[type(agent).__name__] = {agent.my_name[0] : {agent.my_name}}
            self._agents[agent.str_name] = agent
        
        self.print(f'Connecting agent {type(agent).__name__}:{agent.my_name}') if self.show_exec else ...

            
    def _rm_agents(self, agents: Union[List['Agent'],'Agent']):
        if isinstance(agents, list):
            for agent in agents:
                self._rm_agent(agent)
        else:
            self._rm_agent(agents)

    def _rm_agent(self, agent: 'Agent'):
        assert isinstance(agent.my_name, tuple)
        if agent.my_name in self._agents:
            del self._agents[agent.str_name]
            self.agent_list[type(agent).__name__][agent.my_name[0]].remove(agent.my_name)
        self.print(
            f"Desconnecting agent {type(agent).__name__}:{agent.my_name}"
        ) if self.show_exec else ...

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
                        assert isinstance(trgt, tuple)
                        self._sending(sender,trgt,act,msg)
                elif is_broadcast(target):
                    for agent_name in self._agents.keys():
                        if agent_name != sender:
                            self._sending(sender,agent_name,act,msg)
                elif isinstance(target, str):
                    self._sending(sender,target,act,msg)
        except AssertionError:
            raise
        
        with Lock():
            self.send_counter += 1
            sender = sender.split("_")[0]
            if sender not in self.send_counter_agent:
                self.send_counter_agent[sender] = 1
            else:
                self.send_counter_agent[sender] += 1
    
    def _sending(self, sender: str, target: str, act: Act, msg: Union['Belief', 'Goal', 'Ask', 'Plan']):
        self.print(f"{sender} sending {act.name}:{msg} to {target}") if self.show_exec else ...        

        from maspy.agent import Belief, Goal, Ask, Plan
        try:
            if act in [tell,untell]: 
                assert isinstance(msg, Belief),f'Act {act} must send Belief'
            elif act in [achieve, unachieve]: 
                assert isinstance(msg, Goal),f'Act {act} must send Goal'
            elif act in [askOne,askOneReply,askAll,askAllReply,askHow]: 
                assert isinstance(msg, Ask),f'Act {act} must send Ask' 
            elif act in [tellHow,untellHow]: 
                assert isinstance(msg, Plan),f'Act {act} must send Plan'
            self._agents[target].save_msg(act,msg)
        except KeyError:
            self.print(f"Agent {target} not connected")
        except AssertionError:
            raise
    
    def parse_sent_msg(self, sender: str, act: Act, msg: Union['Belief', 'Goal', 'Ask', 'Plan']):
        from maspy.agent import Belief, Goal
        if isinstance(msg, Belief | Goal) and msg is not None:
            msg = msg.update(source=sender)
        if act in [askOne,askAll] and isinstance(msg, Belief | Goal):
            msg = Ask(msg, source=sender)
        return msg