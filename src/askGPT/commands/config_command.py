import shlex
from askGPT.tools import eprint, strToValue
def do_config(shell, args):
    """needed two parameters, the first one is the key and the second one is the value"""
    args = shlex.split(args)
    clean = True
    if len(args) == 0:
        shell._config.printConfig()
        return
    elif len(args) == 1:
        if args[0] == "save":
            shell._config.saveConfig()
            return
        eprint("No value provided.")
        return
    elif len(args) == 2:
        value = strToValue(args[1])
        if args[0] in shell._config.progConfig:
            shell._config.progConfig[args[0]] = value
        elif args[0] in shell._config.conversation_parameters:
            shell._config.updateParameter(args[0], value)
    else:
        eprint("Unrecognized parameter.")
    if not clean:
        pass

def complete_config(shell,text, line, begidx, endidx):
    """complete_query: complete the query command."""
    if not text:
        completions = list(shell._config.progConfig.keys())
    else:
        completions = [ f
                        for f in shell._config.progConfig.keys()
                        if f.startswith(text)
                        ]
    return completions