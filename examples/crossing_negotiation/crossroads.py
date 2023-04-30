from maspy.environment import Environment

class crossroads(Environment):
    def __init__(self, env_name='cross') -> None:
        super().__init__(env_name)
        # Criando duas vias vazias (Indicado por False)
        self._create_fact('Lane',{'South>North': False,
                                 'East>West': False})
        
    def entered_lane(self, lane_name):
        ...
        
