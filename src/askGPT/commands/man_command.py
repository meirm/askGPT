
import os
from rich.markdown import Markdown
import importlib.resources as pkg_resources
from askGPT.tools import eprint

def do_man(shell, line):
    """ when passed the name of a command it will pint an extensive explanation of the command by loading a markup file from data/"""
    if line:
        command = shell.parseline(line)
        if command[0] in shell.commands:
            command = command[0]
        else:
            command = None
    else:
        command = None
    if command:
        # To get the path to a directory 'data' within your 'askGPT' package
        try:
            # This gives you a path-like object you can use
            data_path = pkg_resources.files('askGPT').joinpath('data')
            data_dir = str(data_path)
            man_path = os.path.join( data_dir, "docs", "man_" + command + ".md")
            eprint(f"man_path = {man_path}")
            with open(man_path, "r") as f:
                shell.console.print( Markdown(f.read()))
        except FileNotFoundError:
            print("No manual entry for", command)   

def complete_man(shell,text, line, begidx, endidx):
    """complete_query: complete the query command."""
    if not text:
        completions = list(shell.commands.keys())
    else:
        completions = [ f
                        for f in shell.commands.keys()
                        if f.startswith(text)
                        ]
    return completions