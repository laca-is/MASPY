import numpy as np
import inspect
from functools import partial
from typing import Callable, Any, TYPE_CHECKING
from numpy.typing import NDArray
from copy import deepcopy

if TYPE_CHECKING:
    from maspy.learning.space import ( 
            Space, Discrete
        )

RNG = RandomNumberGenerator = np.random.Generator

__all__ = [
    "env_render_passive_checker",
    "env_reset_passive_checker",
    "env_step_passive_checker",
    "check_action_space",
    "check_observation_space",
    "TileCoder",
]

def normalize(data, new_min=0, new_max=1):
    data = np.array(data) 
    old_min = np.min(data)
    old_max = np.max(data)
    
    if old_min == old_max:
        return np.full_like(data, new_min) if old_min == 0 else np.full_like(data, new_max)
    
    normalized = (data - old_min) / (old_max - old_min)
    
    scaled = normalized * (new_max - new_min) + new_min
    return scaled

def monte_carlo_selection(probabilities):
    prob_aux = normalize(probabilities)
    
    cumulative = np.cumsum(prob_aux)
    total = cumulative[-1]  # Ensure proper normalization in case of rounding errors
    
    rand_num = np.random.uniform(0, total)
    
    position = np.searchsorted(cumulative, rand_num)
    
    # probs = prob_aux / np.sum(prob_aux)
    
    # rand_num = np.random.uniform(0, 1)

    # position = 0
    # for i, p in enumerate(probs):
    #     if rand_num <= p:
    #         position = i
    #         break
    #     else:
    #         rand_num -= p
    
    #from time import sleep
    #print(f'{probabilities} > {cumulative} > {rand_num} > {position}')
    #sleep(1)
    return position

def utl_np_random(seed: int | list[int] | None = None) -> tuple[np.random.Generator, int]:
        if seed is not None and not (isinstance(seed, int) and 0 <= seed):
            if isinstance(seed, int) is False:
                raise ValueError(
                    f"Seed must be a python integer, actual type: {type(seed)}"
                )
            else:
                raise ValueError(
                    f"Seed must be greater or equal to zero, actual value: {seed}"
                )

        seed_seq = np.random.SeedSequence(seed)
        np_seed = seed_seq.entropy
        assert isinstance(np_seed, int)
        rng = RandomNumberGenerator(np.random.PCG64(seed_seq))
        return rng, np_seed

def categorical_sample(prob_n, np_random: np.random.Generator):
    """Generates a random sample from a categorical distribution.

    Args:
        prob_n (Iterable[float]): The probabilities of each category.
        np_random (numpy.random.Generator): A random number generator.

    Returns:
        int: The index of the selected category.

    Raises:
        ValueError: If the input probabilities do not sum to 1.
    """
    prob_n = np.asarray(prob_n)
    csprob_n = np.cumsum(prob_n)
    return np.argmax(csprob_n > np_random.random())

class TileCoder:
    """ Sparse tile coding of a bounded continuous box (Sutton & Barto, section 9.5.4).

    The box is covered by ``n_tilings`` overlapping grids, each one shifted by a fraction of a tile.
    A point activates exactly one tile per grid, so a value function over continuous inputs
    can be stored as a sparse ``dict`` keyed by tile, exactly like a tabular Q-table.

    Parameters
    ----------
    low, high : array-like
        Bounds of the (flattened) box. Points outside are clipped to the border tiles.
    bins : int | array-like
        Number of tiles per dimension of a single grid (an int applies to every dimension).
    n_tilings : int
        Number of overlapping grids. ``1`` gives plain uniform discretization.
    """
    def __init__(self, low: Any, high: Any, bins: int | Any = 10, n_tilings: int = 8) -> None:
        self.low = np.asarray(low, dtype=np.float64).reshape(-1)
        self.high = np.asarray(high, dtype=np.float64).reshape(-1)
        if self.low.shape != self.high.shape:
            raise ValueError(f"low and high must have the same size, got {self.low.shape} and {self.high.shape}")
        if not (np.all(np.isfinite(self.low)) and np.all(np.isfinite(self.high))):
            raise ValueError("Tile coding needs finite bounds")
        self.dims = self.low.size
        self.bins = np.broadcast_to(np.asarray(bins, dtype=np.int64), (self.dims,)).copy()
        if np.any(self.bins < 1) or n_tilings < 1:
            raise ValueError("bins and n_tilings must be positive")
        self.n_tilings = int(n_tilings)

        span = self.high - self.low
        span[span == 0] = 1.0   # degenerate dimension: everything falls in the first tile
        self._scale = self.bins / span
        # asymmetrical displacement of the grids (first odd numbers), see Miller & Glanz (1996)
        dim_steps = 2 * np.arange(self.dims) + 1
        self._offsets = ((np.arange(self.n_tilings)[:, None] * dim_steps[None, :]) % self.n_tilings) / self.n_tilings

    def _scaled(self, x: Any) -> NDArray[Any]:
        x = np.asarray(x, dtype=np.float64).reshape(-1)
        if x.size != self.dims:
            raise ValueError(f"Expected a point with {self.dims} dimension(s), got {x.size}")
        return np.clip((x - self.low) * self._scale, 0.0, self.bins - 1e-9)

    def tiles(self, x: Any) -> list[tuple[int, ...]]:
        """ The active tile of each tiling, as hashable ``(tiling, *coordinates)`` tuples """
        coords = np.floor(self._scaled(x) + self._offsets).astype(np.int64).tolist()
        return [(t, *row) for t, row in enumerate(coords)]

    def cell(self, x: Any) -> tuple[int, ...]:
        """ Coordinates of the finest region that the tilings can tell apart (a tile divided by ``n_tilings``) containing ``x`` """
        return tuple(np.floor(self._scaled(x) * self.n_tilings).astype(np.int64).tolist())


color2num = dict(
    gray=30,
    red=31,
    green=32,
    yellow=33,
    blue=34,
    magenta=35,
    cyan=36,
    white=37,
    crimson=38,
)

def colorize(
    string: str, color: str, bold: bool = False, highlight: bool = False
) -> str:
    """Returns string surrounded by appropriate terminal colour codes to print colourised text.

    Args:
        string: The message to colourise
        color: Literal values are gray, red, green, yellow, blue, magenta, cyan, white, crimson
        bold: If to bold the string
        highlight: If to highlight the string

    Returns:
        Colourised string
    """
    attr = []
    num = color2num[color]
    if highlight:
        num += 10
    attr.append(str(num))
    if bold:
        attr.append("1")
    attrs = ";".join(attr)
    return f"\x1b[{attrs}m{string}\x1b[0m"
