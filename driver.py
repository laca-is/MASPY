from agent import agent, belief, ask, objective

class driver(agent):
    def __init__(self, name, beliefs = [], objectives = []) -> None:
        plans = {'offer': lambda src: driver.offer(self,src),
                 'consider_price': lambda src, p : driver.consider_price(self,src,p)}
        super().__init__(name, beliefs, objectives, plans)

    def offer(agt,src):
        print(f"{agt.my_name}> Offering 20")
        agt.prepare_msg('drv2','achieve',objective('consider_price',[20]))
    
    def consider_price(agt,src,price):
        print(f"{agt.my_name}> Considering price: {price} from {src}")
        my_price = agt.search_beliefs(belief('price',['P'])).args[0]
        if price <= my_price:
            print(f'{agt.my_name}> Accept price')
        else:
            print(f'{agt.my_name}> Reject Price')
            agt.prepare_msg(src,'achieve',objective('consider_price',[int((price+my_price)/2)]))




