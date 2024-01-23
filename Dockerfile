FROM python:3.7.17-slim-bookworm

COPY . /app
WORKDIR /app

RUN pip install -U poetry
RUN poetry config settings.virtualenvs.create false
RUN poetry install

CMD python3 -m dixtionary
