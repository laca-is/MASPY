from threading import Lock
from typing import Any, Dict, Optional, Set

class EnvironmentMultiton(type):
    _instances: Dict[str, "Environment"] = {}
    _lock: Lock = Lock()

    def __call__(cls, __my_name="env"):
        with cls._lock:
            if __my_name not in cls._instances:
                instance = super().__call__(__my_name)
                cls._instances[__my_name] = instance
        return cls._instances[__my_name]

class Environment(metaclass=EnvironmentMultiton):
    def __init__(self, env_name: str):
        self.full_log = False
        self._my_name = env_name
        self.agent_list = {}
        self._agents = {}
        self._name = f"Environment:{self._my_name}"
        self._facts: Dict[str, Any] = {"any": {}}
        self._roles = {"any"}
    
    def print(self,*args, **kwargs):
        return print(f"{self._name}>",*args,**kwargs)
    
    def perception(self,role):
        return self._get_facts(role)
    
    def add_agents(self, agents):
        try:
            for agent in agents:
                self._add_agent(agent)
            #self.send_agents_list()
        except TypeError:
            self._add_agent(agents)
    
    def _add_agent(self, agent):
        if agent.my_name not in self._agents:
            
            self.agent_list[type(agent).__name__] = agent.my_name
            self._agents[agent.my_name] = agent
            
            self.print(f'Connecting agent {type(agent).__name__}:{agent.my_name} to Environment')
        else:
            self.print(f'Agent {type(agent).__name__}:{agent.my_name} already connected')
    
    def _add_role(self, role_name: str):
        if type(role_name) == str:
            self._roles.add(role_name)
        else:
            self.print(f"role *{role_name}* is not a string")

    def _rm_role(self, role_name: str):
        self._roles.remove(role_name)

    def _get_roles(self) -> Set[str]:
        return self._roles
    
    def _check_role(self, role: str) -> bool:
        return role in self._roles
    
    def get_fact_value(self, name: str, role="any"):
        try:
            return self._facts[role][name]
        except KeyError:
            return None
    
    def create_fact(self, name: str, data: Any, role="any"):
        if role != "any":
            if role not in self._roles:
                self._add_role(role)

        if role in self._facts:
            if name not in self._facts[role]:
                self._facts[role].update({name : data})
            else:
                self.print(f"> Fact *{name}:{role}* already created")
        else:
            self._facts[role] = {name: data}
        self.print(f"Creating fact {role}:{name}:{data}") if self.full_log else ...

    def update_fact(self, name: str, data: Any, role="any"):
        if self._fact_exists(name, role):
            self.print(f"Updating fact {role}:{name}:[{self._facts[role][name]} > ",end="") if self.full_log else ...
            self._facts[role] = {name: data}
            print(f"{self._facts[role][name]}]") if self.full_log else ...
            
    def _extend_fact(self, name: str, data: str, role="any"):
        if not self._fact_exists(name, role):
            return
        try:
            self.print(f"Extending fact {role}:{name}[{self._facts[role][name]} > ",end="") if self.full_log else ...
            match self._facts[role][name]:
                case list() | tuple():
                    self._facts[role][name].append(data)
                case dict() | set():
                    self._facts[role][name].update(data)
                case int() | float() | str():
                    self.print(f"Impossible to extend fact {name}:{type(data)}")
            print(f"{self._facts[role][name]}]") if self.full_log else ...
        except (TypeError, ValueError):
            self.print(f"Fact {name}:{type(self._facts[role][name])} can't extend {type(data)}")

    def _reduce_fact(self, name, data, role="any"):
        if not self._fact_exists(name, role):
            return
        try:
            match self._facts[role][name]:
                case list() | set():
                    self._facts[role][name].remove(data)
                case dict():
                    self._facts[role][name].pop(data)
                case tuple():
                    old_tuple = self._facts[role][name]
                    self._facts[role][name] = tuple(x for x in old_tuple if x != data)
                case int() | float() | str():
                    self.print(f"> Impossible to reduce fact {name}:{type(data)}")
        except (KeyError, ValueError):
            self.print(f"> Fact {name}:{type(self._facts[role][name])} doesn't contain {data}")

    def _fact_exists(self, name: str, role: str) -> bool:
        try:
            self._facts[role][name]
        except KeyError:
            self.print(f"> Fact {name}:{role} doesn't exist")
            return False
        return True

    def _rm_fact(
        self, del_name: str, del_data: Any = None, del_role: Optional[str] = None
    ):
        if del_role is None:
            for role in self._roles:
                if del_name in self._facts[role].keys():
                    if del_data is None:
                        del self._facts[role][del_name]
                    elif del_data in self._facts[role][del_name].keys():
                        del self._facts[role][del_name][del_data]

    def _get_facts(self, agent_role: Optional[str] = None):
        found_facts = {}
        for role in self._roles:
            if role == agent_role or role == "any" or agent_role == "all":
                for fact in self._facts[role]:
                    found_facts[fact] = self._facts[role][fact]
        return found_facts

