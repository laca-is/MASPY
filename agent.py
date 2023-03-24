from dataclasses import dataclass, field

@dataclass(frozen=True, order=True)
class belief:
    key: str
    args: list = field(default_factory=list)  
    source: str = 'percept'

@dataclass(frozen=True, order=True)
class ask:
    key: str
    args: list = field(default_factory=list) 
    reply: list = field(default_factory=list) 
    source: str = 'unknown'

@dataclass(frozen=True, order=True)
class plan:
    key: str
    args: list = field(default_factory=list)
    source: str = 'percept'


MSG = belief | ask | plan

class agent:
    def __init__(self, name) -> None:
        self.my_name = name
        self.beliefs = []
        self.plans = {
            'test' : lambda a,b,c : agent.test(a,b,c), 
            'print' : lambda a,b : agent.print(a,b)
        }

        print(f'{name}> Initialized')
    
    def add_belief(self, belief):
        if belief not in self.beliefs:
            self.beliefs.append(belief)

        print(f'{self.my_name}> Adding {belief}')

    def rm_belief(self, belief):
        self.beliefs.remove(belief)

        print(f'{self.my_name}> Removing {belief}')

    def run_plan(self, plan):
        print(f'{self.my_name}> Running {plan}')
        try:
            self.plans[plan.key](*plan.args)
        except(TypeError):
            print(f"Plan {plan} doesn't exist")
    
    def stop_plan(self, plan):
        pass

    def search_beliefs(self, ask, all=False):
        found_beliefs = []
        for belief in self.beliefs:
            if belief.key == ask.key \
            and len(belief.args) == len(ask.key):
                found_beliefs.append(belief)
                if not all:
                    return found_beliefs

    def recieve_msg(self, sender, act, msg: MSG):
        print(f'{self.my_name}> Received from {sender} : {act} -> {msg}')
        match (act, msg):
            case ("tell", belief): 
                self.add_belief(msg)

            case ("untell", belief): 
                self.rm_belief(msg)

            case ("achieve", plan):
                self.run_plan(msg)

            case ("unachieve", plan):
                self.stop_plan(msg)

            case ("askOne", ask):
                found_beliefs = self.search_beliefs(ask)
                self.prepare_msg(ask.source,'tell',found_beliefs[0])

            case ("askAll", belief):
                found_beliefs = self.search_beliefs(ask,True)
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

    def prepare_msg(self, target, act, msg):
        print(f"{self.my_name}> Sending to {target} : {act} -> {msg}")
        self.send_msg(target, act, msg)

    def send_msg(self, target, act, msg):
        pass

    @staticmethod
    def test(a,b,c):
        print(f'{a} {b} {c}')

    @staticmethod
    def print(a,b):
        print(f'Printing vars {a} {b}')


