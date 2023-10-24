def do_help(shell, arg):
    """help: show the help message."""
    if arg:
        try:
            print(getattr(shell, 'do_' + arg).__doc__)
        except AttributeError:
            print(shell.nohelp % (arg,))
    else:
        names = shell.commands.keys()
        cmds_doc = []
        cmds_undoc = []
        cmds_misc = []
        for name in names:
            if name[:5] == 'help_':
                cmds_misc.append(name[5:])
            elif shell.commands[name].__doc__:
                cmds_doc.append(name)
            else:
                cmds_undoc.append(name)
        shell.print_topics(shell.doc_header, cmds_doc, 15, 80)
        shell.print_topics(shell.misc_header, cmds_misc, 15, 80)
        shell.print_topics(shell.undoc_header, cmds_undoc, 15, 80)