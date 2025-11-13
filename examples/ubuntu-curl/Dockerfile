FROM ubuntu:22.04

# Update package list and install curl
RUN apt-get update && apt-get install -y curl

# Verify curl is installed
RUN curl --version

# Set default command
CMD ["/bin/bash"]
