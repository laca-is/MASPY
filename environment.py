
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

class env:
    def __init__(self) -> None:
        self.__caracteristics = {'any' : {'a' : 10}}
        self.__roles = ['any']

    def add_role(self, role_name):
        self.__roles.append(role_name)

    def add_caracteristic(self, name, data, role='any'):
        try: 
            self.__caracteristics[role][name].update(data)
        except(KeyError):
            try:
                self.__caracteristics[role][name] = data
            except(KeyError):
                self.__caracteristics[role] = {name : data}

    def get_caracteristics(self, agent_role=None):
        found_caractersitics = {}
        for role in self.__roles:
            if role == agent_role or role == 'any' or agent_role == 'all':
                for caracteristic in self.__caracteristics[role]:
                    found_caractersitics[caracteristic] = self.__caracteristics[role][caracteristic]
        return found_caractersitics
