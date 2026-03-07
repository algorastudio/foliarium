FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Python 3.12 via deadsnakes PPA
RUN apt-get update && apt-get install -y \
        software-properties-common curl gnupg sudo \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y \
        python3.12 python3.12-venv python3.12-dev python3-pip \
    && ln -sf /usr/bin/python3.12 /usr/local/bin/python \
    && ln -sf /usr/bin/python3.12 /usr/local/bin/python3 \
    && python3.12 -m pip install --upgrade pip \
    && rm -rf /var/lib/apt/lists/*

# Utente non-root standard devcontainer
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && echo "$USERNAME ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

USER $USERNAME
