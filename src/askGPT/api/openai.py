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
        self._model = "gpt-3.5-turbo"
        self._temperature = 0.9
        self._max_tokens = 150
        self._top_p = 1
        self._frequency_penalty = 0
        self._presence_penalty = 0
        # self._stop = ["\n"]
        self._config = config
        self._chat_log = []


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
            with open(os.path.join(self._config.conversations_path, subject + self._config.fileExtention), "r") as f:
                lines = f.readlines()
        
        lines = click.edit("".join(lines))
        if lines is not None:
            with open(os.path.join(self._config.conversations_path, subject + self._config.fileExtention), "w") as f:
                f.write(lines)
                self.createPrompt(subject, None, None)
        else:
            eprint("No changes made")



    def bootStrapChat(self,scenario):
        """Read the scenario and return the initial chat"""
        chat = list()
        
        if scenario in self._config.scenarios:
            self.greetings = {"role" : "system", "content":  self._config.scenarios[scenario]["greetings"] }
            conversationChat = [self.greetings]
            return  conversationChat + self._config.scenarios[scenario]["conversation"]
        else:
            eprint("Scenario not found")
            return []

    def completions_with_backoff(self, delay_in_seconds: float = 1,**kwargs):
        """Delay a completion by a specified amount of time."""
        # Sleep for the delay
        time.sleep(delay_in_seconds)
        if self._config.progConfig.get("api_base",None) is not None:
            openai.api_base = self._config.progConfig["api_base"]
        return openai.ChatCompletion.create(**kwargs)

    def createPrompt(self, subject: str, scenario: str, enquiry: dict):
        subject = sanitizeName(subject)
        chat = list()
        if subject:
            with open(os.path.join(self._config.conversations_path, sanitizeName(subject) + self._config.fileExtention), "a") as f:
                pass
            with open(os.path.join(self._config.conversations_path, sanitizeName(subject) + self._config.fileExtention), "r") as f:
                chatRaw = f.readlines()
                bootstrappedChat = list()
                if scenario:
                    bootstrappedChat = self.bootStrapChat(scenario)
                for line in chatRaw:
                    if line.startswith("user:"):
                        bootstrappedChat.append({"role": "user", "content": line.replace("user: ","")})
                    elif line.startswith("assistant:"):
                        bootstrappedChat.append({"role": "assistant", "content": line.replace("assistant: ","")})
                    elif line.startswith("system:"):
                        bootstrappedChat.append({"role": "system", "content": line.replace("system: ","")})
                    else:
                        bootstrappedChat[-1]["content"] += line
            
                """we need to add the enquiry to the chat"""
                if enquiry:
                    bootstrappedChat.append(enquiry)
                
                """We return a list that concats bootstrappedChat andchat"""
                return bootstrappedChat
        else:
            eprint("Please set a subject")
            return []


    def query(self, subject: str, scenario: str, enquiry: str, max_tokens: int = 150, temperature: float = 0.9, top_p: float = 1, frequency_penalty: float = 0, presence_penalty: float = 0, stop: list = ["\n", " user:", " assistant:"]):
        """Query the model with the given prompt."""
        # Load the license
        if not self.loadLicense():
            return
        # Create the prompt
        
        # We will prepend a system prompt with the information gathered from the me.txt file if file exists in the .askGPT config directory
        # open the ~/.askGPT/me.txt
        prompt = ""
        if self._config.progConfig.get("useMemoryFile",False):
            try:
                meFilePath = os.path.join(self._config.settingsPath,self._config.progConfig.get("memoryFile"))
                meText = ""
                if os.path.exists(meFilePath):
                    with open(meFilePath,'r', encoding='utf-8') as file:
                        meText = file.read().strip()
                        if meText != "":
                            meText = "\n\nUser info:\n"+meText+"\n\n"
                            prompt = {"role": "system", "content": meText}
            except Exception as ex:
                eprint ("Error reading me.txt : "+str(ex))
        # if prompt has a value then we init chat with it and then append list(self._chat_log)
        if prompt != "":
            chat = [prompt]+list(self._chat_log)
        else:
            chat  = list(self._chat_log)
        chat.append({"role":"user", "content": enquiry})
        # print("sending chat:")
        # print(chat)
        # return 
        ai = self.submitDialogWithBackOff(chat)
        if ai:
            # Add the response to the chat log
            self._chat_log.append({"role": "user", "content": enquiry})
            self._chat_log.append({"role": "assistant", "content": ai})
            # Return the response
            return ai

    def saveLicense(self, api_key):
        if not os.path.isdir(self._config.settingsPath):
            os.mkdir(self._config.settingsPath)
        with open(os.path.join(self._config.settingsPath, "credentials"), "w") as f:
            f.write(api_key)
        return True

    def load(self,chat):
        self.greetings = chat[0]
        self._chat_log = chat[1:]

    def loadLicense(self):
        # Load your API key from an environment variable or secret management service
        if os.getenv("OPENAI_API_KEY"):

            openai.api_key = os.getenv("OPENAI_API_KEY")
            self._config.credentials = os.getenv("OPENAI_API_KEY")
            self._config.has["license"] = True
            return True
        else:
            if os.path.isfile(os.path.join(self._config.settingsPath, "credentials")):
                with open(os.path.join(self._config.settingsPath, "credentials"), "r") as f:
                    credentials = f.read()
                    openai.api_key = credentials.strip()
                    self._config.credentials = credentials
                    self._config.has["license"] = True
                    return True
            else:
                eprint("Please set OPENAI_API_KEY and OPENAI_ORGANIZATION environment variables.")
                eprint("Or create a file at ~/.askGPT/credentials with the following format:")
                eprint("OPENAI_API_KEY:OPENAI_ORGANIZATION")
            
        return False
    
    def dream(self, prompt):
        response = openai.Image.create(
        prompt=prompt,
        n=1,
        size="1024x1024"
        )
        image_url = response['data'][0]['url']
        return image_url

    def submitDialog(self, subject, scenario):
        """Send the dialog to openai and save the response"""
        subject = sanitizeName(subject)
        chat = ""
        if subject:
            with open(os.path.join(self._config.conversations_path, sanitizeName(subject) + self._config.fileExtention), "a") as f:
                pass
            #chat = self.createPrompt(subject, scenario, None)
            chat = list(self._chat_log)
            if chat == None:
                print("Empty conversation")
                return
            ai = self.submitDialogWithBackOff(chat)
            if ai:
                return ai

    def submitDialogWithBackOff(self, chat):
        tries = self._config.progConfig.get("maxRetries",1)
        success = False
        reason = "Error: Could not send the dialog"
        sleepBetweenRetries = self._config.progConfig["retryDelay"]
        ai  = ModuleNotFoundError
        while tries > 0:
            try:
                if self._config.progConfig["debug"]:
                    eprint(chat)
                conversation = list(chat)
                conversation.insert(0, self.greetings)
                response = self.completions_with_backoff(
                    delay_in_seconds=self._config.delay,
                    model=self._config.progConfig["model"],
                    messages=conversation,
                    temperature=self._config.progConfig["temperature"],
                    max_tokens=self._config.progConfig["maxTokens"],
                    top_p=self._config.progConfig["topP"],
                    frequency_penalty=self._config.progConfig["frequencyPenalty"],
                    presence_penalty=self._config.progConfig["presencePenalty"],
                
                )
                # print(response)
                # return
                ai = response.choices[0]['message'].content
                if ai.startswith("\n\n"):
                    ai = ai[2:]
                if self._config.progConfig["debug"]:
                    eprint(ai)
                success = True
                break
            except KeyboardInterrupt:
                reason = "Operation aborted."
                break
            except Exception as e:
                tries -= 1
                if str(e) == "openai.error.RateLimitError":
                    eprint("Error: Too many requests. We will try again")
                if str(e).startswith("This model's maximum context length is"):
                    eprint("Error: Too many tokens. We will try again with less history")
                    eprint(f"Current number of interactions: {len(chat)}")
                    chat = chat[int((len(chat)/round(tries + 0.51)) + 0.5):]
                    self._chat_log = chat
                    eprint(f"New number of interactions: {len(chat)}")
                    time.sleep(5)
                    continue
                
                eprint("Error: " + str(e))

                eprint(f"Retrying again in {sleepBetweenRetries} seconds...")
                time.sleep(sleepBetweenRetries)
                sleepBetweenRetries *= self._config.progConfig["retryMultiplier"] 
                if sleepBetweenRetries > self._config.progConfig["retryMaxDelay"]:
                    sleepBetweenRetries = self._config.progConfig["retryMaxDelay"]
        if success == False:
            eprint(reason)
            return
        return ai

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




