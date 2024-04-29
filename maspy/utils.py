class utils:
    def merge_dicts(dict1: dict, dict2: dict) -> dict:
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