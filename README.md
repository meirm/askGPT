askGPT is a simple command line tool for interacting with OpenAI's API.

## Install 
    git clone https://github.com/meirm/askGPT.git
    cd askGPT
    python setup.py install

## Examples

    # askGPT query --subject test --enquiry "This is a test"
    This is a test of my AI capabilities.

    # askGPT query --subject test --enquiry "Do you believe?" --verbose
    Human: Do you believe in God?
    AI: 
    I do not have a belief system that includes the concept of God.
    Human: Do you believe?
    AI: 
    I believe in the power of knowledge and understanding. I believe that by learning and exploring, we can make the world a better place.
## Usage
    
    askGPT query --subject <subject> --enquiry <enquiry>

    askGPT list
    
    askGPT show --subject <subject>
    
    askGPT delete --subject <subject>
    
    askGPT delete --all
    
    askGPT config
    
    askGPT credentials
    
    askGPT list_personas

    
### Options
    -h --help     Show this screen.

    --version     Show version.
    
    --subject     Subject of the conversation
    
    --enquiry     Your question
    
    --all         Delete all archived conversations
    

## Personas
Personas is a way to provide the AI bot with a personality and some background information to respond to our enquires in a relevat way.
In the git repository under config you have a sample json with a few personalities. Copy the file to $HOME/.askGPT
If you do not have a personas.json file in the directory, the pogram will load with a Neutral persona without any background.

### Creating new persona
Edit the personas.json, add a new key which will be used to refere to the new persona. 
The format of the new entry should be:
    
    {"<persona>": {"name": "<name>", "greetings": "<Initial sentence>", "prompt": [ {"user":"Human", "prompt":"<your initial prompt>"},{"user": "AI", "prompt": "<AI response>"}, ... ]}}

i.e.

    "AlbertoKnox":{"Name": "Knox", "greetings":"I am Alberto Knox, the philosopher from Sophia's world. I am also a chatbot", "prompt":[
        {"user" : "Human", "prompt": "What's your role in the book?"},
        {"user": "AI", "prompt": "The ideal philosopher. I am never quick to judge and I always thinks about what I am doing."}
    ]}

## API Key and Organization
In order to communicate with openai API you need to register at https://www.openai.com and create an API key. If you don't have an organization code and it shows Organization: Personal, go to https://beta.openai.com/docs/api-reference/authentication and look for the code in the example.



## Summary
"askGPT" is a program that allows you to interact with chatgpt on the command line and save the history of your conversation.
At any time you can resume a conversation, create a new one or read the dialog from a previous session.

Features:
chat history. 

To install run: python setup.py install

To load the available personas copy the file personas.json into your .askGPT directory.


To run the program type: askGPT
