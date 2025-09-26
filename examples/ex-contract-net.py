from maspy import *
from random import randint

class Initiator(Agent):
    def __init__(self, agt_name=None):
        super().__init__(agt_name)
        self.add(Goal("start"))
        self.idle_counter = -1

    @pl(gain, Goal("start"))
    def start(self, src):
        self.idle_counter = 0
        value = randint(15,30)
        self.add(Belief("half_value", value/2))
        self.print(f"Broadcasting value {value} to all participants")
        self.send(broadcast, tell, Belief("request_offer", randint(15,30)))
    
    @pl(gain, Goal("offer", Any), Belief("half_value", Any))
    def offer(self, src, offered_value, half_value):
        self.idle_counter = 0
        if offered_value < half_value:
            self.print(f"{src}'s offer ({offered_value}) refused")
            self.send(src, tell, Belief("offer_refused", offered_value))
        else:
            self.print(f"{src}'s offer ({offered_value}) accepted")
            self.send(src, tell, Belief("offer_accepted", offered_value))
    
    @pl(gain, Belief("negotiation_complete", Any))
    def negotiation_complete(self, src, value):
        self.idle_counter = 0
        self.print(f"{src} accepted ({value}). Negotiation complete")
    
    @pl(gain, Belief("negotiation_failed", Any))
    def negotiation_failed(self, src, value):
        self.idle_counter = 0
        self.print(f"{src} accepted ({value}) but had already negotiated")

class Participant(Agent):
    def __init__(self, agt_name=None):
        super().__init__(agt_name)
        self.idle_counter = -1
        self.best_offer = [500,""]
        self.add(Belief("max_value", randint(1,30)))
        self.add(Belief("Negotiating"))
    
    @pl(gain, Belief("request_offer", Any), [Belief("max_value", Any), Belief("Negotiating")])
    def request_offer(self, src, value, max_value):
        self.idle_counter = 0
        if value > 1.5 * max_value:
            self.print(f"Refusing {src}'s value ({value}) > {max_value}")
        else:
            offered_value = randint(10, value-5)
            self.print(f"Offering ({offered_value}) for {src}'s {value}")
            self.send(src, achieve, Goal("offer", offered_value))
    
    @pl(gain, Belief("offer_accepted", Any))
    def offer_accepted(self, src, value):
        self.idle_counter = 0
        if value < self.best_offer[0]:
            self.print(f"Received good value {value} from {src} < {self.best_offer}")
            self.best_offer = [value, src]
        else:
            self.print(f"Already accepted better value {value} > {self.best_offer}")
    
    @pl(gain, Belief("offer_refused", Any))
    def offer_refused(self, src, value):
        self.idle_counter = 0
        self.print(f"{src} rejected offer of {value}")

if __name__ == "__main__":
    [Initiator() for _ in range(5)]
    [Participant() for _ in range(15)] 
    Admin().start_system()

