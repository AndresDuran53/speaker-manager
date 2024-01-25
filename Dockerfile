# syntax=docker/dockerfile:1

FROM python:3.10-slim-buster

ENV TZ="America/Costa_Rica"

WORKDIR /home

COPY requirements.txt requirements.txt
RUN apt-get update && apt-get install -y alsa-utils && rm -rf /var/lib/apt/lists/*
RUN pip3 install -r requirements.txt

COPY . .

CMD [ "python3", "speakerManager/speakerManager.py"]

