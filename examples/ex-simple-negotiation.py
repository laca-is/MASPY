from maspy import *
from random import choice, randint

class Seller(Agent):
    @pl(gain, Goal("Buying", Any))
    def buy_product(self, src, product):
        my_product = self.get(Belief("Product", (product, Any)))
        if my_product:
            self.print(f"{src} is Buying {product}:{my_product.args[1]}")
            self.rm(my_product)
        else:
            self.print(f"{product} is not available for {src}")
        self.stop_cycle()
    
    @pl(gain, Belief("Reject", (Any, Any)))
    def product_rejected(self, src, reject):
        product, reason = reject
        self.print(f"{src} rejected {product} because {reason}")
        self.stop_cycle()

class Buyer(Agent):
    @pl(gain, Goal("Buy", Any), Belief("Budget", Any))
    def buy_product(self, src, product, budget):
        
        self.print(f"Looking to Buy {product}")
        
        seller_product = self.send("Seller", askOneReply, Belief("Product", (product, Any)))
        
        if seller_product and seller_product.args[1] <= budget:
            self.print(f"Accepting {product} for {seller_product.args[1]}. I had {budget}")
            self.send("Seller", achieve, Goal("Buying", product))
        else:
            self.print(f"Rejected {product} for {seller_product.args[1]}. I had {budget}")
            self.send("Seller", tell, Belief("Reject", (product, "Expensive")))
        self.stop_cycle()
        
if __name__ == "__main__":
    Seller( beliefs=[ Belief("Product",("Food", 5)),
                      Belief("Product",("Clothing", 10))]
    )
    Buyer( beliefs= Belief("Budget", randint(1, 12)),
           goals= Goal("Buy", choice(["Food", "Clothing"]))
    )
    Admin().start_system()



    