import shlex
import datetime
import os
from askGPT.tools import eprint, addMetadata
import requests
"""dream will help you generate images based on your prompt"""
def do_dream(shell, args):
    args = shlex.split(args)
    if len(args) == 0:
        eprint("No prompt provided.")
        return
    prompt = " ".join(args)
    """ show rich progress"""
    with shell.console.status("waiting for response ...", spinner="dots"):
        url = shell._config.chat.dream(prompt)
        if url:
            """ download the image into the conversation directory using the <subject>_<date>  add the prompt to the metadata of the image after saving. """
            subject = shell.conversation_parameters["subject"]
            date = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"{subject}_{date}.png"
            filepath = os.path.join(shell._config.conversations_path, filename)
            with open(filepath, "wb") as f:
                f.write(requests.get(url).content)
                addMetadata(filepath,  f"{prompt}")  
                print(f"Image saved at {filepath}")
        else:
            eprint("Error while generating the image.")
        
