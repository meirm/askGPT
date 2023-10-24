import shlex
from askGPT.tools   import eprint

"""Show the greeting and the conversation prompt used to precondition the scenario"""
def do_intro(shell, args):
    """if args is one of the scenarios, print the greeting of that scenario"""
    args = shlex.split(args)
    scenario = shell.conversation_parameters["scenario"]
    if len(args) != 0:
        scenario = args[0]
        """print current scenario from conversation_parameters"""
    if scenario in shell._config.scenarios:    
        print(f"system: {shell._config.scenarios[scenario]['greetings']}")
        for p in shell._config.scenarios[scenario]['conversation']:
            print(f"{p['role']}: {p['content']}")
            
    else:
        eprint(f"Scenario {scenario} not found")