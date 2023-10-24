import os
import shlex
from askGPT.tools import eprint

def do_exec(shell,args):
        """Execute a the rest of the line in a bash shell and print the output"""
        args = shlex.split(args)
        if len(args) == 0:
            eprint("No command provided")
            return
        command = " ".join(args)
        os.system(command)