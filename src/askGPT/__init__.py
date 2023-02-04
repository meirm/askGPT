import pkg_resources

DATA_PATH = pkg_resources.resource_filename('askGPT', 'data/')
from .main import cli
