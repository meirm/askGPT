#!/usr/bin/env python
"""
Genie is a simple command line tool for interacting with OpenAI's API.

Usage:
    genie.py query --subject <subject> --enquiry <enquiry>
    genie.py list
    genie.py show --subject <subject>
    genie.py delete --subject <subject>
    genie.py delete --all
    genie.py config
    genie.py credentials

    
Options:
    -h --help     Show this screen.
    --version     Show version.
    --subject     Subject of the conversation
    --enquiry     Your question
    --all         Delete all archived conversations
    
Author: Meir Michanie <meirm@riunx.com>
License: MIT
Date: 2023/01/23
"""
__version__ = "0.2.0"

import os
import openai
import click
from rich import print
from pathlib import Path
import json

"""
Load the configuration file from ~/.genie/config"""
if os.path.isfile(os.path.join(os.getenv("HOME"), ".genie", "config")):
    with open(os.path.join(os.getenv("HOME"), ".genie", "config"), "r") as f:
        progConfig = dict()
        for line in f.readline():
            if line.startswith("#") or len(line) < 3:
                continue
            progConfig[line.split("=")[0]] = line.split("=")[1]
else:
    progConfig = dict()

progConfig["userPrompt"] = progConfig.get("userPrompt"," Human: ")
progConfig["aiPrompt"] = progConfig.get("aiPrompt"," AI: ")
progConfig["maxTokens"] = progConfig.get("maxTokens","150")
progConfig["engine"] = progConfig.get("engine","text-davinci-003")
progConfig["temperature"] = progConfig.get("temperature","0.0")

settingsPath=os.path.join(os.getenv("HOME"), ".genie")

conversations_path=os.path.join(settingsPath, "conversations")
Path(conversations_path).mkdir(parents=True, exist_ok=True)
fileExtention=".ai.txt"

# Load your API key from an environment variable or secret management service
if os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_ORGANIZATION"):
    openai.api_key = os.getenv("OPENAI_API_KEY")
    openai.organization = os.getenv("OPENAI_ORGANIZATION")
else:
    if os.path.isfile(os.path.join(settingsPath, "credentials")):
        with open(os.path.join(settingsPath, "credentials"), "r") as f:
            credentials = f.read()
            openai.api_key = credentials.split(":")[0]
            openai.organization = credentials.split(":")[1].strip()
    else:
        print("Please set OPENAI_API_KEY and OPENAI_ORGANIZATION environment variables.")
        print("Or create a file at ~/.genie/credentials with the following format:")
        print("OPENAI_API_KEY:OPENAI_ORGANIZATION")
        exit(1)


"""
Sanitize the name of the conversation to be saved."""
def sanitizeName(name):
    return name.replace(" ", "_").replace("/", "_")

@click.group()
@click.version_option(__version__)
@click.pass_context
def cli(ctx):
    pass

"""
Load json from file"""
def load_json(file):
    with open(file, "r") as f:
        try:
            return json.load(f)
        except:
            return dict()


personas = load_json(os.path.join(settingsPath,"personas.json"))


"""List the available personas"""
@cli.command()
def list_personas():
    for persona in personas.keys():
        print(persona)

"""
Change config values"""
@cli.command()
@click.option("--user-prompt", prompt="User prompt", default=progConfig["userPrompt"], help="User prompt")
@click.option("--ai-prompt", prompt="AI prompt", default=progConfig["aiPrompt"], help="AI prompt")
@click.option("--max-tokens", prompt="Max tokens", type=int, default=progConfig["maxTokens"], help="Max tokens")
@click.option("--engine", default=progConfig["engine"], help="Set alternative engine")
@click.option("--temperature", default=progConfig["temperature"], help="Set alternative temperature")
def config(user_prompt, ai_prompt, max_tokens,engine, temperature):
    progConfig["userPrompt"] = user_prompt
    progConfig["aiPrompt"] = ai_prompt
    progConfig["maxTokens"] = max_tokens
    progConfig["engine"] = engine
    progConfig["temperature"] = temperature
    show_config()
    with open(os.path.join(settingsPath, "config"), "w") as f:
        for key in progConfig:
            f.write(key + "=" + str(progConfig[key]) + "\n")
        

"""Show the current configuration"""
def show_config():
    print("Current configuration:")
    for key in progConfig:
        print(key + "=" + str(progConfig[key]))
    

"""
Save the API keys to query OpenAI"""
@cli.command()
def credentials():
    print("Welcome to Genie")
    print("Please provide your OpenAI API key and organization")
    print("You can find these values at https://beta.openai.com/account/api-keys")
    openai.api_key = input("API_KEY:")
    openai.organization = input("ORGANIZATION:")
    with open(os.path.join(settingsPath, "credentials"), "w") as f:
        f.write(openai.api_key + ":" + openai.organization)
    print("Genie is now ready to use")


"""
Print the previous conversations saved by genie."""
@cli.command()
def List():
    print(get_list())

"""
list the previous conversations saved by genie."""
def get_list():
    conv_array = list()
    for line in os.listdir(conversations_path):
        if (not line.startswith("."))  and line.endswith(fileExtention) and (os.path.isfile(os.path.join(conversations_path,line))):
            conv_array.append(line.replace(fileExtention,""))
    return conv_array

"""
Delete the previous conversations saved by genie"""
@cli.command()
@click.option("--subject", prompt="Subject", help="Subject of the conversation")
@click.option("--all/--single",  default=False, help="Delete all archived conversations")
def delete(subject, all):
    if all:
        for subject in get_list():
            os.remove(os.path.join(conversations_path, subject))
    elif subject and os.path.isfile(os.path.join(conversations_path,sanitizeName(subject) + fileExtention)):
        os.remove(os.path.join(conversations_path, subject + fileExtention))
    else:
        print("No chat history with that subject")
        return

"""
Show the previous conversations saved by genie"""
@cli.command()
@click.option("--subject", prompt="Subject", help="Subject of the conversation")
def show(subject):
    if subject:
        with open(os.path.join(conversations_path, sanitizeName(subject) + fileExtention), "r") as f:
            chat = f.read()
            print(chat)
    else:
        print("No subject provided")
        return
        
"""
Query the OpenAI API with the provided subject and enquiry"""
@cli.command()
@click.option("--subject", prompt="Subject", help="Subject of the conversation")
@click.option("--enquiry", prompt="Enquiry", help="Your question")
@click.option("--persona", prompt="Persona", default="Neutral", help="Subject of the conversation")
@click.option("--engine", default=progConfig["engine"], help="Set alternative engine")
@click.option("--temperature", default=progConfig["temperature"], help="Set alternative temperature")
@click.option("--quiet/--verbose", default=True, help="Show verbose output or just the answer")
def query(subject, enquiry, persona,engine, temperature, quiet):
    enquiry = progConfig["userPrompt"] + enquiry
    if subject:
        with open(os.path.join(conversations_path, sanitizeName(subject) + fileExtention), "a") as f:
            pass
        with open(os.path.join(conversations_path, sanitizeName(subject) + fileExtention), "r") as f:
            chatRaw = f.read()
            if persona != "Neutral":
                chat = progConfig["aiPrompt"] +  personas[persona]["greetings"] + "\n" + chatRaw  + enquiry + "\n" + progConfig["aiPrompt"]
            else:
                chat = chatRaw + enquiry + "\n" + progConfig["aiPrompt"]
            response = openai.Completion.create(
                engine=engine,
                prompt=chat,
                temperature=float(temperature),
                max_tokens=int(progConfig["maxTokens"]),
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0.6,
                stop=[ # "\n",
                 progConfig["userPrompt"], progConfig["aiPrompt"]],
            )
            ai = response.choices[0].text
            if ai.startswith("\n\n"):
                ai = ai[2:]
            if quiet:
                print(ai)
            else:
                print(chat + ai)
            f.close()
        with open(os.path.join(conversations_path, sanitizeName(subject) + fileExtention), "a") as f:
            f.write(enquiry) 
            f.write("\n")
            f.write(progConfig["aiPrompt"] + ai)
            f.write("\n")
            f.close()
    else:
        print("No subject provided")
        return
    
    #  print("The genie is sleeping. [bold red]Next time, rub the lamp first.[/bold red]")

