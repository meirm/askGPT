import shlex
from askGPT.tools   import eprint, sanitizeName
import toml

def do_show(shell, arg):
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
            print(toml.dumps(shell._config.progConfig))
            return
        elif args[0] == "scenarios":
            print("Current scenarios:")
            for scenario in sorted(shell._config.scenarios.keys()):
                print(scenario)
            return
        elif args[0] == "subjects":
            print("Current subjects:")
            for subject in shell._config.get_list():
                print(subject)
            return
        elif args[0] == "models":
            if shell._config.has.get("license", False):
                print("Current models:")
                for val  in shell._config.chat.listModels():
                    print(val)
            else: 
                shell._config.chat.loadLicense()
            return
        else:
            if shell.conversation_parameters.get("defaultCommand", "") == "query":
                shell.commands["query"](arg)
            else:
                eprint("Unrecognized parameter.")
            return
    elif len(args) == 2:
        if args[0] == "scenario":
            scenario = sanitizeName(args[1])
            scenario = shell._config.scenarios.get(scenario)
            if scenario is not None:
                print("Greetings:")
                print(scenario.get("greetings", ""))
                for prompt in scenario["conversation"]:
                    print("{} {}".format(scenario.get(prompt["role"], shell._config.progConfig.get(prompt["role"])), prompt["content"]))
    else:
            if shell.conversation_parameters.get("defaultCommand", "") == "query":
                shell.commands["query"](arg)
                return
            else:
                eprint("Unrecognized parameter.")
                return
        
def complete_show(shell,text, line, begidx, endidx):
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
            completions = list(shell._config.scenarios.keys())
        else:
            completions = [ f
                            for f in list(["config", "scenarios", "scenario", "subjects"] )
                            if f.startswith(args[-1])
                            ]
    elif len(args) == 3:
        completions = [ f
                        for f in list(shell._config.scenarios.keys())
                        if f.startswith(args[2])
                        ]
    return completions