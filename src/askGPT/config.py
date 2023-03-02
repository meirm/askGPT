""""""
import os
from pathlib import Path
from .tools import load_json, eprint, strToValue
from askGPT import DATA_PATH
import toml
from .api.openai import ChatGPT

basicConfig = dict()
basicConfig["userPrompt"] = basicConfig.get("userPrompt","user")
basicConfig["aiPrompt"] = basicConfig.get("aiPrompt","assistant")
basicConfig["systemPrompt"] = basicConfig.get("systemPrompt","system")
basicConfig["maxTokens"] = basicConfig.get("maxTokens",150)
basicConfig["model"] = basicConfig.get("model","gpt-3.5-turbo")
basicConfig["temperature"] = basicConfig.get("temperature",0.0)
basicConfig["topP"] = basicConfig.get("topP",1)
basicConfig["frequencyPenalty"] = basicConfig.get("frequencyPenalty",0.5)
basicConfig["presencePenalty"] = basicConfig.get("presencePenalty",0.5)
basicConfig["showDisclaimer"] = basicConfig.get("showDisclaimer",True)
basicConfig["maxRetries"] = basicConfig.get("maxRetries",3)
basicConfig["retryDelay"] = basicConfig.get("retryDelay",15.0)
basicConfig["retryMaxDelay"] = basicConfig.get("retryMaxDelay",60)
basicConfig["retryMultiplier"] = basicConfig.get("retryMultiplier",2)
basicConfig["verbose"] = basicConfig.get("verbose", False)
basicConfig["debug"] = basicConfig.get("debug", False)
basicConfig["updateScenarios"] = basicConfig.get("updateScenarios", True)

class Config(object):
    def __init__(self):
        self.rate_limit_per_minute = 20
        self.delay = 60.0 / self.rate_limit_per_minute
        self.disclaimer = "Disclaimer: The advice provided by askGPT is intended for informational and entertainment purposes only. It should not be used as a substitute for professional advice, and we cannot be held liable for any damages or losses arising from the use of the advice provided by askGPT."
        self.settingsPath=os.path.join(os.getenv("HOME"), ".askGPT")
        self.progConfig = dict()
        self.sessionConfig = dict()
        self.credentials = None
        self.has = dict()
        self.has["license"] = False
        self.conversations_path=os.path.join(self.settingsPath, "conversations")
        Path(self.conversations_path).mkdir(parents=True, exist_ok=True)
        self.loadScenarios()
        self.fileExtention=".ai.txt"
        self.loadDefaults()
        self.loadProgConfig()
        self.update()
        self.chat = ChatGPT(self)
        self.chat.loadLicense()
        self.version="0.6.1"
        self.data_path = DATA_PATH

    def loadProgConfig(self):
        if os.path.isfile(os.path.join(self.settingsPath, "config.toml")):
            tomlConfig = toml.load(os.path.join(self.settingsPath,"config.toml"))
            self.progConfig.update(tomlConfig["default"])
        else:
            self.saveConfig()

    def updateParameter(self,key, val):
        val = strToValue(val)
        if key in self.sessionConfig: # order matters
            if self.sessionConfig[key] != val:
                print(f"{key}] = {val}")
                self.sessionConfig[key] = val
        elif key in self.progConfig:
            if self.progConfig[key] != val:
                print(f"{key}] = {val}")
                self.progConfig[key] = val
        


    def saveConfig(self):
        """Save the configuration file"""
        jsonConfig = {'name':'askGPT','default':self.progConfig}
        with open(os.path.join(self.settingsPath,"config.toml"), 'w') as f:
            toml.dump(jsonConfig,f)
        self.update()

    def reloadConfig(self):
        """Reload the configuration file"""
        self.update()

    def get_list(self):
        """
        list the previous conversations saved by askGPT."""
        conv_array = list()
        for line in os.listdir(self.conversations_path):
            if (not line.startswith("."))  and line.endswith(self.fileExtention) and (os.path.isfile(os.path.join(self.conversations_path,line))):
                conv_array.append(line.replace(self.fileExtention,""))
        return sorted(conv_array)

    def loadScenarios(self):
        """if there is not a file named scenarios.json, create it ad add the Neutral scenario"""
        if not os.path.isfile(os.path.join(self.settingsPath,"scenarios.json")):
            # copy the file from PATH
            with open(os.path.join(DATA_PATH,"scenarios.json"), "r") as f:
                data = f.read()
            with open(os.path.join(self.settingsPath,"scenarios.json"), "w") as f:
                f.write(data)
        self.scenarios = load_json(os.path.join(self.settingsPath,"scenarios.json"))


    def loadDefaults(self):
        self.progConfig["userPrompt"] = self.progConfig.get("userPrompt","user")
        self.progConfig["aiPrompt"] = self.progConfig.get("aiPrompt"," assistant")
        self.progConfig["maxTokens"] = self.progConfig.get("maxTokens",150)
        self.progConfig["model"] = self.progConfig.get("model","text-davinci-003")
        self.progConfig["temperature"] = self.progConfig.get("temperature",0.0)
        self.progConfig["topP"] = self.progConfig.get("topP",1)
        self.progConfig["frequencyPenalty"] = self.progConfig.get("frequencyPenalty",0.0)
        self.progConfig["presencePenalty"] = self.progConfig.get("presencePenalty",0.0)
        self.progConfig["showDisclaimer"] = self.progConfig.get("showDisclaimer",True)
        self.progConfig["maxRetries"] = self.progConfig.get("maxRetries",3)
        self.progConfig["retryDelay"] = self.progConfig.get("retryDelay",15.0)
        self.progConfig["retryMaxDelay"] = self.progConfig.get("retryMaxDelay",60)
        self.progConfig["retryMultiplier"] = self.progConfig.get("retryMultiplier",2)
        self.progConfig["verbose"] = self.progConfig.get("verbose", False)
        self.progConfig["debug"] = self.progConfig.get("debug", False)
        self.progConfig["updateScenarios"] = self.progConfig.get("updateScenarios", True)

    def printConfig(self):
        """Print the configuration file"""
        print(toml.dumps(self.progConfig))

    def update(self):
        """
Load the configuration file from ~/.askGPT/config.toml"""
        self.loadProgConfig()
            # self.progConfig.update(tomlConfig["askGPT"])
