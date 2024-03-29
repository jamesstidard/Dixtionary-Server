# Dixtionary
A graphql server for a pictionary type online game.

Production branches are hosted at:

- Web App: [https://dixtionary.stidard.com](https://dixtionary.stidard.com)
- GraphQL API: [https://dixtionary.stidard.com/api/graphql](https://dixtionary.stidard.com/api/graphql)
- Subscriptions API: [wss://dixtionary.stidard.com/api/subscriptions](wss://dixtionary.stidard.com/api/subscriptions)

# Prerequisites
This server requires Python 3.7 and a redis server to run. Dependencies are also managed
by Pipenv, so you'll need that to.

if you have docker `docker run --rm -p 6379:6379/tcp redis:latest` should do it.

# Summoning Ritual
```sh
$ poetry install
$ poetry run python -m dixtionary
```
