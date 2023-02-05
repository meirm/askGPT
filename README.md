askGPT
======
```
                           :|11;                             _     ____ ____ _____
                          20;::20                   __ _ ___| | __/ ___|  _ \_   _|
                          10|:;2$                  / _` / __| |/ / |  _| |_) || |
                            |&2'                  | (_| \__ \   <| |_| |  __/ | |
                '''''''''''':&1 '''''''''''        \__,_|___/_|\_\\____|_|    |_|
             |21111111111111111111111111111121
            18:                              20
            0$     ';;;             :;;:     |&:
         2218$    22|;101         :01;;10:   |&12
        :&; $$    82:':02         ;8|''|8;   |&
        :&; $$     ;111:           '|11|'    |&
         1218$           :211|112|           |&22
            $$             ':::'             |&:
            18;                             '$$
             ;2212:    ';11111111111111111112|
                 82 ;1221:
                 0021;
                 ''
 
                                                            

 ```

***Disclaimer***: The advice provided by askGPT is intended for informational and entertainment purposes only. It should not be used as a substitute for professional advice, and we cannot be held liable for any
damages or losses arising from the use of the advice provided by askGPT.

***askGPT***  is a command line program written in Python that allows you to query the chatGPT API. It keeps track of conversations and has a set of scenarios to focus the conversation.

## Run with docker Latest release
```
docker run -i cyborgfi/askgpt:latest 
```
## Run with docker development version
```
docker run -i cyborgfi/askgpt:dev 
```
## Installation

To install askGPT , simply run the following command:

```
pip install askGPT 
```
or for cutting edge code, not to be used in production:
```
git clone https://github.com/meirm/askGPT.git
cd askGPT 
python -m build
pip install .
```
## Usage

Once installed, you can use ***askGPT***  by running the following command:

```
askgpt  query --subject <subject> --enquiry <enquiry>
```

Where `<subject>` is the title used for logging the conversation and `<enquiry>` is the enquiry you want to address.

Optionally you can run an interactive shell calling

```
askgpt shell
```

Once inside the shell you can run the help command.

## Install 
    pip install askGPT

or

    git clone https://github.com/meirm/askGPT.git
    cd askGPT 
    python setup.py install

## Examples

    # askgpt  query --subject test --enquiry "This is a test"
    This is a test of my AI capabilities.

    # askgpt  query --subject test --enquiry "Do you believe?" --verbose
    Human: Do you believe in God?
    AI: 
    I do not have a belief system that includes the concept of God.
    Human: Do you believe?
    AI: 
    I believe in the power of knowledge and understanding. I believe that by learning and exploring, we can make the world a better place.
## Available commands
    
    askgpt  disclaimer

    askgpt help

    askgpt  man

    askgpt  list
    
    askgpt  show  <config|scenarios|subjects|models>

    askgpt  show subject <subject>
    
    askgpt  delete --subject <subject>
    
    askgpt  delete --all
    
    askgpt  config
    
    askgpt  credentials

    askgpt shell

    askgpt submit

    
### Shell mode
From version 0.4.5 you can run ***askgpt shell***
This will open an interactive shell. The prompt shows the current loaded scenario. You can list scenarios and subjects with the commmands `show scenarios` and `show subjects`. You can change the settings by running `set scenario <scenarioName>` or the subject. Setting the subject to a subject that doesn't exist will create a new conversation log. If you choose a subject that already exist, your next query will be appended to the history of your previous conversation before sending the prompt to chatGPT.

#### Essential Shell commands

* config
* credentials
* set
* help
* man
* query

### Configuration

***askGPT*** will create a config.toml on your .askGPT folder. You can see or change values calling ***askGPT*** config

The content of the file by default is the following:
```
name = "askGPT"

[default]
userPrompt = " Human: "
aiPrompt = " AI: "
maxTokens = 150
model = "text-davinci-003"
temperature = 0.0
topP = 1
frequencyPenalty = 0.0
presencePenalty = 0.0
showDisclaimer = true
maxRetries = 3
retryDelay = 5.0
retryMultiplier = 2.0
retryMaxDelay = 60.0

```
    
## scenarios
***askGPT*** repository includes a sample of several scenarios which you can use to preset your bot.
* Doctor
* Psychotherapist
* Lawyer
* Marv (from The HitchHicker guide to the galaxy)
* VocationalTest
* scenariolityAssessment
* DiaryAssistance
* veganCheff

When you first run askGPT, it will copy the ***scenario.json*** file from the package into your .askGPT directory
In the git repository under ***config*** you can find the latest file named ***scenarios.json*** 

copy this file to ***.askGPT*** directory

***askGPT***  allows you to use scenarios to focus the conversation. scenarios are defined as follows:

```
{"<scenario>": {"name": "<name>", "greetings": "<Initial sentence>", "conversation": [ {"user":"userPrompt", "prompt":"<your initial prompt>"},{"user": "aiPrompt", "prompt": "<AI response>"}, ... ]}}
```

Where `<scenario>` is the name of the scenario, `<name>` is the name of the character, `<initial sentence>` is the initial sentence used to start the conversation, and `<prompt>` is an array of sentences between the user and ***askGPT*** .


i.e.
```
"AlbertoKnox":{"Name": "Knox", "greetings":"I am Alberto Knox, the philosopher from Sophia's world. I am also a chatbot", "conversation":[
    {"user" : "userPrompt", "prompt": "What's your role in the book?"},
    {"user": "aiPrompt", "prompt": "The ideal philosopher. I am never quick to judge and I always thinks about what I am doing."}
]}
```

In the git repository under config you have a sample json with a few scenariolities. Copy the file to $HOME/.***askGPT*** 

## API Key and Organization
In order to communicate with openai API you need to register at https://www.openai.com and create an API key. If you don't have an organization code and it shows Organization: scenariol, go to https://beta.openai.com/docs/api-reference/authentication and look for the code in the example. Once you have your API key and organization code, you can use them to authenticate with ***askGPT*** .

## Summary

***askGPT***  is a command line program written in Python that allows you to query the chatGPT API. It keeps track of conversations and has a set of scenarios to focus the conversation. Installation is easy, 
simply run `pip install askGPT ` and you're ready to go. Authentication requires an API key and organization code from OpenAI. With ***askGPT*** , you can easily query the chatGPT API and have meaningful conversations with AI. 
You can also list the scenarios, list conversations, show the content of a conversation, delete it, and fine tune parameters such as temperature for more scenariolized conversations.

## Contributing
We welcome contributions to ***askGPT***! If you have an idea for a new feature or have found a bug, please open an issue on the GitHub repository.

## License
This project is licensed under the MIT License - see the LICENSE file for details.


## Next

* Adding support for other languages.

## Note

   This project is under active development.