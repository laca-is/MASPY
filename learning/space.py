from typing import Generic, TypeVar, Sequence, Any, Iterable, Mapping

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
]

class Space(Generic[Cov_Type]):
    def __init__(
            self, 
            shape: Sequence[int] | None = None, 
            dtype: npt.DTypeLike | None = None, 
            seed: int | np.random.Generator | None = None
        ):
        self._shape = None if shape is None else tuple(shape)
        self.dtype = None if dtype is None else np.dtype(dtype)
        
        self._np_random = None
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
        
        self.n = np.int64(n)
        self.start = np.int64(start)
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
 