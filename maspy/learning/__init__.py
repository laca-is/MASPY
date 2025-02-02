# from maspy.learning.core import (
#    Model, Wrapper, ObservationWrapper, RewardWrapper, ActionWrapper,
# )

# from maspy.learning.registration import (
#     make, spec, register, registry, register_envs,
# )

# from maspy.learning.space import (
#     Space, Box, Discrete, MultiDiscrete, MultiBinary, Tuple, Dict,
# )

from maspy.learning.modelling import (
    EnvModel,qlearning, sarsa, sequence, combination, permutation, cartesian, listed
)

# register(
#     id="taxi_ml",
#     entry_point="maspy.learning.ex_taxi_ml:TaxiEnv",
#     reward_threshold=8,  # optimum = 8.46
#     max_episode_steps=200,
# )

__all__ = [
    # # Core
    # "Model",
    # "Wrapper",
    # "ObservationWrapper",
    # "RewardWrapper",
    # "ActionWrapper",
    # # Registration
    # "make",
    # "spec",
    # "register",
    # "registry",
    # "register_envs",
    # # Space
    # "Space",
    # "Box",
    # "Discrete",
    # "MultiDiscrete",
    # "MultiBinary", 
    # "Tuple",
    # "Dict",
    # Generic
    "EnvModel",
    "qlearning",
    "sarsa",
    "sequence",
    "combination",
    "permutation",
    "cartesian",
    "listed"
]