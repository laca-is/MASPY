from __future__ import annotations
from typing import Any, Callable, Optional, TYPE_CHECKING
from threading import Lock

if TYPE_CHECKING:
    from maspy.agent import Belief, Goal

class bcolorsMeta(type):
    _instances: dict[str, Any] = {}
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                instance = super().__call__(*args, **kwargs)
                cls._instances[cls] = instance
        return cls._instances[cls]

class bcolors(bcolorsMeta):
    CYAN    = '\033[36m'
    MAGENTA = '\033[35m'
    BLUE    = '\033[34m'
    YELLOW  = '\033[33m'
    GREEN   = '\033[32m'
    RED     = '\033[31m'
    
    BRT_CYAN     = '\033[96m'
    BRT_MAGENTA  = '\033[95m'
    BRT_BLUE     = '\033[94m'
    BRT_YELLOW   = '\033[93m'
    BRT_GREEN    = '\033[92m'
    BRT_RED      = '\033[91m'
    
    ORANGE = '\033[38;5;208m'
    PINK = '\033[38;5;205m'
    TEAL = '\033[38;5;37m'
    LIME = '\033[38;5;154m'
    PURPLE = '\033[38;5;99m'
    GOLD = '\033[38;5;220m'
    SALMON = '\033[38;5;210m'
    TURQUOISE = '\033[38;5;81m'
    VIOLET = '\033[38;5;129m'
    LIGHT_BLUE = '\033[38;5;39m'
    LIGHT_GREEN = '\033[38;5;83m'
    LIGHT_YELLOW = '\033[38;5;228m'
    
    RESET = '\033[39m'
    ENDCOLOR = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
    Colors_Dict: dict[str, tuple[int,list]] = {
        "Agent": (0,[
        RED, PURPLE, MAGENTA, ORANGE, TEAL, SALMON, BRT_RED, PINK, BRT_MAGENTA  ]),
        "Env": (0,[GREEN, LIME, BRT_GREEN, LIGHT_GREEN  ]),
        "Channel": (0,[BLUE, TURQUOISE, BRT_BLUE, LIGHT_BLUE ]),
    }

    @classmethod
    def get_color(cls, t_name: str):
        num = cls.Colors_Dict[t_name][0]
        if num >= len(cls.Colors_Dict[t_name][1]):
            num = 0
        color = cls.Colors_Dict[t_name][1][num]
        cls.Colors_Dict[t_name] = (num + 1, cls.Colors_Dict[t_name][1])
        return color

class Condition:
    def __init__(self, c_type: str, str_type: str, left_value: Condition | Belief | Goal, right_value: Condition | Belief | Goal | None = None, func: Optional[Callable] = None) -> None:
        self.c_type = c_type
        self.str_type = str_type
        self.func = func
        self.left_value = left_value
        self.right_value = right_value
    
    def __invert__(self):
        return Condition("~", "~", self)
    
    def __and__(self, other):
        return Condition("op", "&",self, other, lambda x,y: x & y)
        
    def __or__(self, other):
        return Condition("op", "|", self, other, lambda x,y: x | y)
    
    def __xor__(self, other):
        return Condition("op", "^", self, other, lambda x,y: x ^ y)
    
    def __lt__(self, other):
        return Condition("comp", "<", self,other, lambda x,y: x < y)
    
    def __le__(self, other):
        return Condition("comp", "<=", self,other, lambda x,y: x <= y)
    
    def __gt__(self, other):
        return Condition("comp", ">", self,other, lambda x,y: x > y)
    
    def __ge__(self, other):
        return Condition("comp", ">=", self,other, lambda x,y: x >= y)
    
    def __ne__(self, value):
        return Condition("comp", "!=", self,value, lambda x,y: x != y)
    
    def __str__(self) -> str:
        if self.right_value is None:
            return f'{self.str_type}{self.left_value}'
        else:
            return f'({self.left_value} {self.str_type} {self.right_value})'
    
    def __repr__(self):
        return self.__str__()

def merge_dicts(dict1: dict[Any, dict[Any, set[Any]]] | None, dict2: dict[Any, dict[Any, set[Any]]] | None) -> dict | None:
    if dict1 is None or dict2 is None:
        return None
    for key, value in dict1.items():
        if key in dict2 and isinstance(value, dict):
            for inner_key, inner_value in value.items():
                if inner_key in dict2[key] and isinstance(inner_value, set):
                    dict2[key][inner_key].update(inner_value)
                else:
                    dict2[key][inner_key] = inner_value 
        else:
            dict2[key] = value
    return dict2


def set_changes(original:set, changes:set):
    intersection = original.intersection(changes)
    added = changes - original
    removed = original - intersection
    return intersection.union(added), added, removed

def manual_deepcopy(d: dict[Any, dict[Any, set[Any]]]) -> dict[Any, dict[Any, set[Any]]]:
    return {k: {k2: set(v2) for k2, v2 in v.items()} for k, v in d.items()}