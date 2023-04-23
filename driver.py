from maspy.agent import agent, Belief, Ask, Objective

class driver(agent):
    def __init__(self, name, beliefs = [], objectives = [], plans = {}) -> None:
        super().__init__(name, beliefs, objectives, plans)
        self.add_plan({'offer': driver.offer,
                    'consider_price': driver.consider_price,
                    'test_focus' : driver.test_focus})

    def test_focus(self,src):
        env = self.add_focus('environment').env()
        env.add_caracteristic('vagas',['A2',False],'gerente')
        env.add_caracteristic('vagas',{'A1':True},'gerente')
        env.add_role('gerente')
        print(env.get_caracteristics('all'))
    
    def offer(self,src):
        agents = self.search_beliefs(Belief('Agents',['A'])).args[0]
        print(f"{self.my_name}> Offering 20 to all drivers")
        for agent_name in agents:
            if self.my_name != agent_name and agents[agent_name] == 'driver':
                self.prepare_msg(agent_name,'achieve',Objective('consider_price',[20]))
    
    def consider_price(self,src,price):
        print(f"{self.my_name}> Considering price: {price} from {src}")
        try:
            my_price = self.search_beliefs(Belief('price',['P'])).args[0]
            if price <= my_price:
                print(f'{self.my_name}> Accept price')
            else:
                print(f'{self.my_name}> Reject Price')
                self.prepare_msg(src,'achieve',Objective('consider_price',[int((price+my_price)/2)]))
        except(AttributeError):
            print(f"{self.my_name}> I don't have a price")



