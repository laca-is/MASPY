from agent import agent, belief, ask, objective

class driver(agent):
    def __init__(self, name, beliefs = [], objectives = [], plans = {}) -> None:
        super().__init__(name, beliefs, objectives)
        self.beliefs = beliefs.copy()
        self.objectives = objectives.copy()
        self.plans.update({'offer': lambda self,src: driver.offer(self,src),
                        'consider_price': lambda self,src, p : driver.consider_price(self,src,p)})
        self.plans.update(plans)
    
    def offer(self,src):
        agents = self.search_beliefs(belief('Agents',['A'])).args[0]
        print(f"{self.my_name}> Offering 20 to all drivers")
        for agent_name in agents:
            if self.my_name != agent_name and agents[agent_name] == 'driver':
                self.prepare_msg(agent_name,'achieve',objective('consider_price',[20]))
    
    def consider_price(self,src,price):
        print(f"{self.my_name}> Considering price: {price} from {src}")
        try:
            my_price = self.search_beliefs(belief('price',['P'])).args[0]
            if price <= my_price:
                print(f'{self.my_name}> Accept price')
            else:
                print(f'{self.my_name}> Reject Price')
                self.prepare_msg(src,'achieve',objective('consider_price',[int((price+my_price)/2)]))
        except(AttributeError):
            print(f'{self.my_name}> I don\'t have a price')



