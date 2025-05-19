from maspy import *
from random import randint

cnd = lambda *args, **kwargs: (args, kwargs)

class Website(Environment):
    def announce_trip(self, agt, trip):
        self.print(f"Trip announced by {agt}: {trip}")
        self.create(Percept("trip",{"seller":agt,"attributes":trip}))
    
    def delist_trip(self, agt, trip):
        self.print(f"Trip delisted by {agt}: {trip['attributes']}")
        self.delete(Percept("trip",trip))

class Seller(Agent):    
    def __init__(self, agt_name=None):
        super().__init__(agt_name)
        self.add(Goal("announce"))
        
    @pl(gain,Goal("announce"))
    def create_trips(self, src):
        for _ in range(5):
            stops = randint(0,6)
            trip = (stops,randint(int(700/(stops+1)),1000))
            self.print(f"Creating trip: {trip}")
            self.announce_trip(trip)
        
    @pl(gain,Goal("buy",Any))
    def trip_bought(self, src, trip):
        if self.has(Belief("trip",trip)):
            self.print(f"Selling trip: {trip['attributes']} to {src}")
            self.delist_trip(trip)
            self.send(src,tell,Belief("travel_ticket",trip))
        else:
            self.print(f"Trip {trip['attributes']} not found for {src}")
            self.send(src,achieve,Goal("buyTrip"))
    
    @pl(gain,Goal("improve",(Any,Any)))
    def improve_trip(self, src, improve_args):
        trip, reason = improve_args
        match reason:
            case "stops":
                new_stop = trip['attributes'][0] - 1
                new_price = trip['attributes'][1] + randint(100,200)
            case "price":
                new_stop = trip['attributes'][0] + 1
                new_price = trip['attributes'][1] - randint(50,150)
        
        new_trip = (new_stop,new_price)
        self.print(f"Creating an improved trip: {trip['attributes']} -> {new_trip} because of {reason} for {src}")
        self.announce_trip(new_trip)
        new_trip = {"seller":self.my_name,"attributes":new_trip}
        self.send(src,achieve,Goal("check",new_trip))
    
class Buyer(Agent):
    def __init__(self, agt_name, max_stops, max_price):
        super().__init__(agt_name)
        self.add(Belief("preferences",(max_stops,max_price),adds_event=False))
        self.add(Goal("buyTrip"))
    
    @pl(gain, Goal("buyTrip"), Belief("preferences",(Any,Any)))
    def search_trip(self, src, prefs):
        self.wait(1)
        trips = self.get(Belief("trip",Any),all=True,ck_src=False)

        if trips is None:
            self.print(f"No trips available")
            self.wait(1)
            self.add(Goal("buyTrip"))
            return
        
        best_score = 0
        best_trip = Belief
        best_reason = ""
        for trip in trips:
            assert isinstance(trip, Belief)
            score, reason = self.evaluate_trip(trip.args,prefs)
            if score > best_score:
                best_score = score
                best_trip = trip
                best_reason = reason
        
        if best_score > 2:
            self.print(f"Trip from {best_trip.args['seller']} accepted: {best_trip.args['attributes']}")     
            self.send(best_trip.args['seller'],achieve,Goal("buy",best_trip.args))
        else:
            self.print(f"Trip from {best_trip.args['seller']} rejected: {best_trip.args['attributes']}, asking to improve {best_reason}")
            self.send(best_trip.args['seller'],achieve,Goal("improve",(best_trip.args,best_reason)))
    
    @pl(gain, Goal("check",Any), Belief("preferences",(Any,Any)))
    def check_trip(self, src, trip, prefs):
        score, reason = self.evaluate_trip(trip,prefs)
        if score > 1.8:
            self.print(f"Trip from {trip['seller']} accepted: {trip['attributes']}")
            self.send(src,achieve,Goal("buy",trip))
        else:
            self.print(f"Trip from {trip['seller']} rejected: {trip['attributes']} because of {reason}. Giving up")
            self.stop_cycle()
        
    def evaluate_trip(self,trip: dict, prefs: tuple) -> tuple[float, str]:
        stops, price = trip['attributes']
        max_stops, max_price = prefs
        
        stop_diff = 1 - (stops-max_stops)/6
        price_diff = 1 - (price-max_price)/1000
        score = stop_diff + price_diff
        
        if stop_diff < price_diff:
            improve = "stops"
        else:
            improve = "price"
        
        return score, improve
    
    @pl(gain, Belief("travel_ticket",Any))
    def ticket_received(self, src, trip):
        self.print(f"Received travel ticket for trip {trip['attributes']} from {src}")
        self.stop_cycle()
      
if __name__ == "__main__":
    ws = Website()
    agent_list: list = [Seller() for _ in range(1)]
    
    for _ in range(3):
        stops = randint(0,6)
        buyer = Buyer("Buyer", randint(0,6), randint(int(700/(stops+1)),1000))
        agent_list.append(buyer)
    
    Admin().connect_to(agent_list,ws)
    Admin().start_system()