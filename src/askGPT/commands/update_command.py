import shlex
import os
from filecmp import cmp
from ..tools   import eprint, sanitizeName
from rich.prompt import Prompt, Confirm
import shutil

def do_update(shell,args):
    """replace the current scenarios files"""
    args = shlex.split(args)
    if shell._config.progConfig["updateScenarios"] == False:
        eprint("Update is disabled in the config file")
        return
    if not cmp(os.path.join(shell._config.data_path, "scenarios.json"), os.path.join(shell._config.settingsPath, "scenarios.json")):
        if not Confirm.ask("New scenarios available.Would you like to replace the current ones?"):
            eprint("Scenarios files matched. No need to overwrite.")
            return 
        if Confirm.ask("Would you like to make a backup of the current one?"):
            shutil.copyfile(os.path.join(shell._config.settingsPath, "scenarios.json"), os.path.join(shell._config.settingsPath, "scenarios.json.bak"))
        shutil.copyfile(os.path.join(shell._config.data_path, "scenarios.json"), os.path.join(shell._config.settingsPath, "scenarios.json"))
        eprint("Scenarios updated, you need to restart to load the new scenario file")
        return 