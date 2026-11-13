from typing import TYPE_CHECKING, Any, Sequence, Optional, Mapping, Callable, cast
from collections import defaultdict
from maspy.learning.core import Model, HashableWrapper
from maspy.learning.space import Discrete, Box, as_box
from maspy.learning.ml_utils import monte_carlo_selection, utl_np_random, TileCoder
from logging import getLogger
from enum import Enum
from itertools import product, combinations, permutations
import numpy as np
import pickle
import sys

if TYPE_CHECKING:
    from maspy.agent import Agent
    from maspy.environment import Environment, Action

Learn_Method = Enum('qlearning | sarsa | actor_critic', ['qlearning', 'sarsa', 'actor_critic']) # type: ignore[misc]

qlearning = Learn_Method.qlearning
sarsa = Learn_Method.sarsa
actor_critic = Learn_Method.actor_critic

Group = Enum('sequence | combination | permutation | cartesian | listed | continuous', ['sequence', 'combination', 'permutation', 'cartesian', 'listed', 'continuous']) # type: ignore[misc]

sequence = Group.sequence
combination = Group.combination
permutation = Group.permutation
cartesian = Group.cartesian
listed = Group.listed
continuous = Group.continuous

DEFAULT_STATE_BINS = 10     # tiles per dimension (of each tiling) used for continuous states
DEFAULT_ACTION_BINS = 5     # grid points per dimension used to quantize continuous actions
MAX_ACTION_GRID = 10_000    # largest quantized action set accepted for one continuous action

def _resolve_bins(spec: int | Sequence[int] | Mapping[str, Any], key: str, size: int, default: int) -> np.ndarray:
    """ Number of bins for each of the `size` dimensions of `key`.
    
    `spec` is either a value applied to every quantity (an int, or a sequence with one entry per dimension)
    or a mapping `{name: int | sequence}` where the quantities that are not listed use `default`.
    """
    if isinstance(spec, Mapping):
        spec = spec.get(key, default)
    try:
        bins = np.broadcast_to(np.asarray(spec, dtype=np.int64), (size,)).copy()
    except ValueError:
        raise ValueError(f"'{key}' has {size} dimension(s), so its bins must be an int or {size} ints, got {spec!r}") from None
    if np.any(bins < 1):
        raise ValueError(f"'{key}': bins must be positive, got {spec!r}")
    return bins

class EnvModel(Model):
    """ The model of the environment 
    
    Discrete states and actions (the `cartesian`, `listed`, ... groups) are enumerated and learnt with a table.
    
    Continuous states and actions are declared with the `continuous` group and a ``(low, high)`` pair
    (or a `Box`), and are never enumerated; the transition functions of the Environment are sampled instead:
    
    * Continuous states are tile coded: the value function is stored sparsely, one entry per active tile.
    * Continuous actions are either quantized into a grid (`qlearning` / `sarsa`),
      or learnt as a real-valued output with a Gaussian policy (`actor_critic`).
    
    Both can be mixed freely with discrete states and actions.
    
    Parameters
    ----------
    env : Environment
        The Environment to model
    agent : Agent, optional
        The Agent that owns the model
    show_learning : bool
        Show a progress bar while training
    bins : int | Sequence[int] | Mapping[str, int | Sequence[int]]
        Tiles per dimension of every tiling, for continuous states. Either one value for all of them,
        or a mapping from the name of the state's Percept to its value(s) [default: 10]
    n_tilings : int
        Number of overlapping tilings of the continuous states. More tilings generalize
        better between nearby states; 1 is plain discretization [default: 8]
    action_bins : int | Mapping[str, int | Sequence[int]]
        Grid points per dimension used to quantize a continuous action when learning with
        `qlearning` or `sarsa`. Either one value for all of them or a mapping from the name of
        the Action's method to its value(s) [default: 5]
    terminal : Callable[[dict], bool], optional
        Tells, from the same ``{name: value}`` state dict that the transitions receive, whether a state is terminal.
        It is only used when an Agent executes the model (`get_state`); training takes the termination from the transitions.
        Without it the terminal states seen while training are remembered, and a state counts as terminal when it falls 
        in the same small region (a tile divided by `n_tilings`) as one of them, which is only approximate
    greedy : bool, optional
        How `qlearning` and `sarsa` exploit what they learnt. With ``True`` the action with the highest value is 
        taken (ties are broken at random). With ``False`` an action is drawn with probability proportional to its 
        normalized value, which is what the discrete models have always done. Defaults to ``True`` for models with 
        continuous parts and ``False`` otherwise: quantized continuous actions have many neighbouring actions with 
        similar values, and drawing among them blurs the policy
    
    Notes
    -----
    For models with continuous parts the transition functions follow the convention
    ``transition(env, state: dict, [action_value]) -> (next_state: dict, reward, [terminated])``.
    The values of continuous states and actions are a ``float`` when declared with scalar bounds and
    a ``np.ndarray`` when declared with sequence bounds. States that a transition does not return keep their value.
    
    `possible_starts` has to be a dict (not ``"off-policy"``); for a continuous state it accepts a value,
    a list of values or a `Box` to sample from, and defaults to the whole state space.

    The rest of the model works as with discrete models: Agents execute the learnt policy, `get_best_action`,
    `update_learning` (online learning from real steps), `look`, `state_step`, `set_state`, `reset_percepts`,
    `print_policy` and saving/loading. Where a state is given it can be a dict by name or the tuple that `get_state` returns.
    A continuous action learnt with `qlearning` or `sarsa` can only take the values of its grid: raise `action_bins` 
    for finer control, or use `actor_critic` for an output that is not quantized.
    """
    def __init__(self, env: 'Environment', agent: Optional['Agent'] = None, show_learning: bool = False, *, 
                 bins: int | Sequence[int] | Mapping[str, Any] = DEFAULT_STATE_BINS, n_tilings: int = 8, 
                 action_bins: int | Sequence[int] | Mapping[str, Any] = DEFAULT_ACTION_BINS,
                 terminal: Callable[[dict[str, Any]], bool] | None = None,
                 greedy: bool | None = None) -> None:
        super().__init__()
        self.name: str = f'Model_{env.my_name}' if agent is None else f'Model_{agent.my_name}_{env.my_name}'
        self.show_learning = show_learning
        print(f'Creating {self.name}') if show_learning else ...
        self.agent_name: str | None = agent.my_name if agent is not None else None
        self.env: 'Environment' = env
        states: dict[str, Sequence[Any]] = {}
        for name, list_states in env._states.items():
            states.update({name: list_states[0].data})
        actions = env._actions.copy()
        from maspy.environment import Action
        self.actions_list: list[HashableWrapper] = []
        self.actions_dict: dict[HashableWrapper, Action] = {}
        
        self.bins = bins
        self.n_tilings = n_tilings
        self.action_bins = action_bins
        self.terminal = terminal
        self.state_names: list[str] = list(states.keys())
        self.continuous_states: dict[str, Box] = {
            name: as_box(list_states[0].data) 
            for name, list_states in env._states.items() if list_states[0].state_type == "continuous"
        }
        self.continuous_actions: list[tuple[Action, Box]] = []
        self._action_boxes: dict[int, Box] = {}
        self.tile_coder: TileCoder | None = None
        self.continuous_policy: bool = False        
        
        self.orginize_actions(actions)
        
        self._n_discrete_actions: int = len(self.actions_list) - sum(
            1 for act in self.actions_dict.values() if act.act_type == "continuous"
        )
        self.continuous: bool = bool(self.continuous_states or self.continuous_actions)        
        self.greedy: bool = self.continuous if greedy is None else greedy
        
        self.off_policy: bool = False
        self.q_table: dict = dict()
        self.trained = False
        self.logger = getLogger("maspy")
        
        if self.continuous:
            self._init_sampling(env)
            from maspy.admin import Admin
            Admin()._add_model(self)
            self.logger.info(f"Model {self.name} created", extra=self.model_info)
            return
           
        value_lists = list(states.values())
        #print('States: ',value_lists)
        tuples_values: list = []
        for value in value_lists:
            if isinstance(value, list): 
                if len(value_lists) == 1:
                    tuples_values = value_lists
                else:
                    tuples_values.append(tuple(value))
            elif not type(value).__dict__.get("__hash__"):
                tuples_values.append((value,))
            else:
                tuples_values.append(value)
        #print('Tuples: ',tuples_values)
        aux_list = list(product(*tuples_values))
        self.states_list: list[HashableWrapper] = []
        for stt in aux_list:
            #print('Moddeling: ',stt)
            self.states_list.append(HashableWrapper(stt))
        
        self.terminated_states: list[HashableWrapper] = []
        
        self.num_actions: int = len(self.actions_list)
        self.P = {
            state: {action: [] for action in range(self.num_actions)}
            for state in self.states_list
        }
        
        if isinstance(env.possible_starts,str):
            if env.possible_starts == "off-policy":
                self.initial_state_distrib = self.states_list.copy() 
                self.initial_states = states
                self.off_policy = True
            else:
                raise TypeError(f'Error: possible_starts must be a {dict} when not "off-policy", got {env.possible_starts} instead')
        else:
            self.make_policy_table(env, states)
            
        #print("initial_state_distrib:", self.initial_state_distrib)
        #print("len:", len(self.initial_state_distrib))
        self.curr_state = self.initial_state_distrib[np.random.randint(0, len(self.initial_state_distrib))]     
        self.action_space = Discrete(len(self.actions_list))
        self.observation_space = Discrete(len(self.states_list))
        
        from maspy.admin import Admin
        Admin()._add_model(self)
        self.logger.info(f"Model {self.name} created", extra=self.model_info)
    
    
    @property
    def model_info(self) -> dict[str, Any]:
        table = self.policy_table if self.continuous_policy else self.q_table
        qtable = {
            str(getattr(key, "original", key)): [value for value in values]
            for key, values in table.items()
        }
        
        return {
            "class_name": "Learning",
            "my_name": self.name,
            "environment": self.env.my_name,
            "agent": self.agent_name,
            "policy": qtable,
            "learning parameters": {
                "learning_method": self.learning_method,
                "discount_factor": self.discount_factor,
                "learning_rate": self.learning_rate,
                "epsilon": self.epsilon,
                "epsilon_decay": self.epsilon_decay,
                "final_epsilon": self.final_epsilon,
                "off_policy": self.off_policy
                                    } if self.trained else None,
        }
    
    def print_policy(self, key=None):
        if self.continuous:
            if key is not None:
                state = self._user_state(key)
                if self.continuous_policy:
                    return f'State: {state} - Action: {self._policy_action(state)}\n'
                return f'State - Actions {self.actions_list}\nState: {state} - Value: {self._q_values(state)}\n'
            table = self.policy_table if self.continuous_policy else self.q_table
            buffer = f'State - Actions {self.actions_list}\n'
            for key, value in table.items():
                buffer += f'Key: {key} - Value: {value}\n'
            return buffer
        
        if key is not None:
            if not isinstance(key, tuple):
                key = (key,)
            key = HashableWrapper(key)
            return f'State - Actions {self.actions_list}\nKey: {key} - Value: {self.q_table[key]}\n'
        buffer = f'State - Actions {self.actions_list}\n'
        for key, value in self.q_table.items():
            buffer += f'Key: {key} - Value: {value}\n'
        return buffer
    
    def reset_percepts(self) -> None:
        """ Reset the state and percepts of the environment """
        self.reset()
        from maspy.environment import Percept
        for stt, (name, _) in zip(self.curr_state, self.initial_states.items()):
            percept = self.env.get(Percept(name),ck_values=False)
            if isinstance(stt, frozenset):
                stt = dict(stt)
            assert isinstance(percept, Percept)
            self.env.change(percept,values=stt)
    
    def orginize_actions(self, actions: list['Action']) -> None:
        """ Organize the actions of the modelled environment """
        for action in actions:
            if action.act_type == 'listed':
                for args in action.data:
                    args = HashableWrapper(args)
                    self.actions_list.append(args)
                    self.actions_dict[args] = action
                                
            elif action.act_type == 'combination':
                act_comb: list = []
                for i in range(1, len(action.data) + 1):
                    act_comb.extend(combinations(action.data, i))
                for args in act_comb:
                    args = HashableWrapper(args)
                    self.actions_list.append(args)
                    self.actions_dict[args] = action
                    
            elif action.act_type == "permutation":
                act_perm: list = []
                for i in range(1, len(action.data) + 1):
                    act_perm.extend(permutations(action.data, i))
                for args in act_perm:
                    args = HashableWrapper(args)
                    self.actions_list.append(args)
                    self.actions_dict[args] = action
                
            elif action.act_type == "cartesian":
                ranges: list = []
                for args in action.data:
                    if isinstance(args, str):
                        ranges.append([args])
                    elif isinstance(args, Sequence):
                        ranges.append(args)
                    elif isinstance(args, int):
                        ranges.append(range(args))
                act_cart = list(product(*ranges))
                for args in act_cart:
                    args = HashableWrapper(args)
                    self.actions_list.append(args)
                    self.actions_dict[args] = action
            elif action.act_type == "continuous":
                self._add_continuous_action(action)
            else:
                print(f"Unsupported action type: {action.act_type}")
    
    def _add_continuous_action(self, action: 'Action') -> None:
        """ Registers a continuous action and quantizes it into a grid of actions (used by `qlearning` and `sarsa`) """
        box = as_box(action.data)
        name = getattr(action.func, "__name__", "continuous")
        if not box.is_bounded():
            raise ValueError(f"Continuous action '{name}' needs finite bounds, got {box}")
        self.continuous_actions.append((action, box))
        self._action_boxes[id(action)] = box
        
        bins = _resolve_bins(self.action_bins, name, box.size, DEFAULT_ACTION_BINS)
        if int(np.prod(bins, dtype=np.int64)) > MAX_ACTION_GRID:
            raise ValueError(
                f"Quantizing continuous action '{name}' with bins={bins.tolist()} gives more than {MAX_ACTION_GRID} actions; "
                f"lower action_bins, or learn it with actor_critic"
            )
        axes = [
            np.linspace(low, high, n) if n > 1 else np.array([(low + high) / 2])
            for low, high, n in zip(box.low.ravel(), box.high.ravel(), bins)
        ]
        for point in product(*axes):
            args = HashableWrapper(float(point[0]) if box.shape == () else tuple(float(v) for v in point))
            # grids of different actions can hold the same values, the name keeps them apart
            args.hashable = (name, args.hashable)
            self.actions_list.append(args)
            self.actions_dict[args] = action
    
    def _init_sampling(self, env: 'Environment') -> None:
        """ Prepares a model with continuous states and/or actions. 
        
        There is nothing to enumerate: no transition table is built, 
        the transition functions are called on the fly while learning.
        """
        if isinstance(env.possible_starts, str):
            raise TypeError(
                f'possible_starts="{env.possible_starts}" cannot be used with continuous states or actions, '
                f'use a dict instead (the continuous states that it does not list start anywhere in their space)'
            )
        self.states_list = []
        self.P = {}
        self.terminated_states = []
        self._terminal_cells: set = set()
        self._disc_idx: list[int] = [i for i, n in enumerate(self.state_names) if n not in self.continuous_states]
        self._cont_idx: list[int] = [i for i, n in enumerate(self.state_names) if n in self.continuous_states]
        
        self.initial_states = {}
        self._start_options: dict[str, Box | list] = {}
        for name in self.state_names:
            if name in self.continuous_states:
                default: Any = self.continuous_states[name]
            else:
                default = env._states[name][0].data
            spec = env.possible_starts.get(name, default)
            self.initial_states[name] = spec
            if isinstance(spec, Box):
                self._start_options[name] = spec
            elif isinstance(spec, (list, tuple, set)):
                self._start_options[name] = list(spec)
            else:
                self._start_options[name] = [spec]
        
        if self.continuous_states:
            lows: list[np.ndarray] = []
            highs: list[np.ndarray] = []
            bins: list[np.ndarray] = []
            for name, box in self.continuous_states.items():
                if not box.is_bounded():
                    raise ValueError(f"Continuous state '{name}' needs finite bounds to be tile coded, got {box}")
                lows.append(box.low.ravel())
                highs.append(box.high.ravel())
                bins.append(_resolve_bins(self.bins, name, box.size, DEFAULT_STATE_BINS))
            low, high = np.concatenate(lows), np.concatenate(highs)
            self.tile_coder = TileCoder(low, high, np.concatenate(bins), self.n_tilings)
            self.observation_space = Box(low, high)
        
        self.num_actions = len(self.actions_list)
        self.action_space = Discrete(self.num_actions)
        self.reset()
    
    def make_policy_table(self, env: 'Environment', states: dict[str, Sequence]) -> None:
        """ Creates the policy table based on the states and actions lists """
        state: dict = {}
        keys = states.keys()
        assert isinstance(env.possible_starts, dict), "possible_starts must be a dict when not off-policy"
        self.initial_states = env.possible_starts.copy()
        self.initial_state_distrib = [ HashableWrapper(item) for item in env.initial_dist ]
        
        for stt in self.states_list:               
            for act in self.actions_list:
                action = self.actions_dict[act]
                if action.transition is not None:
                    func = action.transition
                else:
                    func = action.func
                    
                for key, val in zip(keys, stt):
                    state[key] = val
                if len(action.data) == 1:
                    results = func(env,state)
                else:
                    results = func(env,state,act.original)
                assert isinstance(results, tuple), "transition returns must be at least state e reward"
                self.add_transition(stt, results, act)    
                
    def add_transition(self, state: HashableWrapper, results: tuple, action: Any) -> None:
        """ Adds a transition to the policy table """
        # print(state, " - ",results, " - ",action)
        action_idx = self.actions_list.index(action)
        new_state: HashableWrapper = HashableWrapper(tuple(results[0].values()))
        reward: float | int = results[1]
        probability: float = 1.0
        terminated: bool = False
        
        for result in results[2:]:
            if isinstance(result, float):
                probability = result
            elif isinstance(result, bool):
                terminated = result
                
        self.P[state][action_idx].append((probability, new_state, reward, terminated))
        
    def _canonical(self, name: str, value: Any) -> float | tuple[float, ...]:
        """ The hashable form of a continuous state: a float for scalar states and a tuple of floats for vectors """
        box = self.continuous_states[name]
        arr = np.asarray(value, dtype=np.float64).reshape(-1)
        if arr.size != box.size:
            raise ValueError(f"Continuous state '{name}' expects {box.size} value(s), got {arr.size}: {value!r}")
        return float(arr[0]) if box.shape == () else tuple(arr.tolist())
    
    @staticmethod
    def _box_value(box: Box, value: Any, clip: bool = False) -> float | np.ndarray:
        """ A continuous value as the Environment sees it: a float for scalar bounds, a np.ndarray otherwise """
        arr = np.asarray(value, dtype=np.float64).reshape(box.shape)
        if clip:
            arr = np.clip(arr, box.low, box.high)
        return float(arr) if box.shape == () else arr
    
    def _state_dict(self, state: HashableWrapper) -> dict[str, Any]:
        """ The state as the `{name: value}` dict that is handed to the transition functions """
        out: dict[str, Any] = {}
        for name, value in zip(self.state_names, state.hashable):
            box = self.continuous_states.get(name)
            out[name] = value if box is None else self._box_value(box, value)
        return out
    
    def _parse_results(self, results: Any, state: HashableWrapper) -> tuple[HashableWrapper, Any, bool]:
        """ Reads the return of a transition function that started in `state`: (next_state: dict, reward, [probability], [terminated]) """
        if not (isinstance(results, tuple) and len(results) >= 2 and isinstance(results[0], dict)):
            raise TypeError(
                f"A transition must return (next_state: dict, reward, [terminated]), got {results!r}"
            )
        new_state = results[0]
        unknown = set(new_state) - set(self.state_names)
        if unknown:
            raise KeyError(f"The transition returned unknown state(s) {sorted(unknown)}, the model has {self.state_names}")
        values = []
        for i, name in enumerate(self.state_names):
            value = new_state[name] if name in new_state else state.hashable[i]
            values.append(self._canonical(name, value) if name in self.continuous_states else value)
        terminated = False
        for result in results[2:]:
            if isinstance(result, (bool, np.bool_)):
                terminated = bool(result)
        return HashableWrapper(tuple(values)), results[1], terminated
    
    def resolve_action(self, action: int | float | np.ndarray) -> tuple['Action', Any, bool]:
        """ Translates the output of `get_action` into what has to be executed
        Parameters
        ----------
        action : int | float | np.ndarray
            An index of `actions_list`, or the real-valued output of a policy learnt with `actor_critic`
        
        Returns
        -------
        tuple[Action, Any, bool]
            The Action, the value to give it and whether it takes a value at all
            (call `action.func(env, agent_name, value)` if so, `action.func(env, agent_name)` otherwise)
        """
        if isinstance(action, (int, np.integer)):
            key = self.actions_list[int(action)]
            act = self.actions_dict[key]
            if act.act_type == "continuous":
                return act, self._box_value(self._action_boxes[id(act)], key.original, clip=True), True
            return act, key.original, len(act.data) != 1
        act, box = self.continuous_actions[0]
        return act, self._box_value(box, action, clip=True), True

    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None) -> tuple[HashableWrapper, dict[str, Any]]:
        """ Reset the model to an initial state """
        if not self.continuous:
            return super().reset(seed=seed, options=options)
        if seed is not None:
            self._np_random, self._np_random_seed = utl_np_random(seed)
        rng = self.np_random
        values: list = []
        for name in self.state_names:
            options_ = self._start_options[name]
            if isinstance(options_, Box):
                value = rng.uniform(options_.low, options_.high) if options_.is_bounded() else options_.sample()
            else:
                value = options_[int(rng.integers(len(options_)))]
            values.append(self._canonical(name, value) if name in self.continuous_states else value)
        self.curr_state = HashableWrapper(tuple(values))
        self.last_action = None
        return self.curr_state, {"prob": 1.0}
    
    def _simulate(self, state: HashableWrapper, action: Any) -> tuple[HashableWrapper, Any, bool]:
        """ Calls the transition function of `action` in `state`, returns (next_state, reward, terminated) """
        act, value, takes_value = self.resolve_action(action)
        func = act.transition if act.transition is not None else act.func
        state_dict = self._state_dict(state)
        results = func(self.env, state_dict, value) if takes_value else func(self.env, state_dict)
        return self._parse_results(results, state)
    
    def step(self, action: Any) -> tuple[HashableWrapper, Any, bool, bool, dict[str, Any]]:
        """ Take a action step in the model """
        if not self.continuous:
            return super().step(action)
        self.curr_state, reward, terminated = self._simulate(self.curr_state, action)
        self.last_action = action
        return self.curr_state, reward, terminated, False, {"prob": 1.0}

    def look(self, action: Any) -> tuple[HashableWrapper, Any, bool, bool, dict[str, Any]]:
        """ Look at a action step in the model, without taking it """
        if not self.continuous:
            return super().look(action)
        next_state, reward, terminated = self._simulate(self.curr_state, action)
        return next_state, reward, terminated, False, {"prob": 1.0}
    
    def state_step(self, state: HashableWrapper, action: Any) -> tuple[HashableWrapper, Any, bool, bool, dict[str, Any]]:
        """ The step that `action` would take from `state`, without changing the current state of the model """
        if not self.continuous:
            return super().state_step(state, action)
        next_state, reward, terminated = self._simulate(self._user_state(state), action)
        return next_state, reward, terminated, False, {"prob": 1.0}
    
    def _user_state(self, state: Any) -> HashableWrapper:
        """ A state given by the user (a dict by name, the tuple that `get_state` returns, or the bare value of a 
        single-state model) as the HashableWrapper that the model works with """
        if isinstance(state, HashableWrapper):
            return state
        names = self.state_names
        if isinstance(state, Mapping):
            missing = [name for name in names if name not in state]
            if missing:
                raise KeyError(f"The state is missing {missing}, the model has {names}")
            values = [state[name] for name in names]
        elif isinstance(state, (tuple, list)) and len(state) == len(names):
            values = list(state)
        elif len(names) == 1:
            values = [state]
        else:
            raise ValueError(f"Expected a state with {len(names)} values {names}, got {state!r}")
        return HashableWrapper(tuple(
            self._canonical(name, value) if name in self.continuous_states else value
            for name, value in zip(names, values)
        ))
    
    def set_state(self, state: Any) -> tuple[HashableWrapper, dict]:
        """ Set the current state """
        if not self.continuous:
            return super().set_state(state)
        self.curr_state = self._user_state(state)
        self.last_action = None
        return self.curr_state, {"prob": 1.0}
    
    def _action_index(self, action: Any) -> int:
        """ The index in `actions_list` of an action given by its value: the discrete action with that exact value 
        or, for the continuous ones, the closest point of their grid """
        if isinstance(action, np.ndarray):
            action = tuple(action.ravel().tolist())
        wrapped = HashableWrapper(action)
        for i, key in enumerate(self.actions_list):
            if self.actions_dict[key].act_type != "continuous" and key == wrapped:
                return i
        try:
            vec = np.asarray(action, dtype=np.float64).reshape(-1)
        except (TypeError, ValueError):
            raise ValueError(f"{action!r} is not an action of {self.name}") from None
        best, best_dist = -1, np.inf
        for i, key in enumerate(self.actions_list):
            act = self.actions_dict[key]
            if act.act_type != "continuous":
                continue
            box = self._action_boxes[id(act)]
            if box.size != vec.size:
                continue
            span = np.where(box.high.ravel() > box.low.ravel(), box.high.ravel() - box.low.ravel(), 1.0)
            dist = float(np.linalg.norm((np.ravel(key.original) - vec) / span))
            if dist < best_dist:
                best, best_dist = i, dist
        if best < 0:
            raise ValueError(f"{action!r} is not an action of {self.name}")
        return best
       
    def _cont_vec(self, values: tuple) -> np.ndarray:
        """ The continuous part of a state as one flat vector """
        return np.concatenate([np.ravel(values[i]) for i in self._cont_idx])
    
    def _features(self, state: HashableWrapper) -> tuple:
        """ The keys of the table entries that represent `state`
        
        Discrete models have one entry per state. With continuous states there is one entry 
        per active tile (the discrete part of the state is kept in the key), and the value of 
        the state is the sum of those entries.
        """
        if self.tile_coder is None:
            return (state,)
        values = state.hashable
        discrete = tuple(values[i] for i in self._disc_idx)
        return tuple((discrete, *tile) for tile in self.tile_coder.tiles(self._cont_vec(values)))
    
    def _terminal_key(self, state: HashableWrapper) -> tuple:
        """ Identifies the region of a state that is checked for termination: continuous states are only known by their small grid cell """
        values = state.hashable
        discrete = tuple(values[i] for i in self._disc_idx)
        if self.tile_coder is None:
            return discrete
        return (discrete, self.tile_coder.cell(self._cont_vec(values)))
    
    def _select_action(self, values: np.ndarray) -> int:
        """ Picks an action index from the values of the actions of a state (see `greedy`) """
        if not self.greedy:
            return int(monte_carlo_selection(values))
        best = np.flatnonzero(values == np.max(values))
        return int(best[0]) if len(best) == 1 else int(best[self.np_random.integers(len(best))])
    
    def _q_values(self, state: HashableWrapper) -> np.ndarray:
        """ The value of every action in `state` """
        keys = self._features(state)
        if len(keys) == 1:
            return self.q_table[keys[0]]
        q = np.zeros(self.num_actions)
        for key in keys:
            q += self.q_table[key]
        return q

    def learn(self, learn_method: Learn_Method, learning_rate: float = 0.05, discount_factor: float = 0.8, epsilon: float = 1, final_epsilon: float = 0.1, max_steps: int | None = None, num_episodes: int = 10000, load_learning: bool = False, learning_rate_policy: float = 0.01) -> None:
        """ The main learning function to update the chosen policy table using the chosen learning method
        
        Parameters
        ----------
        learn_method: Learn_Method
            The learning method to be used in the t
            (`qlearning`, `sarsa` or `actor_critic`)
        learning_rate: float
        
            Step size of the table (or of the critic, in `actor_critic`)
        discount_factor: float
        epsilon: float
            Initial exploration. With `actor_critic` it is the standard deviation of the Gaussian noise 
            added to the policy, relative to half the range of the action
        final_epsilon: float
        max_steps: int | None
            Maximum steps of an episode. Required for continuous tasks that have no terminal state
        num_episodes: int
        load_learning: bool
        learning_rate_policy: float
            Step size of the actor in `actor_critic`
        
        Notes
        -----
        `actor_critic` is for a model whose only Action is a single continuous one. It learns a real-valued
        policy (a linear Gaussian policy over the tile coded state) with a critic estimating the state value; 
        the actor moves its mean towards the actions that turned out better than expected 
        (the CACLA rule, van Hasselt & Wiering, 2007). Use `qlearning` or `sarsa` to learn any other mix of 
        discrete and continuous actions; continuous actions are then quantized according to `action_bins`.
         """
        self.learning_method = learn_method
        self.learning_rate = learning_rate
        self.learning_rate_policy = learning_rate_policy
        self.discount_factor = discount_factor

        self.continuous_policy = learn_method.name == "actor_critic"
        if self.continuous_policy:
            self._setup_continuous_policy()

        self.epsilon = epsilon
        self.epsilon_decay = epsilon / (num_episodes / 2)
        self.final_epsilon = final_epsilon
        
        self.training_error: list = [] 
        self.trend: dict = {'avg': 0, 'slope': 0}
        self.episode_steps: list = []
        if load_learning:
            self.load_learning(f'{self.name}_{learn_method.name}_{learning_rate}_{discount_factor}_{epsilon}_{final_epsilon}_{num_episodes}_{max_steps}.pkl')
        else:
            self.q_table = defaultdict(lambda: np.zeros(self.num_actions))
            self.value_table: dict = defaultdict(lambda: 0.0)
            self.policy_table: dict = defaultdict(lambda: np.full(self.num_actions, 1 / self.num_actions))
            if self.continuous_policy:
                action_size = self._act_box.size
                self.policy_table = defaultdict(lambda: np.zeros(action_size))
            
        self.states_buffer = []
        for i in self.progress_bar(range(1, num_episodes+1), "Training"):
            self.reset()
            done = False
            step = 0
            next_state: HashableWrapper
            while not done and not (max_steps and step >= max_steps):
                action: Any = self.get_action()
                old_state = self.curr_state
                if self.off_policy:
                    action_hashed = self.actions_list[action]
                    act = action_hashed.original
                    curr_stt = self.curr_state.original
                    stt_len = len(curr_stt)
                    try:
                        results = self.actions_dict[action_hashed].transition(self.env, *curr_stt, act)
                    except Exception as e:
                        print('\n',e)
                        print(f'@ Current State: {curr_stt}, Action: {action_hashed}')
                        for buff in self.states_buffer:
                            print(f'\t{buff}')
                        raise
                    #print(" # ",curr_stt," <",stt_len,"> ",results[:stt_len])
                    if stt_len == -1:
                        next_state = self.curr_state = HashableWrapper((results[:stt_len],))
                    else:
                        next_state = self.curr_state = HashableWrapper(results[:stt_len])
                    reward = results[stt_len]
                    probability = 1.0
                    terminated = False
                    
                    for result in results[stt_len+1:]:
                        if isinstance(result, float):
                            probability = result
                        elif isinstance(result, bool):
                            terminated = result
                else:
                    next_state, reward, terminated, truncated, info = self.step(action)
                self.states_buffer.append(f"In State <{old_state}> | Make Action <{action}> | Move to State: {next_state} | Reward {reward} / {terminated}")
                if len(self.states_buffer) > 5:
                    self.states_buffer.pop(0)
                #print(f"In State <{old_state}> | Make Action <{action}> | Move to State: {next_state} | Reward {reward} / {terminated} / {truncated} - {info}")
                #sleep(0.1)
                try:
                    match learn_method.name:
                        case "qlearning":
                            self._q_learning_update(old_state, next_state, action, reward, terminated)
                        case "sarsa":
                            self._sarsa_update(old_state, next_state, action, reward, terminated)
                        case "actor_critic":
                            self._cacla_update(old_state, next_state, action, reward, terminated)
                        case _:
                            print(f"Unsupported learning method {learn_method}")
                except Exception as e:
                    print('\n',e)
                    print(f'# Current State: {curr_stt}, Action: {action_hashed}')
                    for buff in self.states_buffer:
                        print(f'\t{buff}')
                    raise
                if terminated:
                    done = True
                    if self.continuous:
                        self._terminal_cells.add(self._terminal_key(next_state))
                    else:
                        self.terminated_states.append(next_state)
                step += 1
                
            self.episode_steps.append(step)
            if len(self.episode_steps) % 50 == 0:
                window = self.episode_steps[-50:]
                self.trend['avg'] = sum(window) / 50
            #if done and step < max_steps:
            #    print(f" Episode {i} finished in {step} steps : #{self.curr_state}")
                
            self.epsilon = max(self.final_epsilon, self.epsilon - self.epsilon_decay)
        
        self.trained = True
        self.logger.info(f'Training Complete', extra=self.model_info)
        print(f"Training Complete")
        #self.reset_percepts()
        #self.save_learning(f"{self.name}_{learn_method.name}_{learning_rate}_{discount_factor}_{epsilon}_{final_epsilon}_{num_episodes}_{max_steps}.pkl")

    def save_learning(self, filename: str) -> None:
        """ Save the current policy table to a pickle file """
        with open(filename, 'wb') as file:
            if self.continuous_policy:
                pickle.dump({"__actor_critic__": {"value": dict(self.value_table), "policy": dict(self.policy_table)}}, file)
            else:
                pickle.dump(dict(self.q_table), file)
    
    def load_learning(self, filename: str | None = None) -> None:
        """ Load the policy table from a pickle file """
        if filename is None:
            filename = "q_table.pkl"
        print("Loading Model...",end=" ",flush=True)
        with open(filename, 'rb') as file:
            loaded_q_table = pickle.load(file)
        if isinstance(loaded_q_table, dict) and "__actor_critic__" in loaded_q_table:
            if not self.continuous_policy:
                raise ValueError(f"{filename} holds an actor_critic policy, it can only be loaded when learning with actor_critic")
            action_size = self._act_box.size
            self.value_table = defaultdict(lambda: 0.0, loaded_q_table["__actor_critic__"]["value"])
            self.policy_table = defaultdict(lambda: np.zeros(action_size), loaded_q_table["__actor_critic__"]["policy"])
        else:
            self.q_table = defaultdict(lambda: np.zeros(self.num_actions), loaded_q_table)
        print("Model Loaded!")
    
    def progress_bar(self, iterable, prefix='', length=50):
        total = len(iterable)
        for i, item in enumerate(iterable):
            percent = (i + 1) / total
            filled = int(length * percent)
            bar = '█' * filled + '-' * (length - filled)
            sys.stdout.write(f'\r{prefix}: {i+1}/{total} avg_steps({self.trend["avg"]:.2f}) |{bar}| {percent:.0%}') if self.show_learning else ...
            sys.stdout.flush() if self.show_learning else ...
            yield item
        print() if self.show_learning else ...
    
    def update_learning(self, action: Any, state: Any, next_state: Any, reward: float | None = None, terminated: bool | None = None) -> None:
        """ Learn from one step that was actually taken, using the learning method that the model was trained with
        
        Parameters
        ----------
        action : Any
            The argument that the action was executed with. In a model with continuous actions it is the value that was
            given to the action: the discrete action with exactly that value, or else the closest point of the grid
            of a continuous one (for `qlearning` and `sarsa`), or the value itself (for `actor_critic`)
        state : Any
            The state where the action was taken. With continuous states: a dict by name, the tuple that `get_state`
            returns, or the bare value if the model has a single state
        next_state : Any
            The state that was reached, in the same format
        reward : float, optional
            The reward that was received. By default it is evaluated by calling the transition function in `state`
        terminated : bool, optional
            If the step ended the episode. By default it is evaluated by calling the transition function in `state`
        """
        if getattr(self, "learning_method", None) is None:
            raise RuntimeError("update_learning needs a model that has been trained with learn()")
        step_reward: Any
        step_terminated: bool
        if self.continuous:
            state = self._user_state(state)
            next_state = self._user_state(next_state)
            if self.continuous_policy:
                executed: Any = self._box_value(self._act_box, action, clip=True)
            else:
                executed = self._action_index(action)
            if reward is None or terminated is None:
                simulated = self._simulate(state, executed)
                step_reward = simulated[1] if reward is None else reward
                step_terminated = simulated[2] if terminated is None else terminated
            else:
                step_reward, step_terminated = reward, terminated
            match self.learning_method.name:
                case "qlearning":
                    self._q_learning_update(state, next_state, executed, step_reward, step_terminated)
                case "sarsa":
                    self._sarsa_update(state, next_state, executed, step_reward, step_terminated)
                case "actor_critic":
                    self._cacla_update(state, next_state, executed, step_reward, step_terminated)
            return
        state = HashableWrapper((state,))
        next_state = HashableWrapper((next_state,))
        action = HashableWrapper(action)
        action_idx = self.actions_list.index(action)
        if self.off_policy:
            act = action.original
            curr_stt = state.original
            stt_len = len(curr_stt)
            print(f'In State <{curr_stt}> | Make Action <{act}>')
            results = self.actions_dict[action].transition(self.env, *curr_stt, act)
            if stt_len == -1:
                n_state = HashableWrapper((results[:stt_len],))
            else:
                n_state = HashableWrapper(results[:stt_len])
            step_reward = results[stt_len]
            step_terminated = False
        else:
            n_state, step_reward, step_terminated, _truncated, _info = self.state_step(state, action_idx)
        if n_state != next_state:
            print(f"Update Error: {n_state} != {next_state}")
        if reward is not None:
            step_reward = reward
        if terminated is not None:
            step_terminated = terminated
        match self.learning_method.name:
            case "qlearning":
                self._q_learning_update(state, next_state, action_idx, step_reward, step_terminated)
            case "sarsa":
                self._sarsa_update(state, next_state, action_idx, step_reward, step_terminated)
    
    def update_qtable(self, other_qtable):
        self.q_table = (1-self.learning_rate)*self.q_table + (self.learning_rate)*other_qtable
    
    def _q_learning_update(self, state: HashableWrapper, next_state: HashableWrapper, action: int, reward: float, terminated: bool) -> None:
        """ Update the Q-table using the Q-learning algorithm
        
        Parameters
        ----------
        state : HashableWrapper
            The current state of the environment
        next_state : HashableWrapper
            The next state of the environment
        action : int
            The action taken in the current state
        reward : float
            The reward received for taking the action in the current state
        """
        keys = self._features(state)
        q_table = (not terminated) * np.max(self._q_values(next_state))
        
        temp_diff = (
            reward + self.discount_factor * q_table - sum(self.q_table[key][action] for key in keys)
        )
        
        for key in keys:
            self.q_table[key][action] += self.learning_rate / len(keys) * temp_diff 
        
        self.training_error.append(temp_diff)
    
    def _sarsa_update(self, state: HashableWrapper, next_state: HashableWrapper, action: int, reward: float, terminated: bool) -> None:
        """ Update the Q-table using the SARSA algorithm """
        next_action = cast(int, self.get_action(next_state))
        
        keys = self._features(state)
        next_q = (not terminated) * self._q_values(next_state)[next_action]
        
        temp_diff = (
            reward + self.discount_factor * next_q - sum(self.q_table[key][action] for key in keys)
        )
        
        for key in keys:
            self.q_table[key][action] += self.learning_rate / len(keys) * temp_diff
        
        self.training_error.append(temp_diff)

    def _expected_sarsa_update(self, state: HashableWrapper, next_state: HashableWrapper, action: int, reward: float, terminated: bool, policy) -> None:
        """ Update the Q-table using the Expected SARSA algorithm """
        if not terminated:
            expected_q = np.dot(policy[next_state], self.q_table[next_state])
        else:
            expected_q = 0
        
        temp_diff = (
            reward + self.discount_factor * expected_q - self.q_table[state][action]
        )
        
        self.q_table[state][action] += self.learning_rate * temp_diff
        
        self.training_error.append(temp_diff)

        
    def _actor_critic_update(self, state: HashableWrapper, next_state: HashableWrapper, action: int, reward: float, terminated: bool) -> None:
        """ Update the Q-table using the Actor-Critic algorithm """
        current_value = self.value_table[state]
        next_value = (not terminated) * self.value_table[next_state]

        td_error = reward + self.discount_factor * next_value - current_value
        
        self.value_table[state] += self.learning_rate * td_error

        self.policy_table[state][action] += self.learning_rate_policy * td_error

        self.policy_table[state] = self.policy_table[state] / np.sum(self.policy_table[state])
        
        self.training_error.append(td_error)

    def _setup_continuous_policy(self) -> None:
        """ Checks that the model can be learnt with a continuous policy and caches the scale of its action """
        if self._n_discrete_actions or len(self.continuous_actions) != 1:
            raise ValueError(
                f"actor_critic needs a model whose only Action is a single continuous one, "
                f"but {self.name} has {self._n_discrete_actions} discrete action(s) and {len(self.continuous_actions)} continuous one(s). "
                f"Use qlearning or sarsa instead, they quantize continuous actions"
            )
        self._act_box: Box = self.continuous_actions[0][1]
        low, high = self._act_box.low.ravel(), self._act_box.high.ravel()
        self._act_center = (low + high) / 2
        self._act_half = (high - low) / 2
    
    def _policy_mean(self, state: HashableWrapper) -> np.ndarray:
        """ The mean of the Gaussian policy in `state`, with the range of the action scaled to [-1, 1] """
        mean = np.zeros(self._act_box.size)
        for key in self._features(state):
            mean += self.policy_table[key]
        return mean
    
    def _policy_action(self, state: HashableWrapper, noise: float = 0.0) -> float | np.ndarray:
        """ The action of the policy in `state`, with optional Gaussian exploration noise """
        unit = self._policy_mean(state)
        if noise > 0:
            unit = unit + noise * self.np_random.standard_normal(unit.shape)
        return self._box_value(self._act_box, self._act_center + self._act_half * np.clip(unit, -1.0, 1.0), clip=True)
    
    def _cacla_update(self, state: HashableWrapper, next_state: HashableWrapper, action: Any, reward: float, terminated: bool) -> None:
        """ Update the critic with TD(0) and the actor with the CACLA rule
        
        The critic estimates the value of the (tile coded) state. When the TD error is positive, the action 
        taken was better than expected and the mean of the policy is moved towards it.
        """
        keys = self._features(state)
        step = 1 / len(keys)
        value = sum(self.value_table[key] for key in keys)
        next_value = 0.0 if terminated else sum(self.value_table[key] for key in self._features(next_state))
        td_error = reward + self.discount_factor * next_value - value
        
        for key in keys:
            self.value_table[key] += self.learning_rate * step * td_error
        
        if td_error > 0:
            half = np.where(self._act_half > 0, self._act_half, 1.0)
            taken = (np.asarray(action, dtype=np.float64).reshape(-1) - self._act_center) / half
            delta = taken - self._policy_mean(state)
            for key in keys:
                self.policy_table[key] += self.learning_rate_policy * step * delta
        
        self.training_error.append(td_error)
        
    def get_action(self, state: tuple | HashableWrapper | None = None) -> int | float | np.ndarray:
        """ Get the action to take in the current state 
        
        Returns an index of `actions_list`, or, for a policy learnt with `actor_critic`, the value of the 
        continuous action (use `resolve_action` to translate either into something that can be executed).
        Without a `state` it explores (while learning), with a `state` it exploits.
        """
        if state is not None:
            stt: tuple = tuple()
            for curr_s, s in zip(self.curr_state.original, state):
                if s is Any:
                    stt += (curr_s,)
                else:
                    stt += (s,)
            if self.continuous:
                stt = tuple(
                    self._canonical(name, s) if name in self.continuous_states else s 
                    for name, s in zip(self.state_names, stt)
                )
            state = stt    
            #if not isinstance(state, HashableWrapper):
            state = HashableWrapper(state)
            if self.continuous_policy:
                return self._policy_action(state)
            action = self._select_action(self._q_values(state))
            #print(f'state: {state} : {self.q_table[state]} > [{action}] {self.actions_list[action]}')
            return action
            #return int(np.argmax(self.q_table[state]))
        
        if self.continuous_policy:
            return self._policy_action(self.curr_state, noise=self.epsilon)
        
        if np.random.uniform(0, 1) < self.epsilon:
            return self.action_space.sample()
        
        return self._select_action(self._q_values(self.curr_state))
        #return monte_carlo_selection(self.q_table[self.curr_state])
        #return int(np.argmax(self.q_table[self.curr_state]))

    def get_state(self) -> tuple: 
        """" Get the current state of the model """
        from maspy.environment import Percept
        state: tuple = tuple()
        for name in self.initial_states.keys():
            percept = self.env.get(Percept(name),ck_values=False)
            assert isinstance(percept, Percept)
            #print(f'name: {name} _values: {percept._values}') 
            if not isinstance(percept._values, tuple):
                state += (percept._values,)
            else:
                state += (percept.values,)
        if self.continuous:
            state = tuple(
                self._canonical(name, value) if name in self.continuous_states else value 
                for name, value in zip(self.state_names, state)
            )
            wrapped = HashableWrapper(state)
            if self.terminal is not None:
                return state, bool(self.terminal(self._state_dict(wrapped)))
            return state, self._terminal_key(wrapped) in self._terminal_cells
        if state in self.terminated_states or HashableWrapper(state) in self.terminated_states:
            return state, True
        else:
            return state, False