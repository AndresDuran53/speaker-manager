# syntax=docker/dockerfile:1

FROM python:3.10-slim-buster

ENV DEBIAN_FRONTEND noninteractive
ENV TZ="America/Costa_Rica"

WORKDIR /home

RUN groupadd -g 1000 sneer
RUN useradd -u 1000 -g sneer sneer

# Install package dependencies
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
        alsa-utils \
        libsndfile1-dev \
        pulseaudio-utils \
        pulseaudio && \
    apt-get clean

# Create PulseAudio configuration for the container user
RUN mkdir -p /home/sneer/.config/pulse && \
    cp /etc/pulse/client.conf /home/sneer/.config/pulse && \
    chown -R sneer:sneer /home/sneer/.config/pulse

# Set PulseAudio variables for the container user
ENV PULSE_SERVER=unix:/run/user/1000/pulse/native
ENV XDG_RUNTIME_DIR=/run/user/1000

# Change the user and group
COPY --chown=sneer:sneer . .

RUN pip3 install -r requirements.txt

USER sneer

CMD [ "python3", "speakerManager/speakerManager.py"]