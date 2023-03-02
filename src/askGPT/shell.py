import cmd
import shlex
import shutil 
from .tools   import eprint, sanitizeName
import toml
import os
import sys
import rich
from pathlib import Path
from rich import print
from rich.text import Text
from rich.style import Style
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.markdown import Markdown
from .tools import strToValue
from rich.console import Console
import click
from filecmp import cmp
import subprocess

danger_style = Style(color="red", blink=False, bold=True)
attention_style = Style(color="yellow", blink=False, bold=True)
ok_style = Style(color="green", blink=False, bold=False)
console = Console()


"""Here we will define the class Shell which is a child of cmd.cmd which will allow us to run all the commands interactively such as query, config, edit."""
class Shell(cmd.Cmd):
    def __init__(self, config) -> None:
        super().__init__()
        
        self.intro = "Welcome to askGPT. Type help or ? to list commands."
        self.doc_header = "Commands (type help <topic>):"
        self.misc_header = "Miscellaneous help topics:"
        self.undoc_header = "Undocumented commands:"
        self.ruler = "-"
        self._config = config
        self.commands = dict()
        self.lastResponse = None
        self._register_commands()
        self.conversation_parameters = {
            "subject": "test",
            "scenario": "ChatGPT",
            "model": "gpt-3.5-turbo",
            "defaultCommand": "query",
            "execute": False

        }
        if os.path.exists(os.path.join(self._config.settingsPath, "last.toml")):
            self.conversation_parameters.update(toml.load(os.path.join(self._config.settingsPath, "last.toml")))
        self.prompt = f"{self.conversation_parameters['scenario']}> "
        self.do_update("")
        

    def do_update(self,args):
        """replace the current scenarios files"""
        args = shlex.split(args)
        if self._config.progConfig["updateScenarios"] == False:
            eprint("Update is disabled in the config file")
            return
        if not cmp(os.path.join(self._config.data_path, "scenarios.json"), os.path.join(self._config.settingsPath, "scenarios.json")):
            if not Confirm.ask("New scenarios available.Would you like to replace the current ones?"):
                eprint("Scenarios files matched. No need to overwrite.")
                return 
            if Confirm.ask("Would you like to make a backup of the current one?"):
                shutil.copyfile(os.path.join(self._config.settingsPath, "scenarios.json"), os.path.join(self._config.settingsPath, "scenarios.json.bak"))
            shutil.copyfile(os.path.join(self._config.data_path, "scenarios.json"), os.path.join(self._config.settingsPath, "scenarios.json"))
            eprint("Scenarios updated, you need to restart to load the new scenario file")
            return 
            

    def do_clone(self,args):
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
            if new_subject in self._config.get_list():
                eprint(f"Subject {new_subject} already exists")
                return
            current_subject = self.conversation_parameters["subject"]
            filename = os.path.join(self._config.conversations_path, f"{current_subject}{self._config.fileExtention}")
            with open(filename, "r") as r:
                text = r.read()
            filename = os.path.join(self._config.conversations_path, f"{new_subject}{self._config.fileExtention}")
            with open(filename, "w") as w:
                w.write(text)
            self.conversation_parameters["subject"] = new_subject
            print(f"Conversation {new_subject} created")


    def do_recap(self, args):
        """prints the text from the conversation file using the subject.ai.txt """
        args = shlex.split(args)
        if len(args) == 0:
            subject = self.conversation_parameters["subject"]
        else:
            subject = args[0]
            if subject not in self._config.get_list():
                eprint(f"Subject {subject} not found")
                return
        filename = os.path.join(self._config.conversations_path, f"{subject}{self._config.fileExtention}")
        if os.path.isfile(filename):
            with open(filename, "r") as f:
                print(f.read())
        else:
            eprint(f"File {filename} not found")

    """capiche
    command that will submit the chat plus the Human entry: If you understand say so.
    """
    def do_capiche(self, args):
        """capiche will submit the chat plus the Human entry: If you understand say so."""
        args = shlex.split(args)
        capiche = "If you understand the task, don't do it, just respond 'Capiche!' and nothing else."
        if len(args) == 0:
            self.do_query(capiche)
        else:
            args.append(".")
            args.append(f"{capiche}")
            self.do_query(" ".join(args))


    """Show the greeting and the conversation prompt used to precondition the scenario"""
    def do_intro(self, args):
        """if args is one of the scenarios, print the greeting of that scenario"""
        args = shlex.split(args)
        scenario = self.conversation_parameters["scenario"]
        if len(args) != 0:
            scenario = args[0]
            """print current scenario from conversation_parameters"""
        if scenario in self._config.scenarios:    
            print(f"system: {self._config.scenarios[scenario]['greetings']}")
            for p in self._config.scenarios[scenario]['conversation']:
                prompt = self._config.progConfig["userPrompt"] if p['user'] == "userPrompt" else self._config.progConfig["aiPrompt"]
                print(f"{prompt}: {p['prompt']}")
                
        else:
            eprint(f"Scenario {scenario} not found")

    def do_greetings(self, args):
        """if args is one of the scenarios, print the greeting of that scenario"""
        args = shlex.split(args)
        if len(args) == 0:
            """print current scenario from conversation_parameters"""
            scenario = self.conversation_parameters["scenario"]
            print(f"system: {self._config.scenarios[scenario]['greetings']}")
            return
        scenario = args[0]
        if scenario in self._config.scenarios:
            print(f"system: {self._config.scenarios[scenario]['greetings']}")
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

    """Write function similar to do_exec but that it is able to save the output from the command being executed."""
    def execStdout(command: list):
        result = subprocess.run([command], stdout=subprocess.PIPE)
        return result.stdout.decode('utf-8')

    def do_set(self,args):
        """Set conversation_parameters checking that the keys exist and that the values are valid"""
        args = shlex.split(args)
        if len(args) == 0:
            for key in self.conversation_parameters:
                print(f"{key} = {self.conversation_parameters[key]}")
            return
        if len(args) == 2:
            key = args[0]
            val = strToValue(args[1])
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
            elif key in self._config.progConfig:
                if key == "fileExtention":
                    if val[0] != ".":
                        val = "." + val
                self._config.progConfig[key] = strToValue(val)
                self._config.saveConfig()
            else:
                eprint("Key not found")
        else:
            eprint("Wrong number of arguments")
    
    def do_version(self,args):
        """Print the version of the program"""
        print(f"Version {self._config.version}")

    def _register_commands(self):
        """Register all the commands."""
        for name in dir(self):
            if name.startswith("do_"):
                self.commands[name[3:]] = getattr(self, name)

        
    def do_credentials(self, args):
        """credentials: show the credentials."""
        if self._config.credentials:
            print(self._config.credentials)
            if not Confirm.ask("Would you like to replace them?"):
                return
        """ask if to replace"""
        api_key = ""
        while(api_key == ""):
            api_key = Prompt.ask("Enter your openai API key",default="" if self._config.credentials is None else self._config.credentials.split(":")[0])
        
        api_organization=""
        while(api_organization == ""):
            api_organization = Prompt.ask("Enter your openai otganization",default="" if self._config.credentials is None else self._config.credentials.split(":")[1])
        self._config.credentials = f"{api_key}:{api_organization}"

        """if yes, ask for the new credentials"""
        self._config.chat.saveLicense(api_key, api_organization)
        self._config.chat.loadLicense()
        """if no, do nothing"""

    def do_delete(self, args):
        """delete: delete a subject."""
        args = shlex.split(args)
        if len(args) == 0:
            subject = self.conversation_parameters["subject"]
        else:
            subject = sanitizeName(args[0])
        if subject in self._config.get_list():
            os.remove(os.path.join(self._config.conversations_path, subject + self._config.fileExtention)) 
        else:
            eprint("Subject not found")

    def do_edit(self, args):
        args = shlex.split(args)
        """edit: edit a subject."""
        if len(args) == 0:
            subject = self.conversation_parameters["subject"]
        else:
            subject = sanitizeName(args[0])
        if subject in self._config.get_list():
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
            if args[0] == "save":
                self._config.saveConfig()
                return
            eprint("No value provided.")
            return
        elif len(args) == 2:
            value = strToValue(args[1])
            if args[0] in self._config.progConfig:
                self._config.progConfig[args[0]] = value
            elif args[0] in self._config.conversation_parameters:
                self._config.updateParameter(args[0], value)
        else:
            eprint("Unrecognized parameter.")
        if not clean:
            pass
            
    

    def do_submit(self, args):
        """submit: submit a subject."""
        if self._config.has.get("license", False):
            with console.status("waiting for response ...", spinner="dots"):
                response = self._config.chat.submitDialog(self.conversation_parameters["subject"], self.conversation_parameters["scenario"])
                if response:
                        text = Text(response)
                        text.stylize("bold magenta")
                        console.print(text)
                        """save to file"""
                        with open(os.path.join(self._config.conversations_path, self.conversation_parameters["subject"] + self._config.fileExtention), "a") as f:
                            if self.conversation_parameters.get("execute", False):
                                editPrompt = click.prompt(f"{response}\nedit command? [y/n]", type=click.Choice(["y", "n"]), default="n")
                                if editPrompt == "y":
                                    edited = click.edit(response)
                                    if edited:
                                        response = edited
                                doExec = click.prompt(f"{response}\nExecute command? [y/n]", type=click.Choice(["y", "n"]), default="y")
                                """execute the command in the terminal and edit the response before saving it."""
                                if doExec == "y":
                                    result  = subprocess.run(response, stdout=subprocess.PIPE, shell=True, stderr=subprocess.STDOUT)
                                    result = result.stdout.decode("utf-8")
                                    print(result)
                                    saveOutput = click.prompt(f"save output? [Y/e/n]", type=click.Choice(["y", "e", "n"]), default="y")
                                    if saveOutput == "e":
                                        edited = click.edit(result)
                                        if edited:
                                            result = edited
                                    if saveOutput != "n":
                                        f.write(f"{self._config.progConfig['aiPrompt']}: {response}")
                                        f.write("\n")
                                        f.write(f"self._config.progConfig['userPrompt']: {str(result)}")
                                        f.write("\n")
                                else:
                                    f.write(f"{self._config.progConfig['aiPrompt']}: {response}")
                                    f.write("\n")
                            else:
                                f.write(f"{self._config.progConfig['aiPrompt']}: {response}")
                                f.write("\n")
                                        
            self._config.chat.loadLicense()
        return

    def do_continue(self, args):
        """This is in case we get an exception that we didn't protect ourselves from"""
        if args:
            eprint(args)
        else:
            eprint("An unknown error occured.")
        
    def do_query(self, enquiry):
        """Query the model with the given prompt."""
        """query: query the model with the given prompt.
         <prompt> """
        if not self._config.has.get("license", False):
            self._config.chat.loadLicense()
            return
        if self._config.has.get("license", False):
            response = None
            with console.status("waiting for response ...", spinner="dots"):
                response = self._config.chat.query(self.conversation_parameters["subject"], self.conversation_parameters["scenario"], enquiry)
            if response:
                text = Text(response)
                text.stylize("bold magenta")
                console.print(f"{text}\n")
                self.lastResponse = text
                """save to file"""
                with open(os.path.join(self._config.conversations_path, self.conversation_parameters["subject"] + self._config.fileExtention), "a") as f:
                        if self.conversation_parameters.get("execute", False):
                                editPrompt = click.prompt(f"edit command? [y/n]", type=click.Choice(["y", "n"]), default="n")
                                if editPrompt == "y":
                                    edited = click.edit(response)
                                    if edited:
                                        response = edited
                                doExec = click.prompt(f"{response}\nExecute command? [y/n]", type=click.Choice(["y", "n"]), default="y")
                                """execute the command in the terminal and edit the response before saving it."""
                                if doExec == "y":
                                    result  = subprocess.run(response, stdout=subprocess.PIPE, shell=True, stderr=subprocess.STDOUT)
                                    result = result.stdout.decode("utf-8")
                                    print(result)
                                    saveOutput = click.prompt(f"save output? [Y/e/n]", type=click.Choice(["y", "e", "n"]), default="y")
                                    if saveOutput == "e":
                                        edited = click.edit(result)
                                        if edited:
                                            result = edited
                                    if saveOutput != "n":
                                        f.write(f"{self._config.progConfig['userPrompt']}: {str(enquiry)}")
                                        f.write("\n")
                                        f.write(f"{self._config.progConfig['aiPrompt']}: {response}")
                                        f.write("\n")
                                        f.write(f"{self._config.progConfig['userPrompt']}: {str(result)}")
                                        f.write("\n")

                                else:
                                    f.write(f"{self._config.progConfig['userPrompt']}: {str(enquiry)}")
                                    f.write("\n")
                                    f.write(f"{self._config.progConfig['aiPrompt']}: {response}")
                                    f.write("\n")
                        else:
                            f.write(f"{self._config.progConfig['userPrompt']}: {str(enquiry)}")
                            f.write("\n")
                            f.write(f"{self._config.progConfig['aiPrompt']}: {response}")
                            f.write("\n")
                            
    def complete_recap(self,text, line, begidx, endidx):
        """complete_query: complete the query command."""
        if not text:
            completions = self._config.get_list()
        else:
            completions = [ f
                            for f in self._config.get_list()
                            if f.startswith(text)
                            ]
        return completions

    def complete_edit(self,text, line, begidx, endidx):
        """complete_query: complete the query command."""
        if not text:
            completions = self._config.get_list()
        else:
            completions = [ f
                            for f in self._config.get_list()
                            if f.startswith(text)
                            ]
        return completions

    def complete_man(self,text, line, begidx, endidx):
        """complete_query: complete the query command."""
        if not text:
            completions = list(self.commands.keys())
        else:
            completions = [ f
                            for f in self.commands.keys()
                            if f.startswith(text)
                            ]
        return completions

  
    def complete_config(self,text, line, begidx, endidx):
        """complete_query: complete the query command."""
        if not text:
            completions = list(self._config.progConfig.keys())
        else:
            completions = [ f
                            for f in self._config.progConfig.keys()
                            if f.startswith(text)
                            ]
        return completions

    def complete_show(self,text, line, begidx, endidx):
        """complete_query: complete the query command."""
        args = shlex.split(line)
        completions = None
        # print(f"{args}\n")
        if len(args) < 2:
            if not text:
                completions = list(["config", "scenarios", "subject", "subjects"] )
            else:
                completions = [ f
                                for f in list(["config", "scenarios", "subject", "subjects"] )
                                if f.startswith(args[-1])
                                ]
        elif len(args) == 2:
            if args[1] == "scenario":
                completions = list(self._config.scenarios.keys())
            else:
                completions = [ f
                                for f in list(["config", "scenarios", "scenario", "subjects"] )
                                if f.startswith(args[-1])
                                ]
        elif len(args) == 3:
            completions = [ f
                            for f in list(self._config.scenarios.keys())
                            if f.startswith(args[2])
                            ]
        return completions

    def complete_set(self,text, line, begidx, endidx):
        """complete_query: complete the query command."""
        # print("len: {}, spaces: {}\n".format(len(line), len(line.split(" "))))
        if  line.rstrip()  == "set":
            completions = list(self.conversation_parameters.keys())
            return completions
        elif len(line.split(" ")) == 2:
            completions = [ f
                            for f in self.conversation_parameters.keys()
                            if f.startswith(text)
                            ]
            return completions
        elif len(line.split(" ")) >  2:
            completions = line.rstrip().split(" ")[1]
            if completions == "scenario":
                completions = [
                    f
                    for f in list(self._config.scenarios.keys())
                    if f.startswith(text) 
                ]
                return completions
            elif completions == "subject":
                completions = [
                    f
                    for f in list(self._config.get_list())
                    if f.startswith(text) 
                ]
                return completions
            elif completions == "model":
                completions = [
                    f
                    for f in list(self._config.chat.listModels())
                    if f.startswith(text) 
                ]
                return completions
            elif completions == "defaulCommand":
                completion =  [
                    f
                    for f in list(self.commands.keys())
                    if f.startswith(text)
                ]
                return completions


    def complete_delete(self,text, line, begidx, endidx):
        """complete_query: complete the query command."""
        if not text:
            completions = self._config.get_list()
        else:
            completions = [ f
                            for f in self._config.get_list()
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
                for scenario in sorted(self._config.scenarios.keys()):
                    print(scenario)
                return
            elif args[0] == "subjects":
                print("Current subjects:")
                for subject in self._config.get_list():
                    print(subject)
                return
            elif args[0] == "models":
                if self._config.has.get("license", False):
                    print("Current models:")
                    for val  in self._config.chat.listModels():
                        print(val)
                else: 
                    self._config.chat.loadLicense()
                return
            else:
                if self.conversation_parameters.get("defaultCommand", "") == "query":
                    self.do_query(arg)
                else:
                    eprint("Unrecognized parameter.")
                return
        elif len(args) == 2:
            if args[0] == "scenario":
                scenario = sanitizeName(args[1])
                scenario = self._config.scenarios.get(scenario)
                if scenario is not None:
                    print("Greetings:")
                    print(scenario.get("greetings", ""))
                    for prompt in scenario["conversation"]:
                        print("{} {}".format(scenario.get(prompt["user"], self._config.progConfig.get(prompt["user"])), prompt["prompt"]))
        else:
                if self.conversation_parameters.get("defaultCommand", "") == "query":
                    self.do_query(arg)
                    return
                else:
                    eprint("Unrecognized parameter.")
                    return
            
    def saveSession(self):
        """EOF: exit the shell."""
        """ save the current parameters in a toml file to be loaded in the next session"""
        with open(os.path.join(os.path.join(self._config.settingsPath, "last.toml")), "w") as f:
            toml.dump(self.conversation_parameters, f)


    def do_EOF(self, arg):
        self.saveSession()
        return True

    def do_exit(self, arg):
        """exit: exit the shell."""
        self.saveSession()
        return True

    def do_quit(self, arg):
        """quit: exit the shell."""
        self.saveSession()
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
        if line == "!!":
            # take the last response from AI and esecute it. This is meanly useful when using the sharedTermninal scenario. We want to capture the output and feed it into the conversation as the user prompt.
            if self.lastResponse:
                self.do_exec(self.lastResponse)

            pass
        elif line.startswith("!"):
            self.do_exec(line[1:])
        elif self.conversation_parameters.get("defaultCommand","query") == "query":

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


    def do_man(self, line):
        """ when passed the name of a command it will pint an extensive explanation of the command by loading a markup file from data/"""
        if line:
            command = self.parseline(line)
            if command[0] in self.commands:
                command = command[0]
            else:
                command = None
        else:
            command = None
        if command:
            try:
                with open(os.path.join(os.path.join(self._config.data_path), "docs", "man_" + command + ".md"), "r") as f:
                    print( Markdown(f.read()))
            except FileNotFoundError:
                print("No manual entry for", command)   

    
