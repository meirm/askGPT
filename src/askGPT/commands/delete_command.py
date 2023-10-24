import os
import shlex
from askGPT.tools import eprint, sanitizeName
def do_delete(shell, args):
    """delete: delete a subject."""
    args = shlex.split(args)
    if len(args) == 0:
        subject = shell.conversation_parameters["subject"]
    else:
        subject = sanitizeName(args[0])
    if subject in shell._config.get_list():
        os.remove(os.path.join(shell._config.conversations_path, subject + shell._config.fileExtention)) 
    else:
        eprint("Subject not found")
    shell._config.chat._chat_log = shell._config.chat._chat_log[:1]


def complete_delete(shell,text, line, begidx, endidx):
    """complete_query: complete the query command."""
    if not text:
        completions = shell._config.get_list()
    else:
        completions = [ f
                        for f in shell._config.get_list()
                        if f.startswith(text)
                        ]
    return completions