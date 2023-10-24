import shlex
"""capiche
command that will submit the chat plus the Human entry: If you understand say so.
"""
def do_capiche(shell, args):
    """capiche will submit the chat plus the Human entry: If you understand say so."""
    args = shlex.split(args)
    capiche = "If you understand the task, don't do it, just respond 'Capiche!' and nothing else."
    if len(args) == 0:
        shell.do_query(capiche)
    else:
        args.append(".")
        args.append(f"{capiche}")
        shell.do_query(" ".join(args))