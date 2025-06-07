from typing import TYPE_CHECKING, Any, Sequence
from collections import defaultdict
from maspy.learning.core import Model, HashableWrapper
from maspy.learning.space import Discrete
from maspy.learning.ml_utils import monte_carlo_selection
from enum import Enum
from itertools import product, combinations, permutations
import numpy as np
import pickle
import sys

if TYPE_CHECKING:
    from maspy.environment import Environment, Action

Learn_Method = Enum('qlearning | sarsa', ['qlearning', 'sarsa']) # type: ignore[misc]

qlearning = Learn_Method.qlearning
sarsa = Learn_Method.sarsa

Group = Enum('sequence | combination | permutation | cartesian | listed', ['sequence', 'combination', 'permutation', 'cartesian', 'listed']) # type: ignore[misc]

sequence = Group.sequence
combination = Group.combination
permutation = Group.permutation
cartesian = Group.cartesian
listed = Group.listed

class EnvModel(Model):
    def __init__(self, env: 'Environment') -> None:
        super().__init__()
        print(f'Creating model for {env.my_name}')
        self.name = env.my_name
        self.env = env
        states = env._states.copy()
        actions = env._actions.copy()
        from maspy.environment import Action
        self.actions_list: list[HashableWrapper] = []
        self.actions_dict: dict[HashableWrapper, Action] = {}
        self.orginize_actions(actions)
        self.off_policy = False
  
        value_lists: list = list(states.values())
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
        
        self.num_actions = len(self.actions_list)
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
        
        self.curr_state = self.initial_state_distrib[np.random.randint(0, len(self.initial_state_distrib))]     
        self.action_space = Discrete(len(self.actions_list))
        self.observation_space = Discrete(len(self.states_list))
        
        from maspy.admin import Admin
        Admin()._add_model(self)
        
    
    def reset_percepts(self):
        self.reset()
        from maspy.environment import Percept
        for stt, (name, _) in zip(self.curr_state, self.initial_states.items()):
            percept = self.env.get(Percept(name),ck_args=False)
            if isinstance(stt, frozenset):
                stt = dict(stt)
            self.env.change(percept, stt)
    
    def orginize_actions(self, actions: list['Action']):
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
            else:
                print(f"Unsupported action type: {action.act_type}")
    
    def make_policy_table(self, env: 'Environment', states: dict[str, list]):
        state: dict = {}
        keys = states.keys()
        assert isinstance(env.possible_starts, dict), "possible_starts must be a dict when not off-policy"
        start_list = list(env.possible_starts.values())
        for percept in env._state_percepts.values():
            if percept.key not in env.possible_starts:
                start_list.append(env._states[percept.key])
                env.possible_starts[percept.key] = env._states[percept.key]
        normalized = [ 
            [item] if not isinstance(item, list | tuple | set) 
            else list(item) for item in start_list
        ]
        
        self.initial_states = env.possible_starts.copy()
        aux_dist = list(product(*normalized))
        self.initial_state_distrib = [ HashableWrapper(item) for item in aux_dist ]
        
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
                
    def add_transition(self, state: HashableWrapper, results: tuple, action: Any):
        #print(state, " - ",results, " - ",action)
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
        
    def learn(self, learn_method: Learn_Method, learning_rate: float = 0.05, discount_factor: float = 0.8, epsilon: float = 1, final_epsilon: float = 0.1, max_steps: int | None = None, num_episodes: int = 10000, load_learning: bool = False):   
        
        self.learning_rate = learning_rate
        self.learning_rate_policy = 0.01
        self.discount_factor = discount_factor
        
        self.epsilon = epsilon
        self.epsilon_decay = epsilon / (num_episodes / 2)
        self.final_epsilon = final_epsilon
        
        self.training_error: list = [] 
        self.trend: dict = {'avg': 0, 'slope': 0}
        self.episode_steps: list = []
        
        if load_learning:
            self.load_learning(f'{self.name}_{learn_method.name}_{learning_rate}_{discount_factor}_{epsilon}_{final_epsilon}_{num_episodes}_{max_steps}.pkl')
        else:
            self.q_table: dict = defaultdict(lambda: np.zeros(self.num_actions))
            self.value_table: dict = defaultdict(lambda: 0.0)
            self.policy_table: dict = defaultdict(lambda: np.full(self.num_actions, 1 / self.num_actions))
            
        self.states_buffer = []
        self.reset_percepts()
        for i in self.progress_bar(range(1, num_episodes+1), "Training"):
            self.reset()
            done = False
            step = 0
            next_state: HashableWrapper
            while not done and not (max_steps and step >= max_steps):
                action = self.get_action()
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
                            self.q_learning_update(old_state, next_state, action, reward, terminated)
                        case "sarsa":
                            self.sarsa_update(old_state, next_state, action, reward, terminated)
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
                    self.terminated_states.append(next_state)
                step += 1
                
            self.episode_steps.append(step)
            if len(self.episode_steps) % 50 == 0:
                window = self.episode_steps[-50:]
                self.trend['avg'] = sum(window) / 50
            #if done and step < max_steps:
            #    print(f" Episode {i} finished in {step} steps : #{self.curr_state}")
                
            self.epsilon = max(self.final_epsilon, self.epsilon - self.epsilon_decay)
        
        self.save_learning(f"{self.name}_{learn_method.name}_{learning_rate}_{discount_factor}_{epsilon}_{final_epsilon}_{num_episodes}_{max_steps}.pkl")

    def save_learning(self, filename: str):
        with open(filename, 'wb') as file:
            pickle.dump(dict(self.q_table), file)
    
    def load_learning(self, filename: str | None = None):
        if filename is None:
            filename = "q_table.pkl"
        print("Loading Model...",end=" ",flush=True)
        with open(filename, 'rb') as file:
            loaded_q_table = pickle.load(file)
        self.q_table = defaultdict(lambda: np.zeros(self.num_actions), loaded_q_table)
        print("Model Loaded!")
    
    def progress_bar(self, iterable, prefix='', length=50):
        total = len(iterable)
        for i, item in enumerate(iterable):
            percent = (i + 1) / total
            filled = int(length * percent)
            bar = '█' * filled + '-' * (length - filled)
            sys.stdout.write(f'\r{prefix}: {i+1}/{total} avg_steps({self.trend["avg"]:.2f}) |{bar}| {percent:.0%}')
            sys.stdout.flush()
            yield item
        print() 
    
    def q_learning_update(self, state, next_state, action: int, reward, terminated):
        q_table = (not terminated) * np.max(self.q_table[next_state])
        
        temp_diff = (
            reward + self.discount_factor * q_table - self.q_table[state][action]
        )
        
        self.q_table[state][action] += self.learning_rate * temp_diff
        
        self.training_error.append(temp_diff)
    
    def sarsa_update(self, state, next_state, action: int, reward, terminated):
        next_action = self.get_action(next_state)
        
        next_q = (not terminated) * self.q_table[next_state][next_action]
        
        temp_diff = (
            reward + self.discount_factor * next_q - self.q_table[state][action]
        )
        
        self.q_table[state][action] += self.learning_rate * temp_diff
        
        self.training_error.append(temp_diff)

    def expected_sarsa_update(self, state, next_state, action: int, reward, terminated, policy):
        if not terminated:
            expected_q = np.dot(policy[next_state], self.q_table[next_state])
        else:
            expected_q = 0
        
        temp_diff = (
            reward + self.discount_factor * expected_q - self.q_table[state][action]
        )
        
        self.q_table[state][action] += self.learning_rate * temp_diff
        
        self.training_error.append(temp_diff)

        
    def actor_critic_update(self, state, next_state, action: int, reward, terminated):
        current_value = self.value_table[state]
        next_value = (not terminated) * self.value_table[next_state]

        td_error = reward + self.discount_factor * next_value - current_value
        
        self.value_table[state] += self.learning_rate * td_error

        self.policy_table[state][action] += self.learning_rate_policy * td_error

        self.policy_table[state] = self.policy_table[state] / np.sum(self.policy_table[state])
        
        self.training_error.append(td_error)

        
    def get_action(self, state: tuple | HashableWrapper | None = None):
        if state is not None:
            stt: tuple = tuple()
            for curr_s, s in zip(self.curr_state.original, state):
                if s == Any:
                    stt += (curr_s,)
                else:
                    stt += (s,)
            state = stt    
            #if not isinstance(state, HashableWrapper):
            state = HashableWrapper(state)
            action = monte_carlo_selection(self.q_table[state])
            #print(f'state: {state} : {self.q_table[state]} > [{action}] {self.actions_list[action]}')
            return action
            #return int(np.argmax(self.q_table[state]))
        
        if np.random.uniform(0, 1) < self.epsilon:
            return self.action_space.sample()
        
        return monte_carlo_selection(self.q_table[self.curr_state])
        #return int(np.argmax(self.q_table[self.curr_state]))

    def get_state(self) -> tuple: 
        from maspy.environment import Percept
        state: tuple = tuple()
        for name in self.initial_states.keys():
            percept = self.env.get(Percept(name),ck_args=False)
            assert isinstance(percept, Percept)
            state += (percept.args,)
        if state in self.terminated_states or HashableWrapper(state) in self.terminated_states:
            return state, True
        else:
            return state, False