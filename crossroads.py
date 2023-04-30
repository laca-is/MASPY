from maspy.environment import env

class crossroads(env):
    def __init__(self, env_name='cross') -> None:
        super().__init__(env_name)
        # Criando duas vias vazias (Indicado por False)
        self.create_fact('Lane',{'South>North': False,
                                 'East>West': False})
        
    def entered_lane(self, lane_name):
        ...
        
