# Apply typing fixes at package initialization - must be first!
from .modules import typing_fix

# Version information
# This version should match the version in pyproject.toml
__version__ = "2.0.0"

# Enable flexible configuration if available
try:
    from .modules.config_integration import enable_flexible_configuration

    enable_flexible_configuration()
except ImportError:
    pass

# Export public API
from .api import AskGPTClient

# Export web server app (lazy import to avoid requiring web dependencies)
def get_app():
    """Get the FastAPI application instance."""
    from .web_server import app
    return app

__all__ = ["AskGPTClient", "get_app", "__version__"]

# For convenience, try to export app directly (may fail if web deps not installed)
try:
    from .web_server import app
    __all__.append("app")
except ImportError:
    pass


def hello() -> str:
    return "Hello from askGPT!"
