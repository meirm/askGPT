import openai
import os
from askGPT.tools import eprint, sanitizeName
import time
import backoff
import click

"""This is a class that inherit from openai class that will allow us to query chatgpt. By using a class we can share the object between modules passing it as an argument."""
class ChatGPT(object):
    def __init__(self, config) -> None:
        super().__init__()
        self._model = "davinci"
        self._temperature = 0.9
        self._max_tokens = 150
        self._top_p = 1
        self._frequency_penalty = 0
        self._presence_penalty = 0
        self._stop = ["\n", " Human:", " AI:"]
        self._chat_log = []
        self._config = config
        self.settingsPath = os.path.join(os.getenv("HOME"),".askGPT")

    def listModels(self):
        models = list()
        for model in sorted(list(map(lambda n: n.id,openai.Model.list().data))):
            models.append(model)
        return models
       
    def editDialog(self,subject):
        """
        Edit a conversation"""
        subject = sanitizeName(subject)
        lines = list()
        if os.path.isfile(os.path.join(self._config.conversations_path, subject + self._config.fileExtention)):
            with open(os.path.join(config.conversations_path, subject + config.fileExtention), "r") as f:
                lines = f.readlines()
        lines = click.edit("".join(lines))
        if lines is not None:
            with open(os.path.join(self._config.conversations_path, subject + self._config.fileExtention), "w") as f:
                f.write(lines)
        else:
            eprint("No changes made")



    def bootStrapChat(self,scenario):
        """Read the scenario and return the initial chat"""
        chat = list()
        conversationChat = list()
        if scenario in self._config.scenarios:
            chat=self._config.scenarios[scenario]["conversation"]
            """read the array conversation, for each row join the user and the prompt. append the line to the conversationChat"""
            for line in chat:
                conversationChat.append(self._config.progConfig.get(line["user"],"userPrompt") + line["prompt"])
            return self._config.progConfig["aiPrompt"] +  self._config.scenarios[scenario]["greetings"] + "\n" + "\n".join(conversationChat)
        else:
            eprint("Scenario not found")
            return ""

    def completions_with_backoff(self, delay_in_seconds: float = 1,**kwargs):
        """Delay a completion by a specified amount of time."""
        # Sleep for the delay
        time.sleep(delay_in_seconds)
        return openai.Completion.create(**kwargs)

    def createPrompt(self, subject: str, scenario: str, enquiry: str):
        subject = sanitizeName(subject)
        enquiry = self._config.progConfig["userPrompt"] + enquiry
        chat = ""
        if subject:
            with open(os.path.join(self._config.conversations_path, sanitizeName(subject) + self._config.fileExtention), "a") as f:
                pass
            with open(os.path.join(self._config.conversations_path, sanitizeName(subject) + self._config.fileExtention), "r") as f:
                chatRaw = f.read()
                if scenario != "Neutral":
                    bootstrappedChat = self.bootStrapChat(scenario)
                    chat = bootstrappedChat + "\n" + chatRaw  + enquiry + "\n" + self._config.progConfig["aiPrompt"]
                else:
                    chat = chatRaw + enquiry + "\n" + self._config.progConfig["aiPrompt"]
                return chat
        else:
            eprint("Please set a subject")
            return ""


    def query(self, subject: str, scenario: str, enquiry: str, max_tokens: int = 150, temperature: float = 0.9, top_p: float = 1, frequency_penalty: float = 0, presence_penalty: float = 0, stop: list = ["\n", " Human:", " AI:"]):
        """Query the model with the given prompt."""
        # Load the license
        if not self.loadLicense():
            return
        # Create the prompt
        response = None
        prompt = self.createPrompt(subject, scenario, enquiry)
        try:
            # Query the model
            response = self.completions_with_backoff(
                prompt=prompt,
                model=self._config.progConfig.get("model", "text-davinci-003"),
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                frequency_penalty=frequency_penalty,
                presence_penalty=presence_penalty,
                stop=stop
            )
        except Exception as e:
            eprint("Error: {}".format(e))
            return
        # Add the response to the chat log
        self._chat_log.append(response.choices[0].text)
        # Return the response
        return response
    
    def loadLicense(self):
        # Load your API key from an environment variable or secret management service
        if os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_ORGANIZATION"):

            openai.api_key = os.getenv("OPENAI_API_KEY")
            openai.organization = os.getenv("OPENAI_ORGANIZATION")
            return True
        else:
            if os.path.isfile(os.path.join(self.settingsPath, "credentials")):
                with open(os.path.join(self.settingsPath, "credentials"), "r") as f:
                    credentials = f.read()
                    openai.api_key = credentials.split(":")[0]
                    openai.organization = credentials.split(":")[1].strip()
                    return True
            else:
                eprint("Please set OPENAI_API_KEY and OPENAI_ORGANIZATION environment variables.")
                eprint("Or create a file at ~/.askGPT/credentials with the following format:")
                eprint("OPENAI_API_KEY:OPENAI_ORGANIZATION")
            
        return False

    def submitDialog(self, subject, scenario):
        """Send the dialog to openai and save the response"""
        subject = sanitizeName(subject)
        if subject:
            with open(os.path.join(self._config.conversations_path, sanitizeName(subject) + self._config.fileExtention), "a") as f:
                pass
            with open(os.path.join(self._config.conversations_path, sanitizeName(subject) + self._config.fileExtention), "r") as f:
                chatRaw = f.read()
                if scenario != "Neutral":
                    bootstrappedChat = self.bootStrapChat(self._config, scenario)
                    chat = bootstrappedChat + "\n" + chatRaw  + "\n" + self._config.progConfig["aiPrompt"]
                else:
                    chat = chatRaw + "\n" + self._config.progConfig["aiPrompt"]
                        
        if chat == "":
            print("Empty conversation")
            return

        tries = self._config.progConfig.get("maxRetries",1)
        success = False
        sleepBetweenRetries = self._config.progConfig["retryDelay"]
        
        while tries > 0:
            try:
                response = self.completions_with_backoff(
                    delay_in_seconds=self._config.delay,
                    model=self._config.progConfig["model"],
                    prompt=chat,
                    temperature=self._config.progConfig["temperature"],
                    max_tokens=self._config.progConfig["maxTokens"],
                    top_p=self._config.progConfig["topP"],
                    frequency_penalty=self._config.progConfig["frequencyPenalty"],
                    presence_penalty=self._config.progConfig["presencePenalty"],
                    stop=[ # "\n",
                    self._config.progConfig["userPrompt"], self._config.progConfig["aiPrompt"]],
                )
                ai = response.choices[0].text
                if ai.startswith("\n\n"):
                    ai = ai[2:]
                success = True
                break
            except Exception as e:
                tries -= 1
                if str(e) == "openai.error.RateLimitError":
                    eprint("Error: Too many requests. We will try again")
                eprint("Error: " + str(e))
                eprint(f"Retrying again in {sleepBetweenRetries} seconds...")
                time.sleep(sleepBetweenRetries)
                sleepBetweenRetries *= self._config.progConfig["retryMultiplier"] 
                if sleepBetweenRetries > self._config.progConfig["retryMaxDelay"]:
                    sleepBetweenRetries = self._config.progConfig["retryMaxDelay"]
        if success == False:
            eprint("Error: Could not send the dialog")
            return
        with open(os.path.join(self._config.conversations_path, subject + self._config.fileExtention), "a") as f:
            f.write(self._config.progConfig["aiPrompt"] + ai)
        print(ai)


    def get_chat_log(self):
        """Get the chat log."""
        return self._chat_log

    def set_model(self, model):
        """Set the model."""
        self._model = model

    def set_temperature(self, temperature):
        """Set the temperature."""
        self._temperature = temperature

    def set_max_tokens(self, max_tokens):
        """Set the max tokens."""
        self._max_tokens = max_tokens
    
    def set_top_p(self, top_p):
        """Set the top p."""
        self._top_p = top_p

    def set_frequency_penalty(self, frequency_penalty):
        """Set the frequency penalty."""
        self._frequency_penalty = frequency_penalty

    def set_presence_penalty(self, presence_penalty):
        """Set the presence penalty."""
        self._presence_penalty = presence_penalty

    def set_stop(self, stop):
        """Set the stop."""
        self._stop = stop

    def get_model(self):
        """Get the model."""
        return self._model

    def get_temperature(self):
        """Get the temperature."""
        return self._temperature

    def get_max_tokens(self):
        """Get the max tokens."""
        return self._max_tokens

    def get_top_p(self):
        """Get the top p."""
        return self._top_p

    def get_frequency_penalty(self):
        """Get the frequency penalty."""
        return self._frequency_penalty

    def get_presence_penalty(self):
        """Get the presence penalty."""
        return self._presence_penalty

    def get_stop(self):
        """Get the stop."""
        return self._stop




