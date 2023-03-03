from .capability import Capability
import toml

def loadCapabilities(config):
    capabilities = {}
    import os
    import importlib
    """create capabilities directory if it doesn't exist"""
    if not os.path.exists(os.path.join(config.settingsPath, "capabilities")):
        os.mkdir(os.path.join(config.settingsPath, "capabilities"))
    """load all capabilities from the capabilities directory"""
    for file in os.listdir(os.path.join(config.settingsPath, "capabilities")):
        if file.endswith(".py") and not file.startswith("_"):
            name = file[:-3]
            module = importlib.import_module(f"askGPT.capabilities.{name}")
            """from the capabilities directory load the toml of the respective capability if exists"""
            moduleConfig = dict()
            if os.path.exists(os.path.join(config.settingsPath, "capabilities", name, "capability.toml")):
                with open(os.path.join(config.settingsPath, "capabilities", name, "capability.toml")) as f:
                    moduleConfig  = toml.load(f)
            capabilities[name] = module.loadCapability(moduleConfig)
    return capabilities

def loadCapabilityFromPath(path):
    import importlib
    import os
    module = importlib.import_module(path)
    moduleConfig = dict()
    if os.path.exists(os.path.join(path, "capability.toml")):
                with open(os.path.join(path, "capability.toml")) as f:
                    moduleConfig  = toml.load(f)
    return module.loadCapability(moduleConfig)

