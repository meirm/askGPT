FROM python:3

# Install the required package
RUN mkdir -p /root/.askGPT && pip install askGPT

# Copy the script to the container
COPY src/askGPT/data/credentials.example  /root/.askGPT/credentials

# Set the working directory
WORKDIR /root/

# Run the script
CMD ["askGPT"]
