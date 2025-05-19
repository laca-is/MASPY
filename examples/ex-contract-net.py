from maspy import *
from random import randint

class Iniciador(Agent):
    def __init__(self, agt_name=None):
        super().__init__(agt_name)
        self.add(Goal("iniciar"))

    @pl(gain,Goal("iniciar"))
    def iniciar(self,src):
        
        valor_inicial = randint(15,30)
        self.print(f"Enviando pedido de proposta com valor inicial {valor_inicial} a todos participantes")
        self.send(broadcast, tell, Belief("pedir_proposta",randint(15,30)))
        
    @pl(gain,Belief("recusado"))
    def recusado(self,src):
        self.print(f"{src} recusou fazer uma proposta")
    
    @pl(gain,Goal("proposta",Any))
    def proposta(self,src,valor_proposto):
        if valor_proposto < 10:
            self.print(f"{src} fez uma proposta com valor {valor_proposto} que foi recusada")
            self.send(src,tell,Belief("proposta_recusada", valor_proposto))
        else:
            self.print(f"{src} fez uma proposta com valor {valor_proposto} que foi aceita")
            self.send(src,tell,Belief("proposta_aceita",valor_proposto))
    
    @pl(gain,Belief("negociacao_completa",Any))
    def negociacao_completa(self,src,valor):
        self.print(f"{src} aceitou o valor {valor}. Negociacao completa")
    
    @pl(gain,Belief("negociacao_falha", Any))
    def negociacao_falha(self,src,valor):
        self.print(f"{src} aceitou o valor {valor} porém ja negociou com outro")
    
class Partiticipante(Agent):
    def __init__(self, agt_name=None):
        super().__init__(agt_name)
        self.add(Belief("valor_maximo",randint(1,30)))
        self.add(Belief("Negociando"))
    
    @pl(gain,Belief("pedir_proposta", Any), [Belief("valor_maximo", Any), Belief("Negociando")])
    def pedir_proposta(self,src, valor, valor_maximo):
        if valor > 1.5 * valor_maximo:
            self.print(f"{src} pediu uma proposta para {valor} mas meu valor maximo eh de {valor_maximo}")
            self.send(src,tell,Belief("recusado"))
        else:
            valor_proposto = randint(10, valor-5)
            self.print(f"{src} pediu uma proposta para {valor}, fazendo proposta para {valor_proposto}")
            self.send(src,achieve,Goal("proposta",valor_proposto))
    
    @pl(gain,Belief("proposta_recusada", Any))
    def proposta_recusada(self,src, valor):
        self.print(f"{src} recusou a proposta de {valor}")
    
    @pl(gain,Belief("proposta_aceita", Any), Belief("Negociando"))
    def proposta_aceita_1(self,src, valor):
        self.print(f"{src} aceitou a proposta de {valor}, finalizando negociacao")
        self.rm(Belief("Negociando"))
        self.send(src,tell,Belief("negociacao_completa",valor))
    
    @pl(gain,Belief("proposta_aceita", Any), ~Belief("Negociando"))
    def proposta_aceita_2(self,src, valor):
        self.print(f"{src} aceitou a proposta de {valor}, porem ja negociei com outro iniciador")
        self.send(src,tell,Belief("negociacao_falha",valor))

if __name__ == "__main__":
    [Iniciador() for _ in range(3)]
    [Partiticipante() for _ in range(5)] 
    Admin().start_system()