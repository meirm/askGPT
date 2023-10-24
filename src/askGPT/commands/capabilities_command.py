import shlex
from askGPT.tools import  eprint

def do_capabilities(shell, args):
    args = shlex.split(args)
    if len(args) == 0:
        """list all the capabilities"""
        for capability in sorted(shell.capabilities):
            print(f"{capability}: {shell.capabilities[capability].description}")
    elif len(args) == 1:
        if args[0] == "enable":
            eprint("No capability provided.")
        elif args[0] == "disable":
            eprint("No capability provided.")
        elif args[0] == "info":
            eprint("No capability provided.")
        else:
            eprint("Unrecognized parameter.")
    elif len(args) == 2:
        if args[0] == "enable":
            if args[1] in shell.capabilities:
                shell.capabilities[args[1]].enabled = True
            else:
                eprint("Capability not found.")
        elif args[0] == "disable":
            if args[1] in shell.capabilities:
                shell.capabilities[args[1]].enabled = False
            else:
                eprint("Capability not found.")
        elif args[0] == "info":
            if args[1] in shell.capabilities:
                print(shell.capabilities[args[1]].description)
            else:
                eprint("Capability not found.")
        else:
            eprint("Unrecognized parameter.")
