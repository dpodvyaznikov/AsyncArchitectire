import os
import json

def validate_event(event, path, schema):
    with open(os.path.join(path, schema)) as f:
        reference = json.load(f)
    rec_check(reference, event)

def rec_check(reference, examined):
    keys_diff = set(reference.keys()).symmetric_difference(set(examined.keys()))
    if keys_diff:
        raise ValueError(f"Event keys do not comply with schema: {keys_diff}")

    for (ref_key, ref_val) in reference.items():
        if isinstance(ref_val, str):
            if ref_key == 'title':
                pass
            elif type(examined[ref_key]).__name__ != ref_val:
                raise ValueError(f"Event value type does not comply with schema: {ref_key}:{examined[ref_key]}")
        elif isinstance(ref_val, dict):
            rec_check(ref_val, examined[ref_key])
        else:
            raise ValueError(f"Invalid reference key: {ref_key}")
