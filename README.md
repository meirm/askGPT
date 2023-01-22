Genie is a simple command line tool for interacting with OpenAI's API.

Usage:
    genie.py query --subject <subject> --enquiry <enquiry>
    genie.py list
    genie.py show --subject <subject>
    genie.py delete --subject <subject>
    genie.py delete --all
    genie.py config
    genie.py credentials
    genie.py list_personas

    
Options:
    -h --help     Show this screen.
    --version     Show version.
    --subject     Subject of the conversation
    --enquiry     Your question
    --all         Delete all archived conversations
    

"genie" is a program that allows you to interact with chatgpt on the command line and save the history of your conversation.
At any time you can resume a conversation, create a new one or read the dialog from a previous session.

Features:
chat history. 

To install run: python setup.py install

To load the available personas copy the file personas.json into your .genie directory.


To run the program type: genie
