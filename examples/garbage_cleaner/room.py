from maspy.environment import Environment

class Room(Environment):
    def __init__(self, env_name='room'):
        super().__init__(env_name)
        self._create_fact("dirt",{1:(0,1)})
        self._extend_fact("dirt",{2:(3,4)})
        