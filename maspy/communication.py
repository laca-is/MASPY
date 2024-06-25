from threading import Lock
from collections.abc import Iterable
from typing import Dict, TypeVar, TYPE_CHECKING, Union, Any

if TYPE_CHECKING:
    from maspy.agent import Agent, Belief, Goal, Ask, Plan

Agt_name = TypeVar('Agt_name', bound=str)
Agt_cls = TypeVar('Agt_cls', bound=str)
Agt_inst = TypeVar('Agt_inst', bound=object)
Agt_fullname = TypeVar('Agt_fullname', bound=tuple[str,int])

tell= TypeVar('tell')
untell = TypeVar('untell')
tellHow = TypeVar('tellHow')
untellHow = TypeVar('untellHow')
achieve = TypeVar('achieve')
unachieve = TypeVar('unachieve')
askOne = TypeVar('askOne')
askAll = TypeVar('askAll')
askHow = TypeVar('askHow')

ACT = Union[tell,untell,tellHow,untellHow,achieve,unachieve,askOne,askAll,askHow]

broadcast = TypeVar('broadcast')


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
        # dict[Agt_cls, dict[Agt_name, set[Agt_fullname]]]
        self.agent_list: dict[str, dict[str, set[tuple]]] = dict()
        # dict[Agt_fullname, Agt_inst]
        self._agents: dict[tuple, 'Agent'] = dict()
        self._name = f"{type(self).__name__}:{self._my_name}"
        
    def print(self,*args, **kwargs):
        return print(f"{self._name}>",*args,**kwargs)
    
    def add_agents(self, agents: Union[list['Agent'],'Agent']):
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
                self._agents[agent.my_name] = agent
            else:
                self.agent_list[type(agent).__name__].update({agent.my_name[0] : {agent.my_name}})
                self._agents[agent.my_name] = agent
        else:
            self.agent_list[type(agent).__name__] = {agent.my_name[0] : {agent.my_name}}
            self._agents[agent.my_name] = agent
        
        self.print(f'Connecting agent {type(agent).__name__}:{agent.my_name}') if self.show_exec else ...

            
    def _rm_agents(self, agents: Union[list['Agent'],'Agent']):
        if isinstance(agents, list):
            for agent in agents:
                self._rm_agent(agent)
        else:
            self._rm_agent(agents)

    def _rm_agent(self, agent: 'Agent'):
        assert isinstance(agent.my_name, tuple)
        if agent.my_name in self._agents:
            del self._agents[agent.my_name]
            del self.agent_list[type(agent).__name__][agent.my_name[0]]
        self.print(
            f"Desconnecting agent {type(agent).__name__}:{agent.my_name}"
        ) if self.show_exec else ...

    def _send(self, sender: tuple, target: Union[Agt_name, Iterable[Agt_name], broadcast], act: ACT | str, message: Union[str, 'Belief', 'Goal', 'Ask', 'Plan'] | list[Union[str, 'Belief', 'Ask', 'Goal', 'Plan']]):  
        if type(act) == TypeVar: 
            act = act.__name__ 
        
        messages = []
        if isinstance(message, list):
            for m in message:
                messages.append(self.parse_sent_msg(sender,act,m))
        else:
            messages.append(self.parse_sent_msg(sender,act,message))
        try:
            for msg in messages:
                if type(target) == Iterable:
                    for trgt in target:
                        self._sending(sender,trgt,act,msg)
                elif is_broadcast(target):
                    for agent_name in self._agents.keys():
                        if agent_name != sender:
                            self._sending(sender,agent_name,act,msg)
                else:
                    self._sending(sender,target,act,msg)
        except AssertionError:
            raise
    
    def _sending(self, sender, target, act, msg):
        self.print(f"{sender} sending {act}:{msg} to {target}") if self.show_exec else ...        

        from maspy.agent import Belief, Goal, Ask, Plan
        try:
            match act:
                case "tell"|"untell": 
                    assert isinstance(msg, Belief),f'Act {act} must send Belief'
                case "achieve"|"unachieve": 
                    assert isinstance(msg, Goal),f'Act {act} must send Goal'
                case "askOne"|"askAll"|"askHow": 
                    assert isinstance(msg, Ask),f'Act {act} must send Ask' 
                case "tellHow"|"untellHow": 
                    assert isinstance(msg, Plan),f'Act {act} must send Plan'
            self._agents[target].save_msg(act,msg)
        except KeyError:
            self.print(f"Agent {target} not connected")
        except AssertionError:
            raise
    
    def parse_sent_msg(self,sender, act, msg):
        from maspy.agent import Belief, Goal, Ask
        if type(msg) in {Belief, Goal} and msg is not None:
            msg = msg.update(source=sender)
        if act in {"askOne","askAll","askHow"}:
            msg = Ask(msg, source=sender)
        return msg