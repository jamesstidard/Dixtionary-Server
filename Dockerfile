FROM python:3.7.17-slim-bookworm

COPY . /app
WORKDIR /app

RUN pip install -U pipenv
RUN pipenv install --system

CMD python3 -m dixtionary
