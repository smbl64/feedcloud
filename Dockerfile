FROM python:3.7-slim-buster
LABEL MAINTAINER="Mohammad Banisaeid <smbl64@gmail.com>"

ENV LANG=C.UTF-8 LC_ALL=C.UTF-8 PYTHONUNBUFFERED=1

RUN apt update

# Install requirements
COPY requirements /app/requirements
RUN pip install -r /app/requirements/prod.txt

COPY . /app
WORKDIR /app
