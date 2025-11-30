"""
Small IO helpers.
"""

import json
import os

def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=2)

def read_json(path):
    with open(path, "r") as fh:
        return json.load(fh)
