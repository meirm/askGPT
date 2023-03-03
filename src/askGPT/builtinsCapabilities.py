"""Show some basic capabilities classes"""

from .capability import Capability

class SampleBuiltinCapability(Capability):
    def __init__(self, **kwargs):
        super().__init__(name="SampleBuiltinCapability", **kwargs)

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


def LoadBuiltinCapabilities():
    caps = {}
    caps["SampleBuiltinCapability"] =  SampleBuiltinCapability( description="Show some basic capabilities classes", version="0.0.1", author="Meir Michanie", license="MIT", credits="", dependencies=[])
    return caps