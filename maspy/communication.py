import inspect
from functools import wraps
from maspy.agent import agent

class comms:
    def __init__(self, env_name='Comm') -> None:
        self.env_name = env_name
        agent.send_msg = self.function_call(agent.send_msg)
                    
    def function_call(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            arg_values = inspect.getcallargs(func, *args, **kwargs)
            msg = {}
            for key,value in arg_values.items():
                msg[key] = value 
            try:
                self.__agents[msg['target']].recieve_msg(msg['self']\
                                .my_name,msg['act'],msg['msg'])
            except(KeyError):
                print(f"Agent {msg['target']} doesn't existsssss")

        
            return func(*args, **kwargs)
        
        return wrapper

