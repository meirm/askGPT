def do_exit(shell, arg):
    """exit: exit the shell."""
    shell.saveSession()
    return True