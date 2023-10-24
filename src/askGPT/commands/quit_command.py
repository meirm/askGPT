def do_quit(shell, arg):
    """quit: exit the shell."""
    shell.saveSession()
    return True