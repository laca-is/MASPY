from maspy import *
import random as rnd
from time import sleep

class Parking(Environment):
    def __init__(self, env_name=None):
        super().__init__(env_name)
        for n in range(1,10):
            self.create(Percept("spot",(n,"free"),adds_event=False))
    
    def park_spot(self, agent, spot_id):
        spot = self.get(Percept("spot",(spot_id,"free")))
        if spot:
            self.change(spot,(spot_id,agent))
            self.print(f"Driver {agent} parking on spot({spot_id})")
        else:
            self.print(f"Requested spot({spot_id}) unavailable")
    
    def leave_spot(self, agent):
        spot = self.get(Percept("spot",("ID",agent)))
        if spot:
            self.print(f"Driver {agent} leaving spot({spot.args[0]})")
            self.change(spot,(spot.args[0],"free"))
        else:
            self.print(f"Driver {agent} not found in any spot")
    
class Manager(Agent):
    def __init__(self, agt_name=None):
        super().__init__(agt_name)
        self.add(Belief("spotPrice",rnd.randint(12,20),adds_event=False))
        self.add(Belief("minPrice",rnd.randint(6,10),adds_event=False))

    
    @pl(gain,Goal("sendPrice"),Belief("spotPrice","SP"))
    def send_price(self,src,spot_price):
        self.send(src,achieve,Goal("checkPrice",spot_price),"Parking")
    
    @pl(gain,Belief("offer_answer",("Answer","Price")),Belief("minPrice","MP"))
    def offer_response(self,src,answer,price,min_price):
        match answer:
            case "reject":
                self.print(f"Given price[{price}] rejected")
            case "accept":
                self.print(f"Price accepted[{price}]. Choosing spot.")
                self.send_spot(src)
            case "offer":
                if price < min_price:
                    counter_offer = (min_price+price)/(1.5*rnd.random()+1.5)
                    counter_offer = round(counter_offer,2)
                    self.print(f"Price offered[{price}] too low. Counter-offer[{counter_offer}]")
                    self.send(src,achieve,Goal("checkPrice",counter_offer),"Parking")
                else:
                    self.print(f"Offered price accepted[{price}]. Choosing spot.")
                    self.send_spot(src)
            
    def send_spot(self, agent):
        free_spots = self.get(Belief("spot",("Id","free"),"Parking"),all=True)
        if free_spots:
            random_spot = rnd.choice(free_spots)
            spot_id = random_spot.args[0]
            self.send(agent,achieve,Goal("park",("Parking",spot_id)),"Parking")
        else:
            self.send(agent,tell,Belief("no_spots_available"))
    
class Driver(Agent):
    def __init__(self, agt_name=None):
        super().__init__(agt_name)
        self.add(Belief("budget",(rnd.randint(6,10),rnd.randint(12,20)),adds_event=False))
        self.add(Goal("park"))
    
    @pl(gain,Goal("park"))
    def ask_price(self,src):
        self.send("Manager",achieve,Goal("sendPrice"),"Parking")
    
    @pl(gain,Goal("checkPrice","Price"),Belief("budget",("WantedPrice","MaxPrice")))
    def check_price(self,src,given_price,want_price,max_price):
        if given_price > max_price:
            self.print(f"Rejecting price[{given_price}]. Higher than my max[{max_price}]")
            answer = ("reject",given_price)
        elif given_price <= want_price:
            self.print(f"Accepting price [{given_price}]. Wanted[{want_price}]")
            answer = ("accept",given_price)
        else:
            counter_offer = (want_price+given_price)/(1.5*rnd.random()+1.5)
            counter_offer = round(counter_offer,2)
            self.print(f"Making counter-offer for price[{given_price}]. Offering[{counter_offer}]")
            answer = ("offer",counter_offer)
            
        self.send(src,tell,Belief("offer_answer",answer,"Parking"))
        if answer[0] == "reject": self.stop_cycle()
            
    @pl(gain,Goal("park",("Park_Name","SpotID")))
    def park_on_spot(self,src,park_name,spot_id):
        self.connect_to(Environment(park_name))
        self.print(f"Parking on spot({spot_id})")
        self.action(park_name).park_spot(self.my_name,spot_id)
        sleep(5)
        self.print(f"Leaving spot({spot_id})")
        self.action(park_name).leave_spot(self.my_name)
        self.disconnect_from(Environment(park_name))
        self.stop_cycle()
    
        
if __name__ == "__main__":
    park = Parking()
    park_ch = Channel("Parking")
    manager = Manager()
    driver_list = []
    for _ in range(10):
        driver_list.append(Driver("Drv"))
    Admin().connect_to(manager, [park,park_ch])
    Admin().connect_to(driver_list, park_ch)
    Admin().start_system()