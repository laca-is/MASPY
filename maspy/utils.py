from typing import Any
import numpy as np

RNG = RandomNumberGenerator = np.random.Generator

def merge_dicts(dict1: dict[str, dict[str, set[Any]]] | None, dict2: dict[str, dict[str, set[Any]]] | None) -> dict | None:
    if dict1 is None or dict2 is None:
        return None
    for key, value in dict1.items():
        if key in dict2 and isinstance(value, dict):
            for inner_key, inner_value in value.items():
                if inner_key in dict2[key] and isinstance(inner_value, set):
                    dict2[key][inner_key].update(inner_value)
                else:
                    dict2[key][inner_key] = inner_value 
        else:
            dict2[key] = value
    return dict2

def set_changes(original:set, changes:set):
    intersection = original.intersection(changes)
    added = changes - original
    removed = original - intersection
    return intersection.union(added), added, removed

def manual_deepcopy(d: dict[str, dict[str, set[Any]]]) -> dict[str, dict[str, set[Any]]]:
    return {k: {k2: set(v2) for k2, v2 in v.items()} for k, v in d.items()}

def np_random(seed: int | None = None) -> tuple[np.random.Generator, int]:
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