from maspy.agent import Agent, Belief, Ask, Objective

class driver(Agent):
    def __init__(self, name, beliefs = [], objectives = [], plans = {}) -> None:
        super().__init__(name, beliefs, objectives, plans)
        self.cross = self.add_focus('crossroads')
        self.add_plan({})

    
    
    # def offer(self,src):
    #     agents = self.search_beliefs(Belief('Agents',['List']))
    #     print(agents)
    #     print(f"{self.my_name}> Offering 20 to all drivers")
    #     for agent_name in agents:
    #         if self.my_name != agent_name and agents[agent_name] == 'driver':
    #             self.prepare_msg(agent_name,'achieve',Objective('consider_price',[20]))
    
    # def consider_price(self,src,price):
    #     print(f"{self.my_name}> Considering price: {price} from {src}")
    #     try:
    #         my_price = self.search_beliefs(Belief('price',['P'])).args[0]
    #         if price <= my_price:
    #             print(f'{self.my_name}> Accept price')
    #         else:
    #             print(f'{self.my_name}> Reject Price')
    #             self.prepare_msg(src,'achieve',Objective('consider_price',[int((price+my_price)/2)]))
    #     except(AttributeError):
    #         print(f"{self.my_name}> I don't have a price")



