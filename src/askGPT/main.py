#!/usr/bin/env python
"""
askGPT is a simple command line tool for interacting with OpenAI's API.
It is based on the example provided by OpenAI at https://beta.openai.com/docs/developer-quickstart/1-introduction
Date: 2023/01/23
"""
__title__ = 'askGPT'
__author__ = 'Meir Michanie'
__license__ = 'MIT'
__credits__ = ''
__version__ = "0.6.0"

import os
from .api.openai import ChatGPT
from .config import Config, basicConfig
import click
from rich import print
import backoff
import time
import toml
import platform
import subprocess
from .shell import Shell
from .tools import eprint, sanitizeName


# use pyreadline3 instead of readline on windows
is_windows = platform.system() == "Windows"
if is_windows:
    import pyreadline3  # noqa: F401
else:
    import readline

pass_config = click.make_pass_decorator(Config, ensure=True)

@click.command()
@click.version_option(__version__)
@pass_config
def cli(config):
    if config.progConfig.get("showDisclaimer",True):
        print(config.disclaimer)
    """Use the cmd module to create an interactive shell where the user can all the commands such as query, edit, config, show. We will call a class which we will write later as a child of cmd.cmd"""
    shell = Shell(config)
    shell.cmdloop()

if __name__ == '__main__':
    cli()
