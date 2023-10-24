
import os
from rich.markdown import Markdown

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
        try:
            with open(os.path.join(os.path.join(shell._config.data_path), "docs", "man_" + command + ".md"), "r") as f:
                print( Markdown(f.read()))
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