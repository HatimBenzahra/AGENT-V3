# Agent Workspace Docker Image
# This image is used as the execution environment for agent operations

FROM python:3.11-slim

LABEL maintainer="Agent Workspace"
LABEL description="Isolated execution environment for ReAct agent"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install common development tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    wget \
    vim \
    nano \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create workspace directory
RUN mkdir -p /workspace
WORKDIR /workspace

# Install common Python packages
RUN pip install --no-cache-dir \
    requests \
    numpy \
    pandas \
    matplotlib \
    pytest \
    black \
    flake8 \
    mypy

# Set default command
CMD ["tail", "-f", "/dev/null"]
