

def do_me(shell, args):
    import os
    from askGPT.tools import eprint    
    filename = os.path.join(shell._config.settingsPath, shell._config.progConfig["memoryFile"])
    # Check for existence of file and create it if not there
    if not os.path.exists(filename):
        open(filename, 'w').close()
    else:
        pass
    if len(args) == 0:
        eprint("/me <show|add|del>")
    elif args == "show":
        try:
            with open(filename, 'r') as filehandle:
                lines = filehandle.readlines()
                print("\n".join([line.strip('\n') for line in lines]))
        except Exception as e:
            shell.print_exception(e)
    elif args.startswith("add"):
            text = args[4:]
            try:
                with open(filename, 'a+') as filehandle:
                    filehandle.write(f'\n{text}')
            except Exception as e:
                shell.print_exception(e)
    elif args.startswith("del"):
        text = args[4:]
        eprint(f"deleting line starting with:\n{text} = ")
        try:
            with open(filename, 'r') as filehandle:
                lines = filehandle.readlines()
                # we will filter out lines starting with arg[1] = ...
                filtered_lines = [line for line in lines if line.startswith(f"{text} = ") is False]
            with open(filename, 'w') as filehandle:
                filehandle.writelines(filtered_lines)
        except Exception as e:
            shell.print_exception(e)
    else:
        eprint(f"Invalid arguments: {args}")