from maspy import *
from random import choice

class Cruzamento(Environment):
    def __init__(self, env_name):
        super().__init__(env_name)
        if choice([True, False]):
            self.create(Percept("cruzamento","livre"))
        else:
            self.create(Percept("cruzamento","ocupado"))

    def cruzar(self, src):
        self.print(f"agente {src} cruzou")
    
    def aguardar(self, src):
        self.print(f"agente {src} aguardando")
        self.change(Percept("cruzamento"),"livre")

class VA(Agent):
    def __init__(self, agt_name):
        super().__init__(agt_name)
        self.add(Belief("no_cruzamento"))
        
    @pl(gain, Goal("cruzar"), Belief("no_cruzamento"))
    def realizar_cruzamento(self, src):
        self.print("Realizando o cruzamento")
        self.cruzar()
        self.stop_cycle()
        
    @pl(gain, Goal("aguardar"), Belief("no_cruzamento"))
    def aguardar(self, src):
        self.print("Aguardando")
        self.aguardar()
        self.send("CT",achieve,Goal("verificar_cruzamento"))
        
class CT(Agent):
    def __init__(self, agt_name):
        super().__init__(agt_name)
        self.add(Goal("verificar_cruzamento"))
        
    @pl(gain, Goal("verificar_cruzamento"), Belief("cruzamento", Any,"C1"))    
    def verificar_cruzamento(self, src, status):
        if status == "livre":
            self.print("Cruzamento esta livre, informando agente VA para cruzar")
            self.send("VA",achieve,Goal("cruzar"))
            self.stop_cycle()
        else:
            self.print("Cruzamento ocupado, informando agente VA para aguardar")
            self.send("VA",achieve,Goal("aguardar"))

if __name__=="__main__":
    c1 = Cruzamento("C1")
    ag1 = VA("VA")
    ag2 = CT("CT")
    Admin().connect_to([ag1,ag2],c1)
    Admin().start_system()    
    
    
        
