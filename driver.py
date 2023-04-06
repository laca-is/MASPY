from agent import agent, belief, ask, objective

class driver(agent):
    def __init__(self, name, beliefs = [], objectives = []) -> None:
        self.plans = {'offer': lambda src: driver.offer(self,src)}
        self.plans.update({'consider_price': lambda src, p : driver.consider_price(self,src,p)})
        super().__init__(name, beliefs, objectives, self.plans)

    def offer(agt,src):
        print(f"{agt.my_name}> Offering 20")
        agt.prepare_msg('drv2','achieve',objective('consider_price',[20]))
    
    
    def consider_price(agt,src,price):
        print(f"{agt.my_name}> Considering price: {price} from {src}")
        bel = agt.search_beliefs(belief('price',['P']))
        my_price = bel.args[0]
        if price <= my_price:
            print('Accept price')
        else:
            print(f'{agt.my_name}> Reject Price')
            agt.prepare_msg(src,'achieve',objective('consider_price',[int((price+my_price)/2)]))

    @staticmethod
    def hello(agt):
        agt.prepare_msg('drv2','achieve',objective('hello'))
        print(f"{agt.my_name}> hello ")



