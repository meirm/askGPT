FROM python:3

# Install the required package
RUN mkdir -p /root/.askGPT && pip install askGPT

COPY askgpt_shell.sh /usr/local/bin
# Set the working directory
WORKDIR /root/

# Run the script
CMD ["askgpt_shell.sh"]
