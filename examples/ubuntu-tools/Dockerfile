FROM ubuntu:22.04

# Update package list and install common tools
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Set default command to bash
CMD ["/bin/bash"]
