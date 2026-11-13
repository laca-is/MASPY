from typing import Generic, TypeVar, Sequence, Any, Iterable, Mapping, Tuple

import numpy as np
from numpy.typing import NDArray
import numpy.typing as npt

from maspy.learning.ml_utils import utl_np_random

Cov_Type = TypeVar("Cov_Type", covariant=True)
RNG = RandomNumberGenerator = np.random.Generator
MaskNDArray = npt.NDArray[np.int8]

__all__ = [
    "Space",
    "Discrete",
    "Box",
    "as_box",
]

class Space(Generic[Cov_Type]):
    def __init__(
            self, 
            shape: Sequence[int] | None = None, 
            dtype: npt.DTypeLike | None = None, 
            seed: int | np.random.Generator | None = None
        ):
        self._shape: tuple[int, ...] | None = None if shape is None else tuple(shape)
        self.dtype: npt.DTypeLike = None if dtype is None else np.dtype(dtype)
        
        self._np_random: np.random.Generator | None = None
        if seed is not None:
            if isinstance(seed, np.random.Generator):
                self._np_random = seed
            else:
                self.seed(seed)
        
    def seed(self, seed: int | None = None) -> int | list[int] | dict[str, int] | tuple[int, ...]:
        self._np_random, np_random_seed = utl_np_random(seed)
        return np_random_seed

    @property
    def np_random(self) -> np.random.Generator:
        if self._np_random is None:
            self.seed()

        if self._np_random is None:
            self._np_random, _ = utl_np_random()

        return self._np_random
    
    @property
    def shape(self) -> tuple[int, ...] | None:
        return self._shape
    
    def sample(self, mask: Any | None = None) -> Cov_Type:
        raise NotImplementedError
    
    def contains(self, x: Any) -> bool:
        raise NotImplementedError

    def __contains__(self, x: Any) -> bool:
        return self.contains(x)
       
class Discrete(Space[np.int64]):
    def __init__(
            self, 
            n: int | np.integer[Any], 
            seed: int | np.random.Generator | None = None,
            start: int | np.integer[Any] = 0 
        ):
        assert np.issubdtype(type(n), np.integer), f"Expected integer type, actual type: {type(n)}"
        assert n > 0, "n (counts) have to be positive"
        assert np.issubdtype(type(start), np.integer), f"Expected integer type, actual type: {type(start)}"
        
        self.n: np.int64 = np.int64(n)
        self.start: np.int64 = np.int64(start)
        super().__init__((), np.int64, seed)
    
    def sample(self, mask: MaskNDArray | None = None) -> np.int64:
        if mask is not None:
            assert isinstance(mask, np.ndarray
            ), f"The expected type of the mask is np.ndarray, actual type: {type(mask)}"
            
            assert (mask.dtype == np.int8
            ), f"The expected dtype of the mask is np.int8, actual dtype: {mask.dtype}"
            
            assert mask.shape == (self.n,
            ), f"The expected shape of the mask is {(self.n,)}, actual shape: {mask.shape}"
            
            valid_action_mask = mask == 1
            
            assert np.all(np.logical_or(mask == 0, valid_action_mask)
            ), f"All values of a mask should be 0 or 1, actual values: {mask}"
            
            if np.any(valid_action_mask):
                return self.start + self.np_random.choice(np.where(valid_action_mask)[0])
            else:
                return self.start
            
        return np.int64(self.start + self.np_random.integers(self.n))
    
    def contains(self, x: Any) -> bool:
        """Return boolean specifying if x is a valid member of this space."""
        if isinstance(x, int):
            as_int64 = np.int64(x)
        elif isinstance(x, (np.generic, np.ndarray)) and (
            np.issubdtype(x.dtype, np.integer) and x.shape == ()
        ):
            as_int64 = np.int64(x.item())
        else:
            return False

        return bool(self.start <= as_int64 < self.start + self.n)
    
    def __repr__(self) -> str:
        """Gives a string representation of this space."""
        if self.start != 0:
            return f"Discrete({self.n}, start={self.start})"
        return f"Discrete({self.n})"

    def __eq__(self, other: Any) -> bool:
        """Check whether ``other`` is equivalent to this instance."""
        return (
            isinstance(other, Discrete)
            and self.n == other.n
            and self.start == other.start
        )
        
class Box(Space[NDArray[Any]]):
    """ A (possibly unbounded) box in R^n: the Cartesian product of closed intervals.

    Used to describe continuous states and continuous actions.

    Parameters
    ----------
    low : float | Sequence[float] | np.ndarray
        Lower bound(s). Use ``-np.inf`` for "no lower bound".
    high : float | Sequence[float] | np.ndarray
        Upper bound(s). Use ``np.inf`` for "no upper bound".
    shape : int | Sequence[int], optional
        Shape of the space. Inferred from ``low``/``high`` when they are arrays,
        and ``(1,)`` when both are scalars (same convention as Gymnasium).
        Scalar bounds are broadcast to ``shape``.
    dtype : floating dtype
        Defaults to ``np.float64``.
    seed : int | np.random.Generator, optional

    Examples
    --------
    >>> Box(-1.0, 1.0)                   # a single continuous dimension, shape (1,)
    >>> Box([0, 0], [10, 5])             # a 2D rectangle
    >>> Box(0.0, 1.0, shape=(3,))        # the unit cube in R^3
    """
    def __init__(
            self,
            low: Any,
            high: Any,
            shape: int | np.integer[Any] | Sequence[int] | None = None,
            dtype: npt.DTypeLike = np.float64,
            seed: int | np.random.Generator | None = None
        ):
        dtype = np.dtype(dtype)
        assert dtype.kind == "f", f"Box dtype must be a floating type, actual dtype: {dtype}"

        final_shape: Tuple[int, ...]
        if shape is not None:
            if isinstance(shape, (int, np.integer)):
                final_shape = (int(shape),)
            else:
                final_shape = tuple(int(d) for d in shape)
        elif isinstance(low, np.ndarray) or (isinstance(low, (list, tuple)) and len(low) > 0):
            final_shape = np.asarray(low).shape
        elif isinstance(high, np.ndarray) or (isinstance(high, (list, tuple)) and len(high) > 0):
            final_shape = np.asarray(high).shape
        else:
            final_shape = (1,)

        low_arr = np.broadcast_to(np.asarray(low, dtype=dtype), final_shape).copy()
        high_arr = np.broadcast_to(np.asarray(high, dtype=dtype), final_shape).copy()
        assert not np.any(np.isnan(low_arr)) and not np.any(np.isnan(high_arr)), "Box bounds cannot be NaN"
        assert np.all(low_arr <= high_arr), f"Box requires low <= high everywhere, got low={low_arr}, high={high_arr}"

        self.low: NDArray[Any] = low_arr
        self.high: NDArray[Any] = high_arr
        super().__init__(final_shape, dtype, seed)

    @property
    def shape(self) -> tuple[int, ...]:
        """ Shape of the space (unlike other spaces, a Box always has one) """
        return self.low.shape

    @property
    def size(self) -> int:
        """ Number of scalar dimensions of the space """
        return int(np.prod(self.low.shape, dtype=np.int64))

    def is_bounded(self, manner: str = "both") -> bool:
        """ True if the space is bounded ``"below"``, ``"above"`` or ``"both"`` (default) in every dimension """
        below = bool(np.all(np.isfinite(self.low)))
        above = bool(np.all(np.isfinite(self.high)))
        match manner:
            case "both":
                return below and above
            case "below":
                return below
            case "above":
                return above
            case _:
                raise ValueError(f"manner must be 'both', 'below' or 'above', got {manner!r}")

    def sample(self, mask: None = None) -> NDArray[Any]:
        """ Draw a random point: uniform on bounded dimensions, exponential on half-bounded ones, normal on unbounded ones """
        assert mask is None, "Box does not support masked sampling"        
        rng = self.np_random
        sample = np.empty(self.shape, dtype=self.dtype)

        bounded_below = np.isfinite(self.low)
        bounded_above = np.isfinite(self.high)
        both = bounded_below & bounded_above
        only_below = bounded_below & ~bounded_above
        only_above = ~bounded_below & bounded_above
        neither = ~bounded_below & ~bounded_above

        sample[neither] = rng.normal(size=int(neither.sum()))
        sample[only_below] = rng.exponential(size=int(only_below.sum())) + self.low[only_below]
        sample[only_above] = self.high[only_above] - rng.exponential(size=int(only_above.sum()))
        sample[both] = rng.uniform(self.low[both], self.high[both])
        return sample.astype(self.dtype)

    def contains(self, x: Any) -> bool:
        """ Return boolean specifying if x is a valid member of this space. """
        if not isinstance(x, np.ndarray):
            try:
                x = np.asarray(x, dtype=self.dtype)
            except (TypeError, ValueError):
                return False
        return bool(
            np.can_cast(x.dtype, self.dtype)
            and x.shape == self.shape
            and np.all(x >= self.low)
            and np.all(x <= self.high)
        )

    def clip(self, x: Any) -> NDArray[Any]:
        """ Clip ``x`` into the bounds of the space """
        return np.clip(np.asarray(x, dtype=self.dtype), self.low, self.high)

    def __repr__(self) -> str:
        """Gives a string representation of this space."""
        return f"Box({self.low.tolist()}, {self.high.tolist()}, {self.shape}, {self.dtype})"

    def __eq__(self, other: Any) -> bool:
        """Check whether ``other`` is equivalent to this instance."""
        return (
            isinstance(other, Box)
            and self.shape == other.shape
            and self.dtype == other.dtype
            and np.allclose(self.low, other.low)
            and np.allclose(self.high, other.high)
        )

    def __hash__(self) -> int:
        return hash((self.shape, str(self.dtype), self.low.tobytes(), self.high.tobytes()))


def as_box(data: Any) -> Box:
    """ Build a :class:`Box` from the way continuous states/actions are declared in an Environment.

    Accepted forms:

    * a :class:`Box` (returned as is);
    * ``(low, high)``: scalar bounds give a scalar quantity (shape ``()``, handled as a plain
      ``float``), sequence bounds give a vector quantity (a ``np.ndarray``);
    * ``(low, high, shape)``: scalar bounds broadcast to ``shape``.
    """
    if isinstance(data, Box):
        return data
    try:
        low, high, *rest = data
        assert len(rest) <= 1
    except (TypeError, ValueError, AssertionError):
        raise ValueError(
            f"A continuous space must be declared as a Box, (low, high) or (low, high, shape); got {data!r}"
        ) from None
    if rest:
        return Box(low, high, shape=rest[0])
    if np.ndim(low) == 0 and np.ndim(high) == 0:
        return Box(low, high, shape=())
    return Box(low, high)