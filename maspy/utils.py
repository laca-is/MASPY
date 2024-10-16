from typing import Any

def merge_dicts(dict1: dict[Any, dict[Any, set[Any]]] | None, dict2: dict[Any, dict[Any, set[Any]]] | None) -> dict | None:
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

def manual_deepcopy(d: dict[Any, dict[Any, set[Any]]]) -> dict[Any, dict[Any, set[Any]]]:
    return {k: {k2: set(v2) for k2, v2 in v.items()} for k, v in d.items()}