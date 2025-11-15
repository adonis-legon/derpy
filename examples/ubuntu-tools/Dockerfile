FROM ubuntu:22.04

# Update package list and install common tools
# Set DEBIAN_FRONTEND=noninteractive to prevent interactive prompts
RUN DEBIAN_FRONTEND=noninteractive apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
    curl \
    wget \
    git \
    vim \
    && rm -rf /var/lib/apt/lists/*

# Set default command to bash
CMD ["/bin/bash"]
