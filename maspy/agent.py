from dataclasses import dataclass, field
from maspy.system_control import control
from time import sleep
import importlib as implib

@dataclass
class Belief:
    key: str
    args: list = field(default_factory=list)  
    source: str = 'percept'

@dataclass
class Ask:
    belief: Belief 
    reply: list = field(default_factory=list) 
    source: str = 'unknown'

@dataclass
class Objective:
    key: str
    args: list = field(default_factory=list)
    source: str = 'percept'

MSG = Belief | Ask | Objective

class agent:
    def __init__(self, name, beliefs, objectives, plans) -> None:
        if beliefs is None or not beliefs:
            beliefs = []
        if objectives is None or not objectives:
            objectives = []
        if plans is None or not plans:
            plans = {}
        
        self.my_name = name
        control().add_agents(self)
        
        self.__environments = {}
        self.__beliefs = beliefs
        self.__objectives = objectives
        self.__plans = plans
        self.__plans.update({'reasoning' : self.reasoning})
        
        self.paused_agent = False   
        print(f'{self.my_name}> Initialized')
    
    def add_focus(self, environment):
        self.__environments[environment] = implib.import_module(environment)
        return self.__environments[environment]
    
    def rm_focus(self, environment):
        del self.__environments[environment]
    
    def add_belief(self, belief):
        assert type(belief) == Belief
        if belief not in self.__beliefs:
            self.__beliefs.append(belief)

    def rm_belief(self, belief):
        self.__beliefs.remove(belief)

    def add_objective(self, objective):
        assert type(objective) == Objective
        if objective not in self.__objectives:
            self.__objectives.append(objective)
            
            if self.paused_agent:
                self.paused_agent = False
                self.__plans['reasoning']()

    def rm_objective(self, objective):
        self.__objectives.remove(objective)

    def add_plan(self, plan):
        assert type(plan) == dict
        for funcs in plan.values():
            assert callable(funcs)
        self.__plans.update(plan)
    
    def rm_plan(self, plan):
        del(self.__plans[plan.key])

    def print_beliefs(self):
        for belief in self.__beliefs:
            print(belief)

    def search_beliefs(self, bel, all=False):
        found_beliefs = []
        for belief in self.__beliefs:
            if belief.key == bel.key \
            and len(belief.args) == len(bel.args):
                if not all:
                    return belief
                else:
                    found_beliefs.append(belief)
        return found_beliefs
    
    def __run_plan(self, plan):
        sleep(0.2)
        print(f"{self.my_name}> Running plan(key='{plan.key}', args={plan.args}, source={plan.source})")
        try:
            return self.__plans[plan.key](self, plan.source, *plan.args)
        except(TypeError, KeyError):
            print(f"{self.my_name}> Plan {plan} doesn't exist")
            raise RuntimeError #TODO: Define New error or better error

    def __stop_plan(self, plan):
        print(f"{self.my_name}> Stoping plan(key='{plan.key}', args={plan.args}, source={plan.source})")
        pass

    def recieve_msg(self, sender, act, msg: MSG):
        if not act == 'env_tell':
            print(f'{self.my_name}> Received from {sender} : {act} -> {msg}')
        match (act, msg):
            case ("tell", belief): 
                self.add_belief(belief)
                print(f'{self.my_name}> Adding {belief}')

            case ("env_tell", belief): 
                self.add_belief(belief)
                print(f'{self.my_name}> Adding Env Belief')
            
            case ("untell", belief): 
                self.rm_belief(belief)
                print(f'{self.my_name}> Removing {belief}')

            case ("achieve", objective):
                print(f'{self.my_name}> Adding {objective}')
                self.add_objective(objective)
                
            case ("unachieve", objective):
                self.rm_objective(objective)
                print(f'{self.my_name}> Removing {objective}')

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
                msg = Ask(msg,source=self.my_name)
                
        print(f"{self.my_name}> Sending to {target} : {act} -> {msg}")
        self.send_msg(target, act, msg)

    def send_msg(self, target, act, msg):
        pass

    def reasoning(self):
        while self.__objectives:
            self.perception()
            # Adicionar guard para os planos
            #  -funcao com condicoes para o plano rodar
            #  -um plano eh (guard(),plano())
            self.execution()
        self.paused_agent = True
            
    def perception(self):

        pass

    def execution(self):
        if not self.__objectives:
            return None
        objective = self.__objectives[-1]
        print(f"{self.my_name}> Execution of {objective}")
        try:
            result = self.__run_plan(objective)
            if objective in self.__objectives:
                self.rm_objective(objective)

        except(RuntimeError):
            print(f"{self.my_name}> {objective} failed")

