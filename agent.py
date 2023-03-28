from dataclasses import dataclass, field

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

    def print_beliefs(self):
        for bel in self.beliefs:
            print(bel)

    def search_beliefs(self, bel, all=False):
        found_beliefs = []
        for belief in self.beliefs:
            if belief.key == bel.key \
            and len(belief.args) == len(bel.args):
                found_beliefs.append(belief)
                if not all:
                    break
        return found_beliefs
    
    def run_plan(self, plan):
        print(f'{self.my_name}> Running {plan}')
        try:
            self.plans[plan.key](*plan.args)
        except(TypeError):
            print(f"Plan {plan} doesn't exist")
    
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
                self.run_plan(msg)

            case ("unachieve", plan):
                self.stop_plan(msg)

            case ("askOne", ask):
                
                found_beliefs = self.search_beliefs(ask)
                self.prepare_msg(ask.source,'tell',found_beliefs[0])

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
    def test(a,b,c):
        print(f'{a} {b} {c}')

    @staticmethod
    def print(a,b):
        print(f'Printing vars {a} {b}')


