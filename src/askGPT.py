#!/usr/bin/env python
"""
askGPT is a simple command line tool for interacting with OpenAI's API.
It is based on the example provided by OpenAI at https://beta.openai.com/docs/developer-quickstart/1-introduction
Date: 2023/01/23
"""
__title__ = 'askGPT'
__author__ = 'Meir Michanie'
__license__ = 'MIT'
__credits__ = ''
__version__ = "0.3.4"

import os
import openai
import click
from rich import print
from pathlib import Path
import json
import backoff
import time
import toml
import sys

basicConfig = dict()
basicConfig["userPrompt"] = basicConfig.get("userPrompt"," Human: ")
basicConfig["aiPrompt"] = basicConfig.get("aiPrompt"," AI: ")
basicConfig["maxTokens"] = basicConfig.get("maxTokens","150")
basicConfig["model"] = basicConfig.get("model","text-davinci-003")
basicConfig["temperature"] = basicConfig.get("temperature","0.0")
basicConfig["topP"] = basicConfig.get("topP","1")
basicConfig["frequencyPenalty"] = basicConfig.get("frequencyPenalty","0.0")
basicConfig["presencePenalty"] = basicConfig.get("presencePenalty","0.0")
basicConfig["showDisclaimer"] = basicConfig.get("showDisclaimer",True)
basicConfig["maxRetries"] = basicConfig.get("maxRetries",3)
basicConfig["retryDelay"] = basicConfig.get("retryDelay",15.0)
basicConfig["retryMaxDelay"] = basicConfig.get("retryMaxDelay",60)
basicConfig["retryMultiplier"] = basicConfig.get("retryMultiplier",2)
class Config(object):
    def __init__(self):
        self.rate_limit_per_minute = 20
        self.delay = 60.0 / self.rate_limit_per_minute
        self.disclaimer = "Disclaimer: The advice provided by askGPT is intended for informational and entertainment purposes only. It should not be used as a substitute for professional advice, and we cannot be held liable for any damages or losses arising from the use of the advice provided by askGPT."
        self.settingsPath=os.path.join(os.getenv("HOME"), ".askGPT")
        self.progConfig = dict()
        self.conversations_path=os.path.join(self.settingsPath, "conversations")
        Path(self.conversations_path).mkdir(parents=True, exist_ok=True)
        self.fileExtention=".ai.txt"
        self.loadLicense()
        self.loadDefaults()
        self.update()

    def loadPersonas(self):
        """if there is not a file named personas.json, create it ad add the Neutral persona"""
        if not os.path.isfile(os.path.join(self.settingsPath,"personas.json")):
            with open(os.path.join(self.settingsPath,"personas.json"), "w") as f:
                f.write(json.dumps({"Neutral":{"name": "Neutral", "greetings": "I am a chatbot. How can I help you today?", "prompt": [], "max_tokens": 1000}}))
        self.personas = load_json(os.path.join(self.settingsPath,"personas.json"))


    def loadDefaults(self):
        self.progConfig["userPrompt"] = self.progConfig.get("userPrompt"," Human: ")
        self.progConfig["aiPrompt"] = self.progConfig.get("aiPrompt"," AI: ")
        self.progConfig["maxTokens"] = self.progConfig.get("maxTokens","150")
        self.progConfig["model"] = self.progConfig.get("model","text-davinci-003")
        self.progConfig["temperature"] = self.progConfig.get("temperature","0.0")
        self.progConfig["topP"] = self.progConfig.get("topP","1")
        self.progConfig["frequencyPenalty"] = self.progConfig.get("frequencyPenalty","0.0")
        self.progConfig["presencePenalty"] = self.progConfig.get("presencePenalty","0.0")
        self.progConfig["showDisclaimer"] = self.progConfig.get("showDisclaimer",True)
        self.progConfig["maxRetries"] = self.progConfig.get("maxRetries",3)
        self.progConfig["retryDelay"] = self.progConfig.get("retryDelay",15.0)
        self.progConfig["retryMaxDelay"] = self.progConfig.get("retryMaxDelay",60)
        self.progConfig["retryMultiplier"] = self.progConfig.get("retryMultiplier",2)

    def loadLicense(self):
        # Load your API key from an environment variable or secret management service
        if os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_ORGANIZATION"):
            openai.api_key = os.getenv("OPENAI_API_KEY")
            openai.organization = os.getenv("OPENAI_ORGANIZATION")
        else:
            if os.path.isfile(os.path.join(self.settingsPath, "credentials")):
                with open(os.path.join(self.settingsPath, "credentials"), "r") as f:
                    credentials = f.read()
                    openai.api_key = credentials.split(":")[0]
                    openai.organization = credentials.split(":")[1].strip()
            else:
                eprint("Please set OPENAI_API_KEY and OPENAI_ORGANIZATION environment variables.")
                eprint("Or create a file at ~/.askGPT/credentials with the following format:")
                eprint("OPENAI_API_KEY:OPENAI_ORGANIZATION")
                exit(1)

    def update(self):
        """
Load the configuration file from ~/.askGPT/config.toml"""
        if os.path.isfile(os.path.join(self.settingsPath, "config.toml")):
            tomlConfig = toml.load(os.path.join(self.settingsPath,"config.toml"))
            self.progConfig.update(tomlConfig["default"])


# Calculate the delay based on your rate limit


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)



def completions_with_backoff(delay_in_seconds: float = 1,**kwargs):
    """Delay a completion by a specified amount of time."""
    # Sleep for the delay
    time.sleep(delay_in_seconds)
    return openai.Completion.create(**kwargs)


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



pass_config = click.make_pass_decorator(Config, ensure=True)


@click.group()
@click.version_option(__version__)
@pass_config
def cli(config):
    if config.progConfig.get("showDisclaimer",True):
        print(config.disclaimer)

@cli.command()
@pass_config
def disclaimer(config):
    """Show the disclaimer"""
    if not config.progConfig.get("showDisclaimer",False):
        print(config.disclaimer)


@cli.command()
@pass_config
@click.option("--user-prompt",  default=basicConfig["userPrompt"], help="User prompt")
@click.option("--ai-prompt", default=basicConfig["aiPrompt"], help="AI prompt")
@click.option("--model", default=basicConfig["model"], help="Set alternative model")
@click.option("--temperature", default=basicConfig["temperature"], type=float, help="Set alternative temperature")
@click.option("--top-p", default=basicConfig["topP"], type=int, help="Set alternative topP")
@click.option("--frequency-penalty", default=basicConfig["frequencyPenalty"], type=float, help="Set alternative frequencyPenalty")
@click.option("--presence-penalty", default=basicConfig["presencePenalty"], type=float, help="Set alternative presencePenalty")
@click.option("--max-tokens", default=basicConfig["maxTokens"], type=int, help="Set alternative maxTokens")
@click.option("--show-disclaimer/--hide-disclaimer", default=basicConfig["showDisclaimer"], help="Show disclaimer on startup")
@click.option("--max-retries", default=basicConfig["maxRetries"], type=int, help="Set alternative maxRetries")
@click.option("--retry_delay", default=basicConfig["retryDelay"], type=float, help="seconds between retries")
@click.option("--retry-multiplier", default=basicConfig["retryMultiplier"], type=float, help="multiplier")
@click.option("--retry-max-delay", default=basicConfig["retryMaxDelay"], type=float, help="max delay between retries")
def config(config, user_prompt, ai_prompt, max_tokens,model, temperature, top_p, 
frequency_penalty, presence_penalty, show_disclaimer,max_retries,
retry_delay,retry_multiplier,retry_max_delay):
    """
Change config values"""
    config.progConfig["userPrompt"] = user_prompt
    config.progConfig["aiPrompt"] = ai_prompt
    config.progConfig["maxTokens"] = max_tokens
    config.progConfig["model"] = model
    config.progConfig["temperature"] = temperature
    config.progConfig["topP"] = top_p
    config.progConfig["frequencyPenalty"] = frequency_penalty
    config.progConfig["presencePenalty"] = presence_penalty
    config.progConfig["showDisclaimer"] = show_disclaimer
    config.progConfig["maxRetries"] = max_retries
    config.progConfig["retryDelay"] = retry_delay
    config.progConfig["retryMultiplier"] = retry_multiplier
    config.progConfig["retryMaxDelay"] = retry_max_delay

    jsonConfig = {'name':'askGPT','default':config.progConfig}
    print(toml.dumps(jsonConfig))
    with open(os.path.join(config.settingsPath,"config.toml"), 'w') as f:
        toml.dump(jsonConfig,f)
        

@cli.command()
@pass_config
@click.option("--subject", prompt="Subject", help="Subject to use to save the conversation")
def edit(config,subject):
    """
Edit a conversation"""
    subject = sanitizeName(subject)
    lines = list()
    if os.path.isfile(os.path.join(config.conversations_path, subject + config.fileExtention)):
        with open(os.path.join(config.conversations_path, subject + config.fileExtention), "r") as f:
            lines = f.readlines()
    lines = click.edit("".join(lines))
    if lines is not None:
        with open(os.path.join(config.conversations_path, subject + config.fileExtention), "w") as f:
            f.write(lines)

@cli.command()
@pass_config
@click.argument("whatToShow", default="config")
@click.argument("subject", default="" )
def show(config, whattoshow, subject):
    """Show config|personas|subjects or the conversation inside a subject."""
    if subject == "":
        if whattoshow == "config":
            print("Current configuration:")
            print(toml.dumps(config.progConfig))
        elif whattoshow == "subjects":
            print("Current subjects:")
            for subject in get_list():
                    print(subject)
        elif whattoshow == 'personas':
            print("Current personas:")
            for persona in config.personas.keys():
                print(persona)
        elif whattoshow == 'models':
            print("Current models:")
            for model in sorted(list(map(lambda n: n.id,openai.Model.list().data))):
                print(model)
        else:
            print("Please specify what to show. Valid options are: config, subjects, personas, subject")
            print("In case of passing the option 'subject' please pass as well the subject's name")
    else:
        if os.path.isfile(os.path.join(config.settingsPath, 'conversations', subject + config.fileExtention)):
            with open(os.path.join(config.settingsPath, 'conversations', subject + config.fileExtention), 'r') as f:
                print(f.read())
        else:
            eprint("Subject not found")


@cli.command()
@pass_config
def credentials(config):
    """
Save the API keys to query OpenAI"""
    print("Welcome to askGPT")
    print("Please provide your OpenAI API key and organization")
    print("You can find these values at https://beta.openai.com/account/api-keys")
    openai.api_key = input("API_KEY:")
    openai.organization = input("ORGANIZATION:")
    with open(os.path.join(config.settingsPath, "credentials"), "w") as f:
        f.write(openai.api_key + ":" + openai.organization)
    print("askGPT is now ready to use")


@pass_config
def get_list(config):
    """
list the previous conversations saved by askGPT."""
    conv_array = list()
    for line in os.listdir(config.conversations_path):
        if (not line.startswith("."))  and line.endswith(config.fileExtention) and (os.path.isfile(os.path.join(config.conversations_path,line))):
            conv_array.append(line.replace(config.fileExtention,""))
    return conv_array


@cli.command()
@pass_config
@click.option("--subject", help="Subject of the conversation")
@click.option("--all/--single",  default=False, help="Delete all archived conversations")
def delete(config, subject, all):
    """
Delete the previous conversations saved by askGPT"""
    if all:
        for subject in get_list():
            os.remove(os.path.join(config.conversations_path, subject + config.fileExtention))
    elif subject and os.path.isfile(os.path.join(config.conversations_path,sanitizeName(subject) + config.fileExtention)):
        os.remove(os.path.join(config.conversations_path, subject + config.fileExtention))
    else:
        eprint("No chat history with that subject")
        return


        

@cli.command()
@pass_config
@click.option("--subject", prompt="Subject", help="Subject of the conversation")
@click.option("--enquiry", prompt="Enquiry", help="Your question")
@click.option("--persona", default="Neutral", help="Persona to use in the conversation")
@click.option("--model", default=basicConfig["model"], help="Set alternative model")
@click.option("--temperature", default=basicConfig["temperature"], type=float, help="Set alternative temperature")
@click.option("--top-p", default=basicConfig["topP"], type=int, help="Set alternative topP")
@click.option("--frequency-penalty", default=basicConfig["frequencyPenalty"], type=float, help="Set alternative frequencyPenalty")
@click.option("--presence-penalty", default=basicConfig["presencePenalty"], type=float, help="Set alternative presencePenalty")
@click.option("--max-tokens", default=basicConfig["maxTokens"], type=int, help="Set alternative maxTokens")
@click.option("--verbose", is_flag=True, help="Show verbose output or just the answer")
@click.option("--save/--no-save", default=True, help="Save the conversation")
@click.option("--retry", is_flag=True, help="In case of error retry the post.")

def query(config, subject, enquiry, persona,model, temperature,max_tokens, top_p,  frequency_penalty, presence_penalty, verbose, save, retry): 
    """
Query the OpenAI API with the provided subject and enquiry"""
    enquiry = config.progConfig["userPrompt"] + enquiry
    if subject:
        with open(os.path.join(config.conversations_path, sanitizeName(subject) + config.fileExtention), "a") as f:
            pass
        with open(os.path.join(config.conversations_path, sanitizeName(subject) + config.fileExtention), "r") as f:
            chatRaw = f.read()
            if persona != "Neutral":
                chat = config.progConfig["aiPrompt"] +  config.personas[persona]["greetings"] + "\n" + chatRaw  + enquiry + "\n" + config.progConfig["aiPrompt"]
            else:
                chat = chatRaw + enquiry + "\n" + config.progConfig["aiPrompt"]
            tries = 1
            if retry:
                tries = config.progConfig["maxRetries"]
            success = False
            sleepBetweenRetries = config.progConfig["retryDelay"]
            while tries > 0:
                try:
                    response = completions_with_backoff(
                        delay_in_seconds=config.delay,
                        model=model,
                        prompt=chat,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        top_p=top_p,
                        frequency_penalty=frequency_penalty,
                        presence_penalty=presence_penalty,
                        stop=[ # "\n",
                        config.progConfig["userPrompt"], config.progConfig["aiPrompt"]],
                    )
                    ai = response.choices[0].text
                    if ai.startswith("\n\n"):
                        ai = ai[2:]
                    if verbose:
                        print(chat + ai)
                    else:
                        print(ai)
                    f.close()
                    success = True
                    break
                except Exception as e:
                    tries -= 1

                    if str(e) == "openai.error.RateLimitError":
                        eprint("Error: Too many requests. We will try again")
                    eprint("Error: " + str(e))
                    eprint(f"Retrying again in {sleepBetweenRetries} seconds...")
                    time.sleep(sleepBetweenRetries)
                    sleepBetweenRetries *= config.progConfig["retryMultiplier"] 
                    if sleepBetweenRetries > config.progConfig["retryMaxDelay"]:
                        sleepBetweenRetries = config.progConfig["retryMaxDelay"]
        if success == False:
            eprint("Error: Too many requests. Please wait a few minutes and try again")
            return
        if save:               
            with open(os.path.join(config.conversations_path, sanitizeName(subject) + config.fileExtention), "a") as f:
                f.write(enquiry) 
                f.write("\n")
                f.write(config.progConfig["aiPrompt"] + ai)
                f.write("\n")
                f.close()
    else:
        print("No subject provided")
        return
    
    #  print("The askGPT is sleeping. [bold red]Next time, rub the lamp first.[/bold red]")

