from maspy import *

class MaquinaCafe(Environment):
    def __init__(self, env_name):
        super().__init__(env_name)
        self.create(Percept("tem_agua"))

    def preparar_cafe(self, src):
        self.print(f"Preparar cafe para o agente: {src}")


class AgenteCafe(Agent):
    def __init__(self, agent_name):
        super().__init__(agent_name)
        self.add(Belief("quero_cafe"))  # Crenca inicial

    @pl(gain,Belief("quero_cafe"))
    def maquina_pronta(self,src):
        self.print("Verificar ambiente")
        percepcao1 = self.get(Belief("tem_agua",source="Expresso"))
        percepcao2 = self.get(Belief("tem_graos",source="Expresso"))
        self.print(percepcao1.name)       # imprime o valor das percepcoes obtidas do ambiente
        self.print(percepcao2.name)
        if percepcao1 and percepcao2:                   # testa se ha conteudo nas "percepcoes"
            self.preparar_cafe()   # chama acao do ambiente
        self.stop_cycle()

if __name__ == "__main__":
    maquina = MaquinaCafe("Expresso")
    agente = AgenteCafe("Cafe35")
    Admin().connect_to([agente],[maquina])
    maquina.create(Percept("tem_graos"))
    Admin().full_report = True
    Admin().start_system()