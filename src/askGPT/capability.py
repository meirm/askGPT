"""
We will load from .askGPT/capabilities/ all existent modules.

We will create a class for each module, which will inherit from the base class Capability.

The base class Capability will have the following methods:

__init__(self, config, name, description, version, author, license, credits, dependencies, **kwargs)

__str__(self)

__repr__(self)

__call__(self, *args, **kwargs)

__getattr__(self, name)

__setattr__(self, name, value)

__delattr__(self, name)

__dir__(self)

__getattribute__(self, name)

__getstate__(self)

__setstate__(self, state)

__reduce__(self)

"""

from .tools import eprint

class Capability:
    def __init__(self, name: str, description: str, version: str, author: str, license: str, credits: str, dependencies: list, **kwargs):
       
        self.name = name
        self.description = description
        self.version = version
        self.author = author
        self.license = license
        self.credits = credits
        self.dependencies = dependencies
        self.enabled = True
        self.__dict__.update(kwargs)

    # def __str__(self):
    #     return f"Capability: {self.name}"

    # def __repr__(self):
    #     return f"Capability: {self.name}"

    # def __call__(self, *args, **kwargs):
    #     return self.__dict__

    # def __getattr__(self, name):
    #     return self.__dict__[name]

    # def __setattr__(self, name, value):
    #     self.__dict__[name] = value

    # def __delattr__(self, name):
    #     del self.__dict__[name]

    # def __dir__(self):
    #     return self.__dict__.keys()

    # def __getattribute__(self, name):
    #     return self.__dict__[name]

    # def __getstate__(self):
    #     return self.__dict__

    # def __setstate__(self, state):
    #     self.__dict__ = state

    # def __reduce__(self):
    #     return self.__dict__
