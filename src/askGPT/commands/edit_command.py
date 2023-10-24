import shlex
from askGPT.tools import sanitizeName, eprint

def do_edit(shell, args):
        args = shlex.split(args)
        """edit: edit a subject."""
        if len(args) == 0:
            subject = shell.conversation_parameters["subject"]
        else:
            subject = sanitizeName(args[0])
        if subject in shell._config.get_list():
            shell._config.chat.editDialog(subject)
        else:
            eprint("Subject not found")

def complete_edit(shell,text, line, begidx, endidx):
    """complete_query: complete the query command."""
    if not text:
        completions = shell._config.get_list()
    else:
        completions = [ f
                        for f in shell._config.get_list()
                        if f.startswith(text)
                        ]
    return completions