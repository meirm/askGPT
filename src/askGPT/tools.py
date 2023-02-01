
import sys
import json

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def sanitizeName(name):
    """
    Sanitize the name of the conversation to be saved."""
    return name.replace(" ", "_").replace("/", "_")

def load_json(file):
    """
    Load json from file"""
    with open(file, "r") as f:
        try:
            return json.load(f)
        except:
            return dict()