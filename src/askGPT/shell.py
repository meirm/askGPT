import cmd

"""Here we will define the class Shell which is a child of cmd.cmd which will allow us to run all the commands interactively such as query, config, edit."""
class Shell(cmd.Cmd):
    def __init__(self, config) -> None:
        super().__init__()
        self.prompt = "askGPT> "
        self.intro = "Welcome to askGPT. Type help or ? to list commands."
        self.doc_header = "Commands (type help <topic>):"
        self.misc_header = "Miscellaneous help topics:"
        self.undoc_header = "Undocumented commands:"
        self.ruler = "-"
        self._config = config
        self.commands = dict()
        self._register_commands()

    def _register_commands(self):
        """Register all the commands."""
        for name in dir(self):
            if name.startswith("do_"):
                self.commands[name[3:]] = getattr(self, name)

        
    def do_query(self, arg):
        """query: query the model with the given prompt."""
        if not self._config:
            print("You need to configure the model first.")
            return
        print("querying the model with the given prompt...")
        print("TODO: implement the query function.")

    def do_config(self, arg):
        """config: configure the model."""
        print("configuring the model...")
        print("TODO: implement the config function.")

    def do_edit(self, arg):
        """edit: edit the config file."""
        print("editing the config file...")
        print("TODO: implement the edit function.")

    def do_EOF(self, arg):
        """EOF: exit the shell."""
        return True

    def do_exit(self, arg):
        """exit: exit the shell."""
        return True

    def do_quit(self, arg):
        """quit: exit the shell."""
        return True
    
    def do_help(self, arg):
        """help: show the help message."""
        if arg:
            try:
                print(getattr(self, 'do_' + arg).__doc__)
            except AttributeError:
                print(self.nohelp % (arg,))
        else:
            names = self.commands.keys()
            cmds_doc = []
            cmds_undoc = []
            cmds_misc = []
            for name in names:
                if name[:5] == 'help_':
                    cmds_misc.append(name[5:])
                elif getattr(self, 'do_' + name).__doc__:
                    cmds_doc.append(name)
                else:
                    cmds_undoc.append(name)
            self.print_topics(self.doc_header, cmds_doc, 15, 80)
            self.print_topics(self.misc_header, cmds_misc, 15, 80)
            self.print_topics(self.undoc_header, cmds_undoc, 15, 80)

    def emptyline(self):
        """emptyline: do nothing."""
        pass

    def default(self, line):
        """default: print the error message."""
        print("Unrecognized command:", line)

    def postloop(self):
        """postloop: print the exit message."""
        print("Exiting askGPT.")

    def precmd(self, line):
        """precmd: print the command."""
        print("Command:", line)
        return line

    def postcmd(self, stop, line):
        """postcmd: print the result."""
        print("Result:", stop)
        return stop

    
