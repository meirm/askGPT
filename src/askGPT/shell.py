import cmd
import shlex
import pkgutil
import shutil 
from .tools   import eprint, sanitizeName
import toml
import os
import sys
import rich
import importlib
from pathlib import Path
from rich import print
from rich.text import Text
from rich.style import Style
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.markdown import Markdown
from .tools import strToValue, addMetadata
import requests
import datetime
from rich.console import Console
import click
from filecmp import cmp
import subprocess

danger_style = Style(color="red", blink=False, bold=True)
attention_style = Style(color="yellow", blink=False, bold=True)
ok_style = Style(color="green", blink=False, bold=False)



"""Here we will define the class Shell which is a child of cmd.cmd which will allow us to run all the commands interactively such as query, config, edit."""
class Shell(cmd.Cmd):
    def __init__(self, config) -> None:
        super().__init__()
        self.console = Console()
        self.intro = "Welcome to askGPT. Type help or ? to list commands."
        self.doc_header = "Commands (type help <topic>):"
        self.misc_header = "Miscellaneous help topics:"
        self.undoc_header = "Undocumented commands:"
        self.ruler = "-"
        self._config = config
        self.commands = dict()
        self.lastResponse = None
        self._register_commands()
        self._register_completion_methods()
        self.conversation_parameters = {
            "subject": "test",
            "scenario": "ChatGPT",
            "model": "gpt-3.5-turbo",
            "defaultCommand": "query",
            "execute": False

        }
        if os.path.exists(os.path.join(self._config.settingsPath, "last.toml")):
            self.conversation_parameters.update(toml.load(os.path.join(self._config.settingsPath, "last.toml")))
        self.prompt = f"{self.conversation_parameters['scenario']}> "
        # when we load we initializr the chat list
        self.chatList = self._config.chat.createPrompt(self.conversation_parameters['subject'], self.conversation_parameters['scenario'], None)
        self._config.chat.load(self.chatList)
        self.commands["update"]("")

    
    def _register_commands(self):
        """Register all the commands."""
        command_package = 'askGPT.commands'  # This is your package where commands are located.
        
        # Dynamically list the modules in the specified package.
        command_modules = pkgutil.iter_modules(importlib.import_module(command_package).__path__)

        for module_info in command_modules:
            if module_info.name.endswith('_command'):
                command_name = "unknown"
                try:
                    # Import the module
                    module = importlib.import_module(f".{module_info.name}", command_package)

                    # Extract the command's name from the module name (assuming the format is '<command>_command')
                    command_name = module_info.name.rsplit('_', 1)[0]

                    # Find and register 'do_' functions (i.e., the command actions)
                    do_function = getattr(module, f"do_{command_name}", None)
                    if callable(do_function):
                        # Bind the function as a method of this class instance
                        bound_method = do_function.__get__(self)
                        setattr(self, f"do_{command_name}", bound_method)
                        self.commands[command_name] = bound_method  # Optional, if you want to keep track of commands
                        
                    # Here, you can also extend it to find and register 'help_' and 'complete_' functions, if available.

                except ImportError as e:
                    # Handle import errors here. You can log the error message if you have a logging system.
                    print(f"Failed to import command '{command_name}': {str(e)}")


    def _register_completion_methods(self):
        # Assuming 'askGPT.shell' is the package where Shell class is defined,
        # and 'commands' is a subpackage containing your commands.
        command_package = 'askGPT.commands'

        # Get the path of the 'commands' subpackage
        package_path = importlib.import_module(command_package).__path__

        # Discover and load all command modules in the 'commands' subpackage
        for importer, modname, ispkg in pkgutil.iter_modules(package_path):
            try:
                # Import the module
                module = importlib.import_module(f".{modname}", command_package)
            except ImportError as e:
                print(f"Error importing module {modname}: {e}")
                continue  # Skip this module

            # Attach complete_* functions from the module to the Shell instance
            for attribute_name in dir(module):
                if attribute_name.startswith("complete_"):
                    # Get the function from the module
                    complete_function = getattr(module, attribute_name)

                    # Bind the function as a method of this class instance
                    bound_method = complete_function.__get__(self)
                    setattr(self, attribute_name, bound_method)
        
    

    def precmd(self, line):
        """This method is called after the line has been input but before
        it has been interpreted. If you want to modify the input line
        before execution (for example, variable substitution) do it here.
        """
        if line.startswith('/'):
            return line[1:]  # Remove the slash and treat the rest as the command
        elif line.startswith("!"):
            return line
        elif line.startswith('?'):
            return line
        else:
            return "query " + line
        

    def postcmd(self, stop, line):
        """postcmd: print the result."""
        #print("Result:", stop)
        return stop


    """Write function similar to do_exec but that it is able to save the output from the command being executed."""
    def execStdout(self, command: list):
        result = subprocess.run(args=command, stdout=subprocess.PIPE)
        return result.stdout.decode('utf-8')
    
    
    def saveSession(self):
        """EOF: exit the shell."""
        """ save the current parameters in a toml file to be loaded in the next session"""
        with open(os.path.join(os.path.join(self._config.settingsPath, "last.toml")), "w") as f:
            toml.dump(self.conversation_parameters, f)


    def emptyline(self):
        """emptyline: do nothing."""
        pass

    def default(self, line):
        if line == "!!":
            # take the last response from AI and esecute it. This is meanly useful when using the sharedTermninal scenario. We want to capture the output and feed it into the conversation as the user prompt.
            if self.lastResponse:
                self.commands["exec"](self.lastResponse)

            pass
        elif line.startswith("!"):
            self.commands["exec"](line[1:])
        elif self.conversation_parameters.get("defaultCommand","query") == "query":

            self.commands["exec"](line)
        else:
            """default: print the error message."""
            print("Unrecognized command:", line)

    def postloop(self):
        """postloop: print the exit message."""
        print("Exiting askGPT.")

    



    
