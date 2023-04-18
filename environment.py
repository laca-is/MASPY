
'''
gerenciar 
    caracteristicas do ambiente
    artefato do ambiente
    cargo de agentes neste ambiente
    comunicacao do ambiente
'''

'''
Get perception:
    verificar situacao do ambiente
        -olhar todas caracteristicas
        -considerar cargo do agente

'''

#attributes = { 'gerente' : {'vagas' : [['A1', True],['A2',False]], 'catraca': 'open'} ,
#         'motorista' : { {},{} }, 
#         'any' : {'time' : 2023} }

class env:
    def __init__(self) -> None:
        self.__caracteristics = {'any' : {}}

    def add_caracteristic(self, name, structure, role='any'):
        print('hue')
        self.__caracteristics[role].update({name : structure})

    #def get_caracteristics(self, name, role):
