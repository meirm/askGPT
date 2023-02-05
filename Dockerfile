FROM python:3

RUN apt update && apt install -y vim nano wget curl && apt clean
# Install the required package
RUN mkdir -p /root/.askGPT && pip install askGPT==0.4.18

COPY askgpt_shell.sh /usr/local/bin
# Set the working directory
WORKDIR /root/

# Run the script
CMD ["askgpt_shell.sh"]
