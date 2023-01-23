askGPT is a simple command line tool for interacting with OpenAI's API.

## Install 
    git clone https://github.com/meirm/genie.git
    cd genie
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

    
### Options:
    -h --help     Show this screen.

    --version     Show version.
    
    --subject     Subject of the conversation
    
    --enquiry     Your question
    
    --all         Delete all archived conversations
    
## Summary
"askGPT" is a program that allows you to interact with chatgpt on the command line and save the history of your conversation.
At any time you can resume a conversation, create a new one or read the dialog from a previous session.

Features:
chat history. 

To install run: python setup.py install

To load the available personas copy the file personas.json into your .genie directory.


To run the program type: genie
