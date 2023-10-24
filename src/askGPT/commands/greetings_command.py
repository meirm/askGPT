import shlex
from askGPT.tools import eprint

def do_greetings(shell, args):
    """if args is one of the scenarios, print the greeting of that scenario"""
    args = shlex.split(args)
    if len(args) == 0:
        """print current scenario from conversation_parameters"""
        scenario = shell.conversation_parameters["scenario"]
        print(f"system: {shell._config.scenarios[scenario]['greetings']}")
        return
    scenario = args[0]
    if scenario in shell._config.scenarios:
        print(f"system: {shell._config.scenarios[scenario]['greetings']}")
    else:
        eprint(f"Scenario {scenario} not found")