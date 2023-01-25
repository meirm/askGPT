#!/usr/bin/env python
"""
askGPT is a simple command line tool for interacting with OpenAI's API.

Usage:
    askGPT disclaimer 
    askGPT query --subject <subject> --enquiry <enquiry>
    askGPT show <config|personas|subjects|engines> 
    askGPT show subject <subject>
    askGPT delete --subject <subject>
    askGPT delete --all
    askGPT config
    askGPT credentials

    
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
__title__ = 'askGPT'
__author__ = 'Meir Michanie'
__license__ = 'MIT'
__credits__ = ''
__version__ = "0.2.6"

import os
import openai
import click
from rich import print
from pathlib import Path
import json
import backoff
import time

disclaimer_note = "Disclaimer: The advice provided by askGPT is intended for informational and entertainment purposes only. It should not be used as a substitute for professional advice, and we cannot be held liable for any damages or losses arising from the use of the advice provided by askGPT."

# Calculate the delay based on your rate limit
rate_limit_per_minute = 20
delay = 60.0 / rate_limit_per_minute

def completions_with_backoff(delay_in_seconds: float = 1,**kwargs):
    """Delay a completion by a specified amount of time."""
    # Sleep for the delay
    time.sleep(delay_in_seconds)
    return openai.Completion.create(**kwargs)

"""
Load the configuration file from ~/.askGPT/config"""
if os.path.isfile(os.path.join(os.getenv("HOME"), ".askGPT", "config")):
    with open(os.path.join(os.getenv("HOME"), ".askGPT", "config"), "r") as f:
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
progConfig["topP"] = progConfig.get("topP","1")
progConfig["frequencyPenalty"] = progConfig.get("frequencyPenalty","0.0")
progConfig["presencePenalty"] = progConfig.get("presencePenalty","0.0")

settingsPath=os.path.join(os.getenv("HOME"), ".askGPT")

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
        print("Or create a file at ~/.askGPT/credentials with the following format:")
        print("OPENAI_API_KEY:OPENAI_ORGANIZATION")
        exit(1)


def sanitizeName(name):
    """
    Sanitize the name of the conversation to be saved."""
    return name.replace(" ", "_").replace("/", "_")


def load_json(file):
    """
Load json from file"""
    with open(file, "r") as f:
        try:
            return json.load(f)
        except:
            return dict()

"""if there is not a file named personas.json, create it ad add the Neutral persona"""
if not os.path.isfile(os.path.join(settingsPath,"personas.json")):
    with open(os.path.join(settingsPath,"personas.json"), "w") as f:
        f.write(json.dumps({"Neutral":{"name": "Neutral", "greetings": "I am a chatbot. How can I help you today?", "prompt": [], "max_tokens": 1000}}))
personas = load_json(os.path.join(settingsPath,"personas.json"))


@click.group()
@click.version_option(__version__)
@click.pass_context
def cli(ctx):
    pass

@cli.command()
def disclaimer():
    """Show the disclaimer"""
    print(disclaimer_note)


@cli.command()
@click.option("--user-prompt", prompt="User prompt", default=progConfig["userPrompt"], help="User prompt")
@click.option("--ai-prompt", prompt="AI prompt", default=progConfig["aiPrompt"], help="AI prompt")
@click.option("--max-tokens", prompt="Max tokens", type=int, default=progConfig["maxTokens"], help="Max tokens")
@click.option("--engine", default=progConfig["engine"], help="Set alternative engine")
@click.option("--temperature", default=progConfig["temperature"], help="Set alternative temperature")
@click.option("--top-p", default=progConfig["topP"], help="Set alternative topP")
@click.option("--frequency-penalty", default=progConfig["frequencyPenalty"], help="Set alternative frequencyPenalty")
@click.option("--presence-penalty", default=progConfig["presencePenalty"], help="Set alternative presencePenalty")
def config(user_prompt, ai_prompt, max_tokens,engine, temperature, top_p, frequency_penalty, presence_penalty):
    """
Change config values"""
    progConfig["userPrompt"] = user_prompt
    progConfig["aiPrompt"] = ai_prompt
    progConfig["maxTokens"] = max_tokens
    progConfig["engine"] = engine
    progConfig["temperature"] = temperature
    progConfig["topP"] = top_p
    progConfig["frequencyPenalty"] = frequency_penalty
    progConfig["presencePenalty"] = presence_penalty
    show('config')
    with open(os.path.join(settingsPath, "config"), "w") as f:
        for key in progConfig:
            f.write(key + "=" + str(progConfig[key]) + "\n")
        

@cli.command()
@click.argument("whatToShow", default="config")
@click.argument("subject", default="" )
def show(whattoshow, subject):
    """Show config|personas|subjects or the conversation inside a subject."""
    if subject == "":
        if whattoshow == "config":
            print("Current configuration:")
            for key in progConfig:
                print(key + "=" + str(progConfig[key]))
        elif whattoshow == "subjects":
            print("Current subjects:")
            for subject in get_list():
                    print(subject)
        elif whattoshow == 'personas':
            print("Current personas:")
            for persona in personas:
                print(persona)
        elif whattoshow == 'engines':
            print("Current engines:")
            for engine in openai.Engine.list():
                print(engine.id)
        else:
            print("Please specify what to show. Valid options are: config, subjects, personas, subject")
            print("In case of passing the option 'subject' please pass as well the subject's name")
    else:
        if os.path.isfile(os.path.join(settingsPath, 'conversations', subject + fileExtention)):
            with open(os.path.join(settingsPath, 'conversations', subject + fileExtention), 'r') as f:
                print(f.read())
        else:
            print("Subject not found")


@cli.command()
def credentials():
    """
Save the API keys to query OpenAI"""
    print("Welcome to askGPT")
    print("Please provide your OpenAI API key and organization")
    print("You can find these values at https://beta.openai.com/account/api-keys")
    openai.api_key = input("API_KEY:")
    openai.organization = input("ORGANIZATION:")
    with open(os.path.join(settingsPath, "credentials"), "w") as f:
        f.write(openai.api_key + ":" + openai.organization)
    print("askGPT is now ready to use")



def get_list():
    """
list the previous conversations saved by askGPT."""
    conv_array = list()
    for line in os.listdir(conversations_path):
        if (not line.startswith("."))  and line.endswith(fileExtention) and (os.path.isfile(os.path.join(conversations_path,line))):
            conv_array.append(line.replace(fileExtention,""))
    return conv_array


@cli.command()
@click.option("--subject", help="Subject of the conversation")
@click.option("--all/--single",  default=False, help="Delete all archived conversations")
def delete(subject, all):
    """
Delete the previous conversations saved by askGPT"""
    if all:
        for subject in get_list():
            os.remove(os.path.join(conversations_path, subject + fileExtention))
    elif subject and os.path.isfile(os.path.join(conversations_path,sanitizeName(subject) + fileExtention)):
        os.remove(os.path.join(conversations_path, subject + fileExtention))
    else:
        print("No chat history with that subject")
        return


        

@cli.command()
@click.option("--subject", prompt="Subject", help="Subject of the conversation")
@click.option("--enquiry", prompt="Enquiry", help="Your question")
@click.option("--persona", default="Neutral", help="Subject of the conversation")
@click.option("--engine", default=progConfig["engine"], help="Set alternative engine")
@click.option("--temperature", default=progConfig["temperature"], help="Set alternative temperature")
@click.option("--top-p", default=progConfig["topP"], help="Set alternative topP")
@click.option("--frequency-penalty", default=progConfig["frequencyPenalty"], help="Set alternative frequencyPenalty")
@click.option("--presence-penalty", default=progConfig["presencePenalty"], help="Set alternative presencePenalty")
@click.option("--max-tokens", default=progConfig["maxTokens"], help="Set alternative maxTokens")
@click.option("--quiet/--verbose", default=True, help="Show verbose output or just the answer")
def query(subject, enquiry, persona,engine, temperature,max_tokens, top_p,  frequency_penalty, presence_penalty, quiet): 
    """
Query the OpenAI API with the provided subject and enquiry"""
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
            try:
                response = completions_with_backoff(
                    delay_in_seconds=delay,
                    engine=engine,
                    prompt=chat,
                    temperature=float(temperature),
                    max_tokens=int(max_tokens),
                    top_p=int(top_p),
                    frequency_penalty=float(frequency_penalty),
                    presence_penalty=float(presence_penalty),
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
            except Exception as e:
                if str(e) == "openai.error.RateLimitError":
                    print("Error: Too many requests. Please wait a few minutes and try again")
                print("Error: " + str(e))
                return
        with open(os.path.join(conversations_path, sanitizeName(subject) + fileExtention), "a") as f:
            f.write(enquiry) 
            f.write("\n")
            f.write(progConfig["aiPrompt"] + ai)
            f.write("\n")
            f.close()
    else:
        print("No subject provided")
        return
    
    #  print("The askGPT is sleeping. [bold red]Next time, rub the lamp first.[/bold red]")

