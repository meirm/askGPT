import shlex
from askGPT.tools import sanitizeName, eprint, strToValue

def do_set(shell,args):
    """Set conversation_parameters checking that the keys exist and that the values are valid"""
    args = shlex.split(args)
    if len(args) == 0:
        for key in shell.conversation_parameters:
            print(f"{key} = {shell.conversation_parameters[key]}")
        return
    if len(args) == 2:
        key = args[0]
        val = strToValue(args[1])
        if key in shell.conversation_parameters:
            if key == "scenario":
                if val in shell._config.scenarios:
                    shell.conversation_parameters[key] = val
                    shell.prompt = f"{val}> "
                    shell._config.chat.greetings = {"role": "system", "content": shell._config.scenarios[val]["greetings"]}
                else:
                    eprint("Scenario not found")
            elif key == "model":
                if val  in shell._config.chat.listModels():
                    shell.conversation_parameters[key] = val
                else:
                    eprint("Model not found")
            else:
                shell.conversation_parameters[key] = val
        elif key in shell._config.progConfig:
            if key == "fileExtention":
                if val[0] != ".":
                    val = "." + val
            shell._config.progConfig[key] = strToValue(val)
            shell._config.saveConfig()
        else:
            eprint("Key not found")
    else:
        eprint("Wrong number of arguments")

def complete_set(shell,text, line, begidx, endidx):
    """complete_query: complete the query command."""
    # print("len: {}, spaces: {}\n".format(len(line), len(line.split(" "))))
    if  line.rstrip()  == "set":
        completions = list(shell.conversation_parameters.keys())
        return completions
    elif len(line.split(" ")) == 2:
        completions = [ f
                        for f in shell.conversation_parameters.keys()
                        if f.startswith(text)
                        ]
        return completions
    elif len(line.split(" ")) >  2:
        completions = line.rstrip().split(" ")[1]
        if completions == "scenario":
            completions = [
                f
                for f in list(shell._config.scenarios.keys())
                if f.startswith(text) 
            ]
            return completions
        elif completions == "subject":
            completions = [
                f
                for f in list(shell._config.get_list())
                if f.startswith(text) 
            ]
            return completions
        elif completions == "model":
            completions = [
                f
                for f in list(shell._config.chat.listModels())
                if f.startswith(text) 
            ]
            return completions
        elif completions == "defaulCommand":
            completion =  [
                f
                for f in list(shell.commands.keys())
                if f.startswith(text)
            ]
            return completions
