from typing import( Generic, Optional, Sequence, Tuple, Type, TypeVar, Union )
from contextlib import closing
from time import sleep
from io import StringIO
from os import system
import numpy as np
import sys
import matplotlib.pyplot as plt

ObsType = TypeVar("ObsType")
ActType = TypeVar("ActType")
T_cov = TypeVar("T_cov", covariant=True)

class learning_model(object):
    def __init__(self, map = None):
        if map is None: # default 4x4 map
            map = [[-2, 0, 0,-2],
                   [-1, 0, 0, 0],
                   [ 0,-2,-1,-1],
                   [ 0, 0, 0,-2]]
            
        self.desc = np.asarray(map, dtype=int)
        self.ori_desc = np.asarray(map, dtype=int).copy()
        
        locs = np.where(self.desc == -2)
        self.locs = [ (x,y) for x,y in zip(locs[0],locs[1]) ] 
        self.comb = 2**len(self.locs)

        self.num_rows, self.num_cols = self.desc.shape    
        self.num_states = self.num_rows * self.num_cols
        self.initial_state_distrib = np.zeros(self.num_states)
        self.max_row = self.num_rows - 1
        self.max_col = self.num_cols - 1
        self.num_actions = 4 # down, up, right, left
        
        self.P = {
            state: {action: [] for action in range(self.num_actions)}
            for state in range(self.num_states)
        }
        
        arrive_reward = 10
        for row in range(self.num_rows):
            for col in range(self.num_cols):
                state = self.encode(row, col)
                if self.desc[row,col] == 0:   # Estados iniciais devem estar fora de sujeira e obstaculos
                    self.initial_state_distrib[state] += 1
                for action in range(self.num_actions):
                    new_row, new_col, = row, col
                    reward = 0 # Recompensa para movimentar normalmente
                    if action == 0 and row < self.max_row and self.desc[row+1, col] != -1 : #  Movimenta p/ Baixo
                        new_row = min(row+1,self.max_row)
                        if self.desc[new_row,col] == -2:    # Recompensa quando alcança posicao alvo
                            reward = arrive_reward
                    elif action == 1 and row > 0 and self.desc[row-1, col] != -1: # Movimenta p/ Cima
                        new_row = max(row-1, 0)
                        if self.desc[new_row,col] == -2:    # Recompensa quando alcança posicao alvo
                            reward = arrive_reward
                    elif action == 2 and col < self.max_col and self.desc[row, col+1] != -1: # Movimenta p/ Direita
                        new_col = min(col+1,self.max_col)
                        if self.desc[row,new_col] == -2:    # Recompensa quando alcança posicao alvo
                            reward = arrive_reward
                    elif action == 3 and col > 0 and self.desc[row, col-1] != -1: # Movimenta p/ Esquerda
                        new_col = max(col-1,0) 
                        if self.desc[row,new_col] == -2:    # Recompensa quando alcança posicao alvo
                            reward = arrive_reward
                    
                    new_state = self.encode(new_row,new_col) # Novo estado apos acao
                    self.P[state][action].append( (1.0, new_state, reward) )

        self.initial_state_distrib /= self.initial_state_distrib.sum()
        self.action_space = Discrete(self.num_actions)
        self.observation_space = Discrete(self.num_states)

    # Recuperar Estado Atual de Acordo com Observacao
    def encode(self, row, col):
        return  row * self.num_cols + col

    # Recuperar Observacao de Acordo com Estado Atual
    def decode(self, i):
        out = []
        out.append(i % self.num_rows)
        i = i // self.num_rows
        out.append(i)
        return reversed(out)

    # Mascara de Possiveis Acoes
    def action_mask(self, state: int):
        mask = np.zeros(self.num_actions, dtype=np.int8)
        row, col = self.decode(state)
        if row < self.max_row and self.desc[row+1, col] != -1: 
            mask[0] = 1
        if row > 0 and self.desc[row-1, col] != -1:
            mask[1] = 1
        if col < self.max_col and self.desc[row, col+1] != -1: 
            mask[2] = 1
        if col > 0 and self.desc[row, col-1] != -1:
            mask[3] = 1
        return mask

    # Retorna o resultado de uma determinada Acao 
    def look(self, a: ActType) -> Tuple[ObsType, float, bool, dict]:
        transitions = self.P[self.s][a]
        if len(transitions) > 1:
            i = self.categorical_sample([t[0] for t in transitions])
            p, s, r = transitions[i]
        else:
            p, s, r = transitions[0]

        return (int(s), r, {"prob": p, "action_mask": self.action_mask(s)})

    # Realiza uma Acao no Estado Atual
    
    def step(self, a: ActType) -> Tuple[ObsType, float, bool, dict]:
        transitions = self.P[self.s][a]
    
        if len(transitions) > 1:
            i = self.categorical_sample([t[0] for t in transitions])
            p, s, r = transitions[i]
        else:
            p, s, r = transitions[0]

        row,col = self.decode(s)
        if self.desc[row][col] == -2:
            self.desc[row][col] = 0
        elif self.desc[row][col] == 0 and r > 0:
            r = 0
            
        self.s = s
        self.last_action = a
        return (int(s), r, {"prob": p, "action_mask": self.action_mask(s)})

    # Transforma o caminho de Estados em sequencia de Acoes
    def states_to_actions(self, path):
        path_actions = []
        x, y = self.decode(self.s)
        for state in path:
            row, col = self.decode(state)
            dif = np.subtract((x,y),(row,col))
            if dif[0] != 0:
                if dif[0] < 0:
                    path_actions.append(0) # Baixo
                else:
                    path_actions.append(1) # Cima
            elif dif[1] != 0:
                if dif[1] < 0:
                    path_actions.append(2) # Direita
                else:
                    path_actions.append(3) # Esquerda
            else:
                return None                # Error
            x = row
            y = col
        #print(f'{self.s} {path} -> {path_actions}')
        return path_actions

    def actions_to_states(self,actions):
        states = []
        for action,value in enumerate(actions):
            if value == 1:
                s, _, _, = self.look(action)
                states.append(s)
        return states
    
    # Retorna possiveis Estados vizinhos e as melhores Acoes
    def sensor(self):
        best_actions = np.zeros((self.num_actions),dtype=int)
        possible_states = []
        row,col = self.decode(self.s)
        mask = self.action_mask(self.s)
        for i in range(max(row-1,0),min(row+1,self.max_row)+1):
            for j in range(max(col-1,0),min(col+1,self.max_col)+1):
                if self.desc[i,j] >= 0 and np.abs((row+col)-(i+j)) == 1:
                    possible_states.append(self.encode(i,j))
                
                if self.desc[i,j] == -2:
                    if i > row and mask[0] == 1:
                        best_actions[0] += 1
                    elif i < row and mask[1] == 1:
                        best_actions[1] += 1
                    if j > col and mask[2] == 1:
                        best_actions[2] += 1
                    elif j < col and mask[3] == 1:
                        best_actions[3] += 1
        return possible_states, best_actions
                
    # Resetar Estado para um Possivel Incial
    def reset(self, *, seed: Optional[int] = None, options: Optional[dict] = None) -> Tuple[ObsType, dict]: 
        self.s = self.categorical_sample(self.initial_state_distrib)
        self.desc = self.ori_desc.copy()
        self.last_action = None
        
        return int(self.s), {"prob": 1.0, "action_mask": self.action_mask(self.s)}

    # Coloca o sistema em um Estado especifico
    def set_state(self, state) -> Tuple[ObsType, dict]: 
        self.s = state
        self.last_action = None
        
        return int(self.s), {"prob": 1.0, "action_mask": self.action_mask(self.s)}

    # Imprimir na tela uma representacao do cenario no estado atual
    def render(self, adj_matrix=None):
        desc = self.desc.copy().tolist()
        outfile = StringIO()

        row, col = self.decode(self.s)
    
        # Representacao do aspirador no cenario 
        desc[row][col] = 1

        end = out = '+'+ ''.join(['-' for x in range(2*len(desc)-1)]) + '+\n'
        for k,line in enumerate(desc):
            out += '|'
            for i,x in enumerate(line):
                if x == -2:
                    out += '#'
                if x == -1:
                    out += '■'
                if x == 1:
                    out += 'O'
                if x == 0:
                    state = self.encode(k,i)
                    if len(adj_matrix) > 0 and adj_matrix[state,state] > 0:
                        if adj_matrix[state,state] == 1:
                            out += '*'
                        elif adj_matrix[state,state] == 2:
                            out += '~'
                        elif adj_matrix[state,state] == 3:
                            out += 'X'
                        else:
                            out += 'ADJ_ERROR'
                    else:
                        out += ' '
                if i < len(line)-1:
                    out += ':'
            out += '|\n'
        out += end

        outfile.write(out)
        if self.last_action is not None:
            outfile.write(f"({['Baixo','Cima','Direita','Esquerda'][self.last_action]})\n")
        else:
            outfile.write("\n")

        with closing(outfile):
            return outfile.getvalue()

    def categorical_sample(self, prob_n):
        np_rand = np.random.default_rng()
        prob_n = np.asarray(prob_n)
        csprob_n = np.cumsum(prob_n)
        return np.argmax(csprob_n > np_rand.random())

class Space(Generic[T_cov]):
    def __init__(self, shape: Optional[Sequence[int]] = None, dtype: Optional[Union[Type, str, np.dtype]] = None ):
        self._shape = None if shape is None else tuple(shape)
        self.dtype = None if dtype is None else np.dtype(dtype)

class Discrete(Space[int]):
    def __init__(self, n: int, start: int = 0 ):
        assert isinstance(n, (int, np.integer))
        assert n > 0, "n (counts) have to be positive"
        assert isinstance(start, (int, np.integer))
        self.n = int(n)
        self.start = int(start)
    
    def sample(self) -> int:
        return int(self.start + np.random.randint(self.n))


    # value_function
    # rewards
    # policy
    # size
    # epsilon

    # num_population
    # num_iteration

    # max_targets

class learning:
    def __init__(self, map_size=10, num_targets=10, wall_perc=0.1,
                epsilon=0.1, num_pop=5, num_step=50, num_iter=100
                ) -> None:     
        self.model = learning_model 
        self.map_size = map_size
        self.num_targets = num_targets
        self.wall_perc = wall_perc
        self.epsilon = epsilon
        self.num_pop = num_pop
        self.num_step = num_step
        self.num_iter = num_iter
        
        self.make_graph = False
        self.adj_matrix = None
        self.methods = [self.q_learning, self.sarsa]
        self.policy = None
        
    def normalize(self, numbers):
        min_val = min(numbers)
        max_val = max(numbers)
        total = sum(numbers)
        range_value = max_val - min_val
        if range_value == 0:
            return [0 for num in numbers]
        else:
            return [(num - min_val)/total for num in numbers]

    def monte_carlo_selection(self, probabilities):
        prob_aux = self.normalize(probabilities)
    
        rand_num = np.random.uniform(0, 1)
    
        position = 0
        for i, p in enumerate(prob_aux):
            if rand_num <= p:
                position = i
                break
            else:
                rand_num -= p
    
        return position

    def shortest_path(self, adj_matrix,start_state,q_table=[],end_state=None):
        n = len(adj_matrix)
        
        seen = [False]*n
        seen[start_state] = True
        distances = [-1]*n
        distances[start_state] = 0
        parent = [-1]*n

        queue = []
        queue.append(start_state)

        closest_state = -1
        best_value = -1

        while queue:
            state = queue.pop(0)
            seen_flag = False
            for vertex, edge in enumerate(adj_matrix[state]):
                if edge != 0 and not seen[vertex] and adj_matrix[vertex,vertex] != 3:
                    seen_flag = True
                    seen[vertex] = True
                    distances[vertex] = distances[state] + 1
                    parent[vertex] = state
                    queue.append(vertex)
                    if adj_matrix[vertex,vertex] < 2:
                        try:
                            vertex_value = (max(q_table[vertex])*4)/distances[vertex]
                            if vertex_value > best_value:
                                closest_state = vertex
                                best_value = vertex_value
                        except:
                            closest_state = vertex
                            queue.clear()
        
        if closest_state != -1:
            path = []
            current = closest_state
            while current != start_state:
                path.append(current)
                current = parent[current]

            return list(reversed(path))
        else:    
            print(f'Return None for shortest path: {start_state} {state} {closest_state} ')
            print(f'Submatrix:\n{self.submatrix(adj_matrix,[state,state],1)}')
            return None

    def show_frames(self, frames):
        for i, frame in enumerate(frames):
            system('cls')
            print(frame['frame'])
            print(f"Timestep: {i + 1} of {len(frames)}")
            print(f"State: {frame['state']}")
            print(f"Action: {frame['action']}")
            print(f"Action Flag: {frame['action_flag']}")
            print(f"Best Actions: {frame['best_actions']}")
            print(f"Possible Actions: {frame['possible_actions']}")
            print(f"Reward: {frame['reward']}")
            print(f"Acumulated Reward: {frame['acumulated_reward']}")
            sys.stdout.flush()
            sleep(0.8)

    def random_map(self, size, num_targets, max_wall_perc=0.1):
        wall_num = int(max_wall_perc*size*size) + np.random.randint(int(max_wall_perc*size*size))
        wall_aux = wall_num
        dirt_num = num_targets
        dirt_aux = dirt_num

        #print(f'Making {(size,size)} map with {wall_num} walls and {dirt_num} dirts')
        total_path = []
        while len(total_path) < size*size - wall_num + 1:
            map = np.zeros([size, size])
            done = False
            while not done:
                if wall_num > 0:
                    x = np.random.randint(size-1)
                    y = np.random.randint(size-1)
                    if map[x,y] == 0:
                        map[x,y] = -1
                        wall_num -= 1

                if dirt_num > 0:
                    x = np.random.randint(size-1)
                    y = np.random.randint(size-1)
                    if map[x,y] == 0:
                        map[x,y] = -2
                        dirt_num -= 1

                if wall_num == 0 and dirt_num == 0:
                    done = True
            
            #Checking map traversability
            wall_num = wall_aux
            dirt_num = dirt_aux
            coord = np.random.randint(low=0,high=size-1,size=2)
            graph = [coord]
            total_path = []
            seen = np.zeros((size,size),dtype=int)
            while graph:
                pos = graph.pop(0)
                total_path.append(pos)
                for i in range(max(0,pos[0]-1),min(size-1,pos[0]+1)+1):
                    if map[i,pos[1]] != -1 and seen[i,pos[1]] == 0:
                        graph.append([i,pos[1]])
                        seen[i,pos[1]] = 1
                for j in range(max(0,pos[1]-1),min(size-1,pos[1]+1)+1):
                    if map[pos[0],j] != -1 and seen[pos[0],j] == 0:
                        graph.append([pos[0],j])
                        seen[pos[0],j] = 1
        try:
            return map
        except Exception as e:
            print(f"{len(total_path) < size*size-wall_num} : {e}")
            sys.exit()

    def submatrix(self, matrix,center,radius):
        x, y = center
        subm_rows = slice(max(0, x-radius), min(x+radius+1, matrix.shape[0]))
        subm_cols = slice(max(0, y-radius), min(y+radius+1, matrix.shape[1]))
        subm = np.zeros((2*radius+1, 2*radius+1), dtype=matrix.dtype)
        subm[:] = -1
        subm[radius-x+subm_rows.start:radius-x+subm_rows.stop, 
            radius-y+subm_cols.start:radius-y+subm_cols.stop] = matrix[subm_rows, subm_cols]
        return subm

    def q_learning(self, q_table, epsilon, e, num_steps=50, num_iter=500):
        alpha = 0.1
        gamma = 0.9 
        sum_acumulated_reward = []
        size = e.num_states
        # Matrix de adjacencia do grafo de exploracao  
        for idx in range(1,num_iter+1):
            adj_matrix = np.zeros((size, size), dtype=int)
            state, _ = e.reset()    # Resetando aspirador para um estado aleatorio
            acumulated_reward = 0

            adj_matrix[state,state] = 2 # Este valor indica na matrix que este estado ja foi explorado
            path_actions = []
            best_states = []
            steps = 0
            while steps < num_steps:
                action, possible_states, path_actions = self.choose_action(e, epsilon, state, q_table, adj_matrix, path_actions)
                next_state, reward, _ = e.step(action)
                acumulated_reward += reward
                
                if next_state in best_states:
                    best_states.remove(next_state)
                
                # Ajustes na matrix de adjacencia
                # Inserindo ligacoes entre estados (valor 1) e estados esplorados (valor 2)
                adj_matrix[next_state,next_state] = 2
                for p_state in possible_states:
                    if adj_matrix[state,p_state] == 0:
                    # print(f"Connecting {state} to {p_state} -> {next_state} ({possible_states}) {possible_actions}")
                        if adj_matrix[p_state,p_state] == 0:
                            adj_matrix[p_state,p_state] = 1
                        adj_matrix[state,p_state] = 1
                        adj_matrix[p_state,state] = 1

                # Linha onde ocorre a retencao do aprendizado
                q_table[state, action] = q_table[state, action] + alpha*(reward + gamma * np.max(q_table[next_state]) - q_table[state, action])
                state = next_state
                steps += 1

            sum_acumulated_reward.append(acumulated_reward)
            if idx == 1:
                print(f"{acumulated_reward}",end=" >> ")
                sys.stdout.flush()
            if idx == num_iter:
                print(f"{np.mean(sum_acumulated_reward,dtype=int)}",end=" | ")
                sys.stdout.flush()
        return q_table

    def choose_action(self, e, epsilon, state, table, adj_matrix, path_actions):
        possible_actions = e.action_mask(state)
        possible_states = e.actions_to_states(possible_actions)
        _, best_actions = e.sensor()
        if sum(best_actions) > 0:   # Usado quando o sensor encontra uma sujeira
            q_actions = np.multiply(table[state],best_actions)
            q_actions = np.add(q_actions,best_actions)
            action = np.argmax(q_actions)
        else:                       
            for ia, act in enumerate(possible_actions): # Verificar disponibilidade de acoes
                if act == 1:
                    s,_,_ = e.look(ia)
                    if adj_matrix[s,s] > 1 and ia != 4:
                        possible_actions[ia] = 0
                
            if sum(possible_actions) == 0 or len(path_actions) > 0: # Usado quando aspirador esta perdido
                if len(path_actions) == 0 or path_actions is None:
                    path = self.shortest_path(adj_matrix,state,table)
                    if path is not None:
                        path_actions = e.states_to_actions(path)
                    if path_actions is None or path is None:
                        print(
                            f"\nCurrent: {state} > ({path}) ({path_actions}) \nPossible States:\
                            \n{[(x,i) for x,i in enumerate(adj_matrix[state]) if x in possible_states]}\
                            \nMap Render:\
                            \n{e.render(adj_matrix)}"
                        )
                        sys.exit()
                        
                action = path_actions.pop(0) # Retornar para areas inexploradas
            elif np.random.uniform(0, 1) < epsilon:
                action = self.monte_carlo_selection(possible_actions)  # Explorar diferentes acoes
            else:
                actions = np.multiply(table[state],possible_actions)
                action = np.argmax(actions) # Utilizar valores aprendidos
        return action, possible_states, path_actions

    def sarsa(self, s_table, epsilon, e, num_steps=50, num_iter=500):
        alpha = 0.1
        gamma = 0.9 
        sum_acumulated_reward = []
        size = e.num_states
        for idx in range(1,num_iter+1):
            adj_matrix = np.zeros((size, size), dtype=int) # Matrix de adjacencia do grafo de exploracao  
            state, _ = e.reset()    # Resetando aspirador para um estado aleatorio
            acumulated_reward = 0

            adj_matrix[state,state] = 2 # Este valor indica na matrix que este estado ja foi explorado
            path_actions = []
            
            action,possible_states,path_actions = self.choose_action(e,epsilon,state,s_table,adj_matrix,path_actions)
            steps = 0
            while steps < num_steps:
                next_state, reward, _ = e.step(action)
                acumulated_reward += reward
                
                # Ajustes na matrix de adjacencia
                # Inserindo ligacoes entre estados (valor 1) e estados esplorados (valor 2)
                adj_matrix[next_state,next_state] = 2
                for p_state in possible_states:
                    if adj_matrix[state,p_state] == 0:
                    # print(f"Connecting {state} to {p_state} -> {next_state} ({possible_states}) {possible_actions}")
                        if adj_matrix[p_state,p_state] == 0:
                            adj_matrix[p_state,p_state] = 1
                        adj_matrix[state,p_state] = 1
                        adj_matrix[p_state,state] = 1
                        
                next_action, possible_states, path_actions = self.choose_action(e,epsilon,next_state,s_table,adj_matrix,path_actions)

                # Linha onde ocorre a retencao do aprendizado
                
                s_table[state, action] = s_table[state, action]+ alpha*(reward + gamma * s_table[next_state][next_action] - s_table[state, action])
                
                state = next_state
                action = next_action
                steps += 1

            sum_acumulated_reward.append(acumulated_reward)
            if idx == 1:
                print(f"{acumulated_reward}",end=" >> ")
                sys.stdout.flush()
            if idx == num_iter:
                print(f"{np.mean(sum_acumulated_reward,dtype=int)}",end=" | ")
                sys.stdout.flush()
        return s_table

    def learn(self, method_index=0):
        print(f'  Average Reward of\n  First and Last Iteration')
        table = np.zeros([self.map_size**2, self.model().num_actions])
        method = self.methods[method_index]
        for i in range(1, self.num_pop+1):
            print(f'Map {i}: ',end='')
            map = self.random_map(self.map_size, self.num_targets)
            env = self.model(map)
            table = method(table, self.epsilon, env, self.num_step, self.num_iter) 
            print('')

        self.policy = table
        
    def exec(self, env, state, num_steps=1, show=False):
        if self.policy is None:
            self.policy = np.zeros([self.map_size**2, self.model().num_actions])
            
        if self.adj_matrix is None: 
            size = env.num_rows*env.num_cols
            self.adj_matrix = np.zeros((size, size), dtype=int) 
        
        env.set_state(state)
        #state, _ = env.encode(x,y)
        reward = 0
        acumulated_reward = 0
        actions_taken = []
        states_arrived = []
        
        self.adj_matrix[state,state] = 2
        possible_actions = []
        path_actions = []
        frames = []
        for _ in range(num_steps):
            flag = 'Best'     
            possible_actions = env.action_mask(state)
            possible_states = env.actions_to_states(possible_actions)
            _, best_actions = env.sensor()
            if sum(best_actions) > 0:
                actions = np.multiply(self.policy[state],best_actions)
                actions = np.add(actions,best_actions)
                action = np.argmax(actions)
            else:
                for ia, act in enumerate(possible_actions):
                    if act == 1:
                        s,_,_ = env.look(ia)
                        if self.adj_matrix[s,s] > 1 and ia != 4:
                            possible_actions[ia] = 0
                actions = np.multiply(self.policy[state],possible_actions)
                if sum(actions) == 0 and sum(possible_actions) > 0:
                    actions = possible_actions
                if sum(actions) > 0 and len(path_actions) == 0:
                    flag = 'Policy'
                    action = np.argmax(actions)
                else:
                    flag = 'Return'
                    if len(path_actions) == 0:
                        path = self.shortest_path(self.adj_matrix,state,self.policy)
                        if path is not None:
                            path_actions = env.states_to_actions(path)
                        if path_actions is None or path is None:
                            print(
                                f"\nCurrent: {state} > ({path}) ({path_actions})\
                                \nAvailable Actions: {actions} = {self.policy[state]}*{possible_actions}\
                                \nPossible States:\
                                \n{[(x,i) for x,i in enumerate(self.adj_matrix[state]) if x in possible_states]}\
                                \nMap Render:\
                                \n{env.render(self.adj_matrix)}"
                            )
                            sys.exit()
                    action = path_actions.pop(0)

            frames.append({
                'frame': env.render(self.adj_matrix),
                'state': state,
                'action': env.last_action,
                'action_flag': flag,
                'best_actions': best_actions,
                'possible_actions': possible_actions,
                'reward': reward,
                'acumulated_reward': acumulated_reward,
            })

            actions_taken.append(action)
            next_state, reward, _ = env.step(action)
            states_arrived.append(next_state)

            self.adj_matrix[next_state,next_state] = 2
            for p_state in possible_states:
                if self.adj_matrix[state,p_state] == 0:
                    if self.adj_matrix[p_state,p_state] == 0:
                        self.adj_matrix[p_state,p_state] = 1
                    self.adj_matrix[state,p_state] = 1
                    self.adj_matrix[p_state,state] = 1

            state = next_state
            acumulated_reward += reward
        
        if show:
            self.show_frames(frames)
        return actions_taken, states_arrived
        
        

        self.policy