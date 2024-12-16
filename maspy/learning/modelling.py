from typing import TYPE_CHECKING, Any
from collections import defaultdict
from maspy.learning.core import Model
from maspy.learning.space import Discrete
from maspy.learning.ml_utils import monte_carlo_selection
from enum import Enum
from itertools import product, combinations, permutations
import numpy as np

if TYPE_CHECKING:
    from maspy.environment import Environment

Learn_Method = Enum('qlearning | sarsa', ['qlearning', 'sarsa']) # type: ignore[misc]

qlearning = Learn_Method.qlearning
sarsa = Learn_Method.sarsa

Group = Enum('sequence | combination | permutation | cartesian | listed | single', ['sequence', 'combination', 'permutation', 'cartesian', 'listed' , 'single']) # type: ignore[misc]

sequence = Group.sequence
combination = Group.combination
permutation = Group.permutation
cartesian = Group.cartesian
listed = Group.listed
single = Group.single

class EnvModel(Model):
    def __init__(self, env: 'Environment') -> None:
        super().__init__()
        self.name = env.my_name
        self.env = env
        states = env._states.copy()
        actions = env._actions.copy()
        from maspy.environment import Action
        self.actions_list: list[str] = []
        self.actions_dict: dict[str, Action] = {}
        for action in actions:
            if isinstance(action.data,str):
                self.actions_list.append(action.data)
                self.actions_dict[action.data] = action
                continue
            for arg in action.data:
                self.actions_list.append(arg)
                self.actions_dict[arg] = action
        state: dict = {}
        keys = states.keys()
        value_lists = states.values()
        self.states_list = list(product(*value_lists))
        self.terminated_states: list[tuple] = []
        
        start_list = list(env.possible_starts.values())
        for percept in env._state_percepts.values():
            if percept.key not in env.possible_starts:
                start_list.append(env._states[percept.key])
        normalized = [ 
            [item] if not isinstance(item, (list, tuple, set, str)) 
            else list(item) for item in start_list
        ]
        self.initial_state_distrib = list(product(*normalized))
            
        print(self.actions_list)
        self.num_actions = len(self.actions_list)
        self.P = {
            state: {action: [] for action in range(self.num_actions)}
            for state in self.states_list
        }
        
        for stt in self.states_list:
            for action in actions:
                if action.transition is not None:
                    func = action.transition
                else:
                    func = action.func
                if action.act_type == 'listed':
                    for args in action.data:
                        for key, val in zip(keys, stt):
                            state[key] = val
                        if len(action.data) == 1:
                            results = func(env,state)
                        else:
                            results = func(env,state,args)
                        assert isinstance(results, tuple), "transition returns must be at least state e reward"
                        self.add_transition(stt, results, args)
                        
                elif action.act_type == 'single':
                    for key, val in zip(keys, stt):
                        state[key] = val
                    results = func(env,state)
                    assert isinstance(results, tuple)
                    self.add_transition(stt, results, action.data)
                    
                elif action.act_type == 'combination':
                    act_comb: list = []
                    for i in range(1, len(action.data) + 1):
                        act_comb.extend(combinations(action.data, i))
                    for act in act_comb:
                        for key, val in zip(keys, stt):
                            state[key] = val
                        results = func(env,state,act)
                        assert isinstance(results, tuple)
                        self.add_transition(stt, results, act)
                else:
                    print(f"Unsupported action type: {action.act_type}")
        
        self.curr_state = self.initial_state_distrib[np.random.randint(0, len(self.initial_state_distrib))]           
        self.action_space = Discrete(len(self.actions_list))
        self.observation_space = Discrete(len(self.states_list))
        
        from maspy.admin import Admin
        Admin()._add_model(self)
        
    
    def reset_percepts(self):
        self.reset()
        from maspy.environment import Percept
        for stt, (name, values) in zip(self.curr_state, self.env.possible_starts.items()):
            percept = self.env.get(Percept(name),ck_args=False)
            self.env.change(percept, stt)
            
    def add_transition(self, state, results: tuple, action: Any):
        action_idx = self.actions_list.index(action)
        new_state: tuple = tuple(results[0].values())
        reward: float | int = results[1]
        probability: float = 1.0
        terminated: bool = False
        
        for result in results[2:]:
            if isinstance(result, float):
                probability = result
            elif isinstance(result, bool):
                terminated = result
                
        self.P[state][action_idx].append((probability, new_state, reward, terminated))
        
    def learn(self, learn_method: Learn_Method, learning_rate: float = 0.05, discount_factor: float = 0.8, epsilon: float = 1, final_epsilon: float = 0.1, num_steps: int = 50, num_episodes: int = 10000):
        self.learning_rate = learning_rate
        self.learning_rate_policy = 0.01
        self.discount_factor = discount_factor
        
        self.epsilon = epsilon
        self.epsilon_decay = epsilon / (num_episodes / 2)
        self.final_epsilon = final_epsilon
        
        self.training_error: list = [] 
        
        self.q_table: dict = defaultdict(lambda: np.zeros(self.num_actions))
        self.value_table: dict = defaultdict(lambda: 0.0)
        self.policy_table: dict = defaultdict(lambda: np.full(self.num_actions, 1 / self.num_actions))
        
        for _ in range(num_episodes):
            self.reset()
            done = False
            step = 0
            while not done:
                action = self.get_action()
                old_state = self.curr_state
                next_state, reward, terminated, truncated, info = self.step(action)
                match learn_method.name:
                    case "qlearning":
                        self.q_learning_update(old_state, next_state, action, reward, terminated)
                    case "sarsa":
                        self.sarsa_update(old_state, next_state, action, reward, terminated)
                    case _:
                        print(f"Unsupported learning method {learn_method}")
                if terminated:
                    done = True
                    self.terminated_states.append(next_state)
                step += 1
            #if step < 50:
            #     print("terminated in ", step, "steps")
            #print(self.training_error[-1])
            self.epsilon = max(self.final_epsilon, self.epsilon - self.epsilon_decay)
        
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

        
    def get_action(self, state: tuple | None = None):
        if state is not None:
            #return monte_carlo_selection(self.q_table[state])
            return int(np.argmax(self.q_table[state]))
        
        if np.random.uniform(0, 1) < self.epsilon:
            return self.action_space.sample()
        
        #return monte_carlo_selection(self.q_table[self.curr_state])
        return int(np.argmax(self.q_table[self.curr_state]))

    def get_state(self):
        from maspy.environment import Percept
        state = ()
        for name in self.env.possible_starts.keys():
            percept = self.env.get(Percept(name),ck_args=False)
            state += (percept.args,)
        return state