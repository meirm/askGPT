
import os
import shlex
from askGPT.tools import eprint
from filecmp import cmp
from ..tools   import eprint, sanitizeName
from rich.prompt import Prompt, Confirm

def do_credentials(shell, args):
    """credentials: show the credentials."""
    if shell._config.credentials:
        print(shell._config.credentials)
        if not Confirm.ask("Would you like to replace them?"):
            return
    """ask if to replace"""
    api_key = ""
    while(api_key == ""):
        api_key = Prompt.ask("Enter your openai API key",default="" if shell._config.credentials is None else shell._config.credentials.split(":")[0])
    shell._config.credentials = f"{api_key}"

    """if yes, ask for the new credentials"""
    shell._config.chat.saveLicense(api_key)
    shell._config.chat.loadLicense()
    """if no, do nothing"""