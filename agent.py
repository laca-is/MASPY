from dataclasses import dataclass, field
from collections.abc import Callable

@dataclass
class belief:
    key: str
    args: list = field(default_factory=list)  
    source: str = 'percept'

@dataclass
class ask:
    belief: belief 
    reply: list = field(default_factory=list) 
    source: str = 'unknown'

@dataclass
class plan:
    key: str
    body: Callable
    args: list = field(default_factory=list)
    source: str = 'percept'


MSG = belief | ask | plan

class agent:
    def __init__(self, name, beliefs = [], objectives = [], plans = {}) -> None:
        self.my_name = name
        self.beliefs = beliefs
        self.objectives = objectives
        self.plans = {'reasoning' : lambda s : self.reasoning(s)}
        self.plans.update(plans)

        plan.body = lambda : self.reason()
        plan.body()

        print(f'{name}> Initialized')
    
    def add_belief(self, belief):
        if belief not in self.beliefs:
            self.beliefs.append(belief)

        print(f'{self.my_name}> Adding {belief}')

    def rm_belief(self, belief):
        self.beliefs.remove(belief)

        print(f'{self.my_name}> Removing {belief}')

    def print_beliefs(self):
        for belief in self.beliefs:
            print(belief)

    def search_beliefs(self, bel, all=False):
        found_beliefs = []
        for belief in self.beliefs:
            if belief.key == bel.key \
            and len(belief.args) == len(bel.args):
                if not all:
                    found_beliefs = belief
                    break
                else:
                    found_beliefs.append(belief)
        return found_beliefs
    
    def run_plan(self, plan):
        print(f'{self.my_name}> Running {plan}')
        try:
            return self.plans[plan.key](*plan.args)
        except(TypeError, KeyError):
            print(f"Plan {plan} doesn't exist")
            raise RuntimeError #TODO: Define New error or better error
    
    def stop_plan(self, plan):
        pass

    def recieve_msg(self, sender, act, msg: MSG):
        print(f'{self.my_name}> Received from {sender} : {act} -> {msg}')
        match (act, msg):
            case ("tell", belief): 
                self.add_belief(msg)

            case ("untell", belief): 
                self.rm_belief(msg)

            case ("achieve", plan):
                self.add_objetive()
                return self.run_plan(msg)

            case ("unachieve", plan):
                self.stop_plan(msg)

            case ("askOne", ask):
                found_belief = self.search_beliefs(ask.belief)
                self.prepare_msg(ask.source,'tell',found_belief)

            case ("askAll", ask):
                found_beliefs = self.search_beliefs(ask.belief,True)
                for bel in found_beliefs:
                    self.prepare_msg(ask.source,'tell',bel)

            case ("tellHow", belief):
                pass

            case ("untellHow", belief):
                pass

            case ("askHow", belief):
                pass

            case _:
                print(f"ERROR: Unknwon type of message {act} | {msg}")

    def prepare_msg(self, target, act, msg: MSG):
        msg.source = self.my_name
        match (act, msg):
            case ("askOne"|"askAll", belief):
                msg = ask(msg,source=self.my_name)
                
        print(f"{self.my_name}> Sending to {target} : {act} -> {msg}")
        self.send_msg(target, act, msg)

    def send_msg(self, target, act, msg):
        pass

    @staticmethod
    def reason():
        print('HI')

    @staticmethod
    def reasoning(self):
        pass
        # print(f'{self.my_name} Started')
        # self.perception()
        # self.execution()
    
    def executuion(self):
        result = self.recieve_msg(self.my_name,'achieve',self.objectives[-1])
        
            

    def perception(self):
        pass
