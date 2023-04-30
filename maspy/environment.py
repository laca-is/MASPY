from threading import Lock
from typing import Any, Dict, Optional, Set

"""
gerenciar 
    caracteristicas do ambiente
    artefato do ambiente
    cargo de agentes neste ambiente
    comunicacao do ambiente
"""

"""
Get perception:
    verificar situacao do ambiente
        -olhar todas caracteristicas
        -considerar cargo do agente

"""


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
    def __init__(self, env_name):
        self._my_name = env_name
        self.__env_channel = None
        self._facts: Dict[str, Any] = {"any": {}}
        self._roles = {"any"}
    
    def perception(self):
        return self.get_facts("all")
    
    def add_channel(self, channel):
        self.__env_channel = channel
    
    def _add_role(self, role_name: str):
        if type(role_name) == str:
            self._roles.add(role_name)
        else:
            print(f"{self._my_name}> role *{role_name}* is not a string")

    def _rm_role(self, role_name: str):
        self._roles.remove(role_name)

    def _get_roles(self) -> Set[str]:
        return self._roles
    
    def _check_role(self, role: str) -> bool:
        return role in self._roles
    
    def _create_fact(self, name: str, data: Any, role="any"):
        if role != "any":
            if role not in self._roles:
                self._add_role(role)

        if role in self._facts:
            if name not in self._facts[role]:
                self._facts[role] = {name : data}
            else:
                print(f"{self._my_name}> Fact *{name}:{role}* already created")
        else:
            self._facts[role] = {name: data}
        print(f'{self._my_name}> Creating fact {role}:{name}:{data}')

    def _update_fact(self, name: str, data: Any, role="any"):
        if self._fact_exists(name, role):
            print(f"{self._my_name}> Updating fact {role}:{name}:[{self._facts[role][name]} > ",end="")
            self._facts[role] = {name: data}
            print(f"{self._facts[role][name]}]")

    def _extend_fact(self, name: str, data: str, role="any"):
        if not self._fact_exists(name, role):
            return
        try:
            print(f"{self._my_name}> Extending fact {role}:{name}[{self._facts[role][name]} > ",end="")
            match self._facts[role][name]:
                case list() | tuple():
                    self._facts[role][name].append(data)
                case dict() | set():
                    self._facts[role][name].update(data)
                case int() | float() | str():
                    print(
                        f"{self._my_name}> Impossible to extend fact {name}:{type(data)}"
                    )
            print(f"{self._facts[role][name]}]")
        except (TypeError, ValueError):
            print(
                f"{self._my_name}> Fact {name}:{type(self._facts[role][name])} can't extend {type(data)}"
            )

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
                    print(
                        f"{self._my_name}> Impossible to reduce fact {name}:{type(data)}"
                    )
        except (KeyError, ValueError):
            print(
                f"{self._my_name}> Fact {name}:{type(self._facts[role][name])} doesn't contain {data}"
            )

    def _fact_exists(self, name: str, role: str) -> bool:
        try:
            self._facts[role][name]
        except KeyError:
            print(f"{self._my_name}> Fact {name}:{role} doesn't exist")
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
        print(self._facts)
        found_facts = {}
        for role in self._roles:
            if role == agent_role or role == "any" or agent_role == "all":
                for fact in self._facts[role]:
                    found_facts[fact] = self._facts[role][fact]
        return found_facts
