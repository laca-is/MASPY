import inspect
from functools import wraps
from agent import agent

class env:
    def __init__(self) -> None:
        self.agents = {}
        agent.send_msg = self.function_call(agent.send_msg)

    def create_agent(self,name='agent_1'):
        if name in self.agents:
            aux = name.split('_')
            name = (''.join(str(x) for x in aux[:-1]))\
                    +'_'+str(int(aux[-1])+1)
            pass
        ag = agent(name)
        self.agents[name] = ag
        return ag 

    def function_call(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            arg_values = inspect.getcallargs(func, *args, **kwargs)
            #print(arg_values)
            msg = {}
            for key,value in arg_values.items():
                msg[key] = value
            try:
                self.agents[msg['target']].recieve_msg(msg['self']\
                                .my_name,msg['act'],msg['msg'])
            except(KeyError):
                print(f"Agent {msg['target']} doesn't exist")

        
            return func(*args, **kwargs)
        
        return wrapper

