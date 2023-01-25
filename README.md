# askGPT

askGPT is a command line program written in Python that allows you to query the chatGPT API. It keeps track of conversations and has a set of personas to focus the conversation.

## Installation

To install askGPT, simply run the following command:

```
pip install askGPT
```

## Usage

Once installed, you can use askGPT by running the following command:

```
askGPT query --subject <subject> --enquiry <enquiry>
```

Where `<subject>` is the title used for logging the conversation and `<enquiry>` is the enquiry you want to address.


## Install 
    pip install askGPT

or

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
    
    askGPT show  <config|personas|subjects|engines>

    askGPT show subject <subject>
    
    askGPT delete --subject <subject>
    
    askGPT delete --all
    
    askGPT config
    
    askGPT credentials
    

    
### Options
    -h --help     Show this screen.

    --version     Show version.
    
    --subject     Subject of the conversation
    
    --enquiry     Your question
    
    --all         Delete all archived conversations
    
## Personas

askGPT allows you to use personas to focus the conversation. Personas are defined as follows:

```
{"<persona>": {"name": "<name>", "greetings": "<Initial sentence>", "prompt": [ {"user":"Human", "prompt":"<your initial prompt>"},{"user": "AI", "prompt": "<AI response>"}, ... ]}}
```

Where `<persona>` is the name of the persona, `<name>` is the name of the character, `<initial sentence>` is the initial sentence used to start the conversation, and `<prompt>` is an array of sentences between the user and askGPT.


i.e.
```
"AlbertoKnox":{"Name": "Knox", "greetings":"I am Alberto Knox, the philosopher from Sophia's world. I am also a chatbot", "prompt":[
    {"user" : "Human", "prompt": "What's your role in the book?"},
    {"user": "AI", "prompt": "The ideal philosopher. I am never quick to judge and I always thinks about what I am doing."}
]}
```

In the git repository under config you have a sample json with a few personalities. Copy the file to $HOME/.askGPT
If you do not have a personas.json file in the directory, the pogram will load with a Neutral persona without any background.

## API Key and Organization
In order to communicate with openai API you need to register at https://www.openai.com and create an API key. If you don't have an organization code and it shows Organization: Personal, go to https://beta.openai.com/docs/api-reference/authentication and look for the code in the example. Once you have your API key and organization code, you can use them to authenticate with askGPT.

## Summary

askGPT is a command line program written in Python that allows you to query the chatGPT API. It keeps track of conversations and has a set of personas to focus the conversation. Installation is easy, 
simply run `pip install askGPT` and you're ready to go. Authentication requires an API key and organization code from OpenAI. With askGPT, you can easily query the chatGPT API and have meaningful conversations with AI. 
You can also list the personas, list conversations, show the content of a conversation, delete it, and fine tune parameters such as temperature for more personalized conversations.

## Next

Adding support for other languages.