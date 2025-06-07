from typing import Any, Generic, Tuple, TypeVar, SupportsFloat
import numpy as np

from maspy.learning.space import Space, Discrete
from maspy.learning.ml_utils import utl_np_random, categorical_sample

ObsType = TypeVar("ObsType")
ActType = TypeVar("ActType")

class HashableWrapper:
    def __init__(self, obj):
        self.original = obj
        self.original_type = type(obj)
        self.hashable = self._make_hashable(obj)

    def _make_hashable(self, obj):
        if isinstance(obj, dict):
            return frozenset((k, self._make_hashable(v)) for k, v in obj.items())
        elif isinstance(obj, (tuple)):
            return tuple(self._make_hashable(v) for v in obj)
        elif isinstance(obj, set):
            return frozenset(self._make_hashable(v) for v in obj)
        elif isinstance(obj, list) and len(obj) == 1:
            self.original = obj[0]
            return self._make_hashable(obj[0])
        else:
            return obj  # Already hashable
    
    def __hash__(self):
        return hash(self.hashable)
    
    def __eq__(self, other):
        return isinstance(other, HashableWrapper) and self.hashable == other.hashable
    
    def __iter__(self):
        return iter(self.hashable)
    
    def __repr__(self):
        return f"*{self.original}"


class Model(Generic[ObsType, ActType]):
    
    action_space: Space[ActType]
    observation_space: Space[ObsType]
    initial_state_distrib: list[HashableWrapper]
    P: dict[HashableWrapper, dict[ActType, list[tuple]]]
    curr_state: HashableWrapper
    last_action: ActType | None
    states_buffer: list[str]
    
    _np_random: np.random.Generator | None = None
    _np_random_seed: int | None = None

    def look(self, action: ActType) -> Tuple[tuple, SupportsFloat, bool, bool, dict[str, Any]]:
        transitions = self.P[self.curr_state][action]
        i = categorical_sample([t[0] for t in transitions], self.np_random)
        p, s, r, t = transitions[i]
        return s, r, t, False, {"prob": p}#, "action_mask": self.action_mask(s)})

    def step(self, action: ActType) -> Tuple[HashableWrapper, SupportsFloat, bool, bool, dict[str, Any]]:
        try:
            transitions = self.P[self.curr_state][action]
            #print(f'\n## Transitions > {self.curr_state} : {action} [{self.P[self.curr_state]}] = {transitions}')
        except KeyError:
            print(f'\n## Key Error > {self.curr_state} : {action}')
            for buff in self.states_buffer:
                print(buff)
            raise KeyError
        i = categorical_sample([t[0] for t in transitions], self.np_random)
        p, s, r, t = transitions[i]
        self.curr_state = s
        #print("Core Step", self.curr_state)
        self.last_action = action
        assert self.curr_state is not None, "State cannot be None after step"
        return self.curr_state, r, t, False, {"prob": p}
        
    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None) -> Tuple[tuple | HashableWrapper, dict[str, Any]]: # type: ignore
        if seed is not None:
            self._np_random, self._np_random_seed = utl_np_random(seed)
        
        self.curr_state = self.initial_state_distrib[np.random.randint(0, len(self.initial_state_distrib))] 
        #print("Core Reset", self.curr_state)
        self.last_action = None
        assert self.curr_state is not None, "State cannot be None after reset"
        return self.curr_state, {"prob": 1.0}

    def set_state(self, state) -> Tuple[HashableWrapper, dict]: 
        if not isinstance(state, HashableWrapper):
            state = HashableWrapper(state)
        self.curr_state = state
        self.last_action = None
        
        return self.curr_state, {"prob": 1.0}#, "action_mask": self.action_mask(self.s)}
    
    @property
    def np_random_seed(self) -> int:
        if self._np_random_seed is None:
            self._np_random, self._np_random_seed = utl_np_random()
        return self._np_random_seed
    
    @property
    def np_random(self) -> np.random.Generator:
        if self._np_random is None:
            self._np_random, self._np_random_seed = utl_np_random()
        return self._np_random
    
    @np_random.setter
    def np_random(self, value: np.random.Generator) -> None:
        self._np_random = value
        self._np_random_seed = -1
