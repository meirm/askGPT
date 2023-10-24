from askGPT.tools import eprint

def do_continue(shell, args):
    """This is in case we get an exception that we didn't protect ourselves from"""
    if args:
        eprint(args)
    else:
        eprint("An unknown error occured.")