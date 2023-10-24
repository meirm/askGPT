import click
import os
from rich import print
from rich.text import Text
import subprocess


from rich.console import Console


def do_submit(shell, args):
    """submit: submit a subject."""
    if shell._config.has.get("license", False):
        with shell.console.status("waiting for response ...", spinner="dots"):
            response = shell._config.chat.submitDialog(shell.conversation_parameters["subject"], shell.conversation_parameters["scenario"])
            if response:
                    text = Text(response)
                    text.stylize("bold magenta")
                    shell.console.print(text)
                    """save to file"""
                    with open(os.path.join(shell._config.conversations_path, shell.conversation_parameters["subject"] + shell._config.fileExtention), "a") as f:
                        if shell.conversation_parameters.get("execute", False):
                            editPrompt = click.prompt(f"{response}\nedit command? [y/n]", type=click.Choice(["y", "n"]), default="n")
                            if editPrompt == "y":
                                edited = click.edit(response)
                                if edited:
                                    response = edited
                            doExec = click.prompt(f"{response}\nExecute command? [y/n]", type=click.Choice(["y", "n"]), default="y")
                            """execute the command in the terminal and edit the response before saving it."""
                            if doExec == "y":
                                result  = subprocess.run(response, stdout=subprocess.PIPE, shell=True, stderr=subprocess.STDOUT)
                                result = result.stdout.decode("utf-8")
                                print(result)
                                saveOutput = click.prompt(f"save output? [Y/e/n]", type=click.Choice(["y", "e", "n"]), default="y")
                                if saveOutput == "e":
                                    edited = click.edit(result)
                                    if edited:
                                        result = edited
                                if saveOutput != "n":
                                    f.write(f"assistant: {response}")
                                    f.write("\n")
                                    f.write(f"user: {str(result)}")
                                    f.write("\n")
                            else:
                                f.write(f"assistant: {response}")
                                f.write("\n")
                        else:
                            f.write(f"assistant: {response}")
                            f.write("\n")
                                    
        shell._config.chat.loadLicense()
    return
