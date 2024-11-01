from maspy import *
import random as rnd
from time import sleep

end_flag = 0

class Parking(Environment):
    def __init__(self, env_name,nr_spots=10):
        super().__init__(env_name)
        self.create(Percept("sold_spots",0,adds_event=False))
        self.print(f"Starting parking with {nr_spots} spots")
        for n in range(1,nr_spots+1):
            self.create(Percept("spot",(n,"free"),adds_event=False))
    
    def park_spot(self, agt, spot_id):
        spot = self.get(Percept("spot",(spot_id,"free")))
        if spot:
            self.change(spot,(spot_id,[agt]))
        else:
            self.print(f"Requested spot({spot_id}) unavailable")
            return None
    
    def leave_spot(self, agt):
        spot = self.get(Percept("spot",("ID",[agt])))
        if spot:
            self.print(f"Driver {agt} leaving spot({spot.args[0]})")
            self.change(spot,(spot.args[0],"free"))
        else:
            self.print(f"Driver {agt} not found in any spot")
            pass

class Manager(Agent):
    def __init__(self, agt_name=None):
        super().__init__(agt_name,read_all_mail=True)
        self.add(Belief("spotPrice",15,adds_event=False))
        self.add(Belief("minPrice",10,adds_event=False))
        self.add(Goal("broadcast_price"))
        self.end_counter = 0
    
    @pl(gain,Goal("broadcast_price"),Belief("spotPrice","SP"))
    def send_price(self,src,spot_price):
        self.print(f"Broadcasting spot price[{spot_price}] to all Agents in Parking Channel.")
        self.send(broadcast,achieve,Goal("checkPrice",spot_price),"Parking")
    
    @pl(gain,Goal("offer_answer",("Answer","Price")),Belief("minPrice","MP"))
    def offer_response(self,src,offer_answer,min_price):
        answer, price = offer_answer
        match answer:
            case "reject":
                self.print(f"Given price[{price}] rejected by {src}")
                pass
            case "accept":
                self.print(f"Price accepted[{price}] by {src}. Choosing spot.")
                self.add(Goal("SendSpot",src),True)
            case "offer":
                if price < min_price:
                    counter_offer = (min_price+price)/1.2
                    counter_offer = round(counter_offer,2)
                    self.print(f"Price offered[{price}] from {src} too low. Counter-offer[{counter_offer}]")
                    self.send(src,achieve,Goal("checkPrice",counter_offer),"Parking")
                else:
                    self.print(f"Offered price from {src} accepted[{price}]. Choosing spot.")
                    self.add(Goal("SendSpot",src),True)
    
    @pl(gain,Goal("SendSpot","Agent"), Belief("spot",("Id","free"),"Parking"))        
    def send_spot(self, src, agent, spot):
        #self.perceive("Parking")
        #free_spots = self.get(Belief("spot",("Id","free"),"Parking"),all=True)
        #if free_spots:
        #    random_spot = rnd.choice(free_spots)
        #    spot_id = random_spot.args[0]
        spot_id = spot[0]
        self.print(f"Sending spot({spot_id}) to {agent}")
        self.send(agent,achieve,Goal("park",("Parking",spot_id)),"Parking")
    
    @pl(gain,Goal("SendSpot","Agent"))
    def unavailable_spot(self, src, agent):
        self.print(f"No spots available for {agent}")
        self.send(agent,tell,Belief("no_spots_available"),"Parking")
    
    
    
class Driver(Agent):
    def __init__(self, agt_name, budget, counter, wait):
        super().__init__(agt_name)
        self.counter = counter
        self.wait_time = wait
        self.last_price = 0
        self.add(Belief("budget",budget,adds_event=False))
    
    @pl(gain,Goal("checkPrice","Price"),Belief("budget",("WantedPrice","MaxPrice")))
    def check_price(self,src,given_price,budget):
        max_price, want_price = budget
        self.add(Belief("offer_made",given_price,adds_event=False))
        if self.last_price == given_price:
            self.print(f"Rejecting price[{given_price}]. Same as last offer")
            answer = ("reject",given_price)
        elif given_price > 2*max_price:
            self.print(f"Rejecting price[{given_price}]. Too Higher than my max[{max_price}]")
            answer = ("reject",given_price)
        elif given_price <= want_price:
            self.print(f"Accepting price [{given_price}]. Wanted[{want_price}]")
            answer = ("accept",given_price)
        else:
            counter_offer = (want_price+given_price)/(self.counter+1.5)
            counter_offer = round(counter_offer,2)
            self.print(f"Making counter-offer for price[{given_price}]. Offering[{counter_offer}]")
            answer = ("offer",counter_offer)
            
        if answer[0] == "reject": 
            self.end_reasoning()
        else:
            self.add(Belief("offer_answer",answer,adds_event=False))
            self.send(src,achieve,Goal("offer_answer",answer),"Parking")
            self.last_price = given_price
        #if answer[0] == "reject": 
        #    self.end_reasoning()
    
    @pl(gain,Belief("no_spots_available"))
    def no_spots(self,src):
        self.print("Leaving because no spots!")
        self.end_reasoning()
        
    
    @pl(gain,Goal("park",("Park_Name","SpotID")))
    def park_on_spot(self,src,spot):
        park_name, spot_id = spot
        self.connect_to(Environment(park_name))
        self.print(f"Parking on spot({spot_id})")
        confirm = self.action(park_name).park_spot(self.str_name,spot_id)
        if confirm is None:
            self.print(f"Spot is unavailable after given by {src}")
            self.end_reasoning()
            return None
        sleep(self.wait_time)
        self.print(f"Leaving spot({spot_id})")
        self.action(park_name).leave_spot(self.str_name)
        self.disconnect_from(Environment(park_name))
        self.end_reasoning()
        
    def end_reasoning(self):
        self.stop_cycle()
        global end_flag
        with self.lock:
            end_flag += 1
        print(f"{self.str_name} Ended reasoning ({end_flag})")
        if Admin().running_class_agents("Drv") is False:
            Admin().stop_all_agents()
        
if __name__ == "__main__":
    park = Parking('Parking',100)
    park_ch = Channel("Parking")
    manager = Manager()
    
    drv_settings: dict = {"budget": [(10,12),(10,14),(10,20),(12,14),(12,16)],
                    "counter": [0.4, 0.8, 1, 1.2, 1.4],
                    "wait": [0, 0.5, 0.7, 1, 1.5]}
    driver_list: list[Agent] = []
    for i in range(1000):
        budget = drv_settings["budget"][i%5]
        counter = drv_settings["counter"][(i*2)%5]
        wait = drv_settings["wait"][(i*4)%5]
        driver_list.append(Driver("Drv",budget,counter,wait))

    Admin().block_prints()
    Admin().connect_to(manager, [park,park_ch])
    Admin().connect_to(driver_list, park_ch)
    Admin().start_system()