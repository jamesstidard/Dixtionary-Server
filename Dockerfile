FROM python:3.7.17-slim-bookworm

COPY . /app
WORKDIR /app

RUN pip install -U poetry
RUN apt-get update -y && apt-get install gcc
RUN poetry config virtualenvs.create false
RUN poetry install

CMD python3 -m dixtionary
