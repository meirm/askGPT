import cmd
import shlex 
from .tools   import eprint, sanitizeName
import toml
import os
import sys
import rich
from rich import print
from rich.text import Text
from rich.style import Style
danger_style = Style(color="red", blink=False, bold=True)
attention_style = Style(color="yellow", blink=False, bold=True)
ok_style = Style(color="green", blink=False, bold=False)
from rich.console import Console
console = Console()

"""Here we will define the class Shell which is a child of cmd.cmd which will allow us to run all the commands interactively such as query, config, edit."""
class Shell(cmd.Cmd):
    def __init__(self, config) -> None:
        super().__init__()
        self.prompt = "Neutral> "
        self.intro = "Welcome to askGPT. Type help or ? to list commands."
        self.doc_header = "Commands (type help <topic>):"
        self.misc_header = "Miscellaneous help topics:"
        self.undoc_header = "Undocumented commands:"
        self.ruler = "-"
        self._config = config
        self.commands = dict()
        self._register_commands()
        self.conversation_parameters = {
            "subject": "test",
            "scenario": "Neutral",
            "model": "text-davinci-003",
            "defaultCommand": "query"

        }

    def do_greetings(self, args):
        """if args is one of the scenarios, print the greeting of that scenario"""
        args = shlex.split(args)
        if len(args) == 0:
            """print current scenario from conversation_parameters"""
            scenario = self.conversation_parameters["scenario"]
            print(self._config.scenarios[scenario]["greetings"])
            return
        scenario = args[0]
        if scenario in self._config.scenarios:
            print(self._config.scenarios[scenario]["greetings"])
        else:
            eprint(f"Scenario {scenario} not found")

    def do_exec(self,args):
        """Execute a the rest of the line in a bash shell and print the output"""
        args = shlex.split(args)
        if len(args) == 0:
            eprint("No command provided")
            return
        command = " ".join(args)
        os.system(command)


    def do_set(self,args):
        """Set conversation_parameters checking that the keys exist and that the values are valid"""
        args = shlex.split(args)
        if len(args) == 0:
            for key in self.conversation_parameters:
                print(f"{key} = {self.conversation_parameters[key]}")
            return
        if len(args) == 2:
            key = args[0]
            val = args[1]
            if key in self.conversation_parameters:
                if key == "scenario":
                    if val in self._config.scenarios:
                        self.conversation_parameters[key] = val
                        self.prompt = f"{val}> "
                    else:
                        eprint("Scenario not found")
                elif key == "model":
                    if val  in self._config.chat.listModels():
                        self.conversation_parameters[key] = val
                    else:
                        eprint("Model not found")
                else:
                    self.conversation_parameters[key] = val
            else:
                eprint("Key not found")
        else:
            eprint("Wrong number of arguments")
    
    def _register_commands(self):
        """Register all the commands."""
        for name in dir(self):
            if name.startswith("do_"):
                self.commands[name[3:]] = getattr(self, name)

        
    def do_credentials(self):
        """credentials: show the credentials."""
        print(self._config.credentials)
        """ask if to replace"""
        """if yes, ask for the new credentials"""
        """if no, do nothing"""

    def do_delete(self, subject):
        """delete: delete a subject."""
        subject = sanitizeName(subject)
        if subject in self._config.subjects:
            self._config.subjects.remove(subject)
            os.remove(os.path.join(self._config.conversations_path, subject + self._config.fileExtention))
            
        else:
            eprint("Subject not found")

    def do_edit(self, subject):
        """edit: edit a subject."""
        subject = sanitizeName(subject)
        if subject in self._config.subjects:
            self._config.chat.editDialog(subject)
        else:
            eprint("Subject not found")

    def do_config(self, args):
        """needed two parameters, the first one is the key and the second one is the value"""
        args = shlex.split(args)
        clean = True
        if len(args) == 0:
            self._config.printConfig()
            return
        elif len(args) == 1:
            if args[1] == "save":
                self._config.saveConfig()
                return
            eprint("No value provided.")
            return
        elif len(args) == 2:
            self._config.updateParameter(args[0], args[1])
        else:
            eprint("Unrecognized parameter.")
        if not clean:
            pass
            
    

    def do_submit(self, args):
        """submit: submit a subject."""
        args = shlex.split(args)
        if len(args) == 0:
            eprint("Submit a subject.")
            return
        elif len(args) > 0:
            subject = sanitizeName(args[0])
            scenario = args[1]
            if subject not in self._config.subjects:
                eprint("Subject not found")
                return
            else:
                """submit: submit a subject."""
                self._config.chat.submitDialog(subject, scenario)
                return
        else:
            eprint("Unrecognized parameter.")
            return

    def do_query(self, enquiry, max_tokens: int = 150, temperature: float = 0.9, top_p: float = 1, frequency_penalty: float = 0, presence_penalty: float = 0, stop: list = ["\n", " Human:", " AI:"]):
        """Query the model with the given prompt."""
        """query: query the model with the given prompt.
         <prompt> """
        if not self._config:
            print("You need to configure the model first.")
            return
        response = self._config.chat.query(self.conversation_parameters["subject"], self.conversation_parameters["scenario"], enquiry)
        text = Text(response["choices"][0]["text"])
        text.stylize("bold magenta")
        console.print(text)
        """Query the model with the given prompt."""

    def complete_query(self,text, line, begidx, endidx):
        """complete_query: complete the query command."""
        if not text:
            completions = self._config.subjects[:]
        else:
            completions = [ f
                            for f in self._config.subjects
                            if f.startswith(text)
                            ]
        return completions

    def do_show(self, arg):
        """
        show: show the config|scenarios|models|subjects or the conversation inside a subject.
        <config|scenarios|models|subjects|subject <subject>>"""
        args = shlex.split(arg)
        if len(args) == 0:
            eprint("Show config|scenarios|models|subjects or the conversation inside a subject.")
            return
        elif len(args) == 1:
            if args[0] == "config":
                print("Current configuration:")
                print(toml.dumps(self._config.progConfig))
                return
            elif args[0] == "scenarios":
                print("Current scenarios:")
                for scenario in self._config.scenarios.keys():
                    print(scenario)
                return
            elif args[0] == "subjects":
                print("Current subjects:")
                for subject in self._config.get_list():
                    print(subject)
                return
            elif args[0] == "models":
                print("Current models:")
                for val  in self._config.chat.listModels():
                    print(val)
                return
            else:
                eprint("Unrecognized parameter.")
                return
        elif len(args) == 2:
            if args[0] == "subject":
                subject = sanitizeName(args[1])
                eprint("Show the conversation inside a subject.")
                if os.path.isfile(os.path.join(self._config.settingsPath, 'conversations', subject + self._config.fileExtention)):
                    with open(os.path.join(self._config.settingsPath, 'conversations', subject + self._config.fileExtention), 'r') as f:
                        print(f.read())
                        return
            else:
                eprint("Unrecognized parameter.")
                return
        else:
            eprint("Unrecognized parameter.")
            return
            
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
        if self.conversation_parameters.get("defaultCommand","query") == "query":
            self.do_query(line)
        else:
            """default: print the error message."""
            print("Unrecognized command:", line)

    def postloop(self):
        """postloop: print the exit message."""
        print("Exiting askGPT.")

    def precmd(self, line):
        """precmd: print the command."""
        #print("Command:", line)
        return line

    def postcmd(self, stop, line):
        """postcmd: print the result."""
        #print("Result:", stop)
        return stop

    
