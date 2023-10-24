import shlex
from askGPT.tools   import eprint, sanitizeName
import os

def do_clone(shell,args):
    """if len(arg) == 1 then copy the current conversation to a new file using arg[1]"""
    args = shlex.split(args)
    if len(args) == 0:
        eprint("You must provide a name for the new conversation")
    else:
        if len(args) == 1:
            new_subject = sanitizeName(args[0])
        else:
            eprint("You can only provide one argument")
            return
        if new_subject in shell._config.get_list():
            eprint(f"Subject {new_subject} already exists")
            return
        current_subject = shell.conversation_parameters["subject"]
        filename = os.path.join(shell._config.conversations_path, f"{current_subject}{shell._config.fileExtention}")
        with open(filename, "r") as r:
            text = r.read()
        filename = os.path.join(shell._config.conversations_path, f"{new_subject}{shell._config.fileExtention}")
        with open(filename, "w") as w:
            w.write(text)
        shell.conversation_parameters["subject"] = new_subject
        print(f"Conversation {new_subject} created")