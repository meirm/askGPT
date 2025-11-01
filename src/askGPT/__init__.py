# Apply typing fixes at package initialization - must be first!
from .modules import typing_fix

# Version information
__version__ = "1.0.0"

# Enable flexible configuration if available
try:
    from .modules.config_integration import enable_flexible_configuration

    enable_flexible_configuration()
except ImportError:
    pass


def hello() -> str:
    return "Hello from askGPT!"
