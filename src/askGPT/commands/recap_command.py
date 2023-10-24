import shlex
from askGPT.tools   import eprint
import os

def do_recap(shell, args):
    """prints the text from the conversation file using the subject.ai.txt """
    args = shlex.split(args)
    if len(args) == 0:
        subject = shell.conversation_parameters["subject"]
    else:
        subject = args[0]
        if subject not in shell._config.get_list():
            eprint(f"Subject {subject} not found")
            return
    filename = os.path.join(shell._config.conversations_path, f"{subject}{shell._config.fileExtention}")
    if os.path.isfile(filename):
        with open(filename, "r") as f:
            print(f.read())
    else:
        eprint(f"File {filename} not found")


def complete_recap(shell,text, line, begidx, endidx):
    """complete_query: complete the query command."""
    if not text:
        completions = shell._config.get_list()
    else:
        completions = [ f
                        for f in shell._config.get_list()
                        if f.startswith(text)
                        ]
    return completions