# Dixtionary
A graphql server for a pictionary type online game.

Production branches are hosted at:

Web App: [https://dixtionary.shitbeards.com](https://dixtionary.shitbeards.com)
GraphQL API: [https://dixtionary.shitbeards.com/api/graphql](https://dixtionary.shitbeards.com/api/graphql)
Subscriptions API: [wss://dixtionary.shitbeards.com/api/subscriptions](wss://dixtionary.shitbeards.com/api/subscriptions)

# Prerequisites
This server requires Python 3.7 and a redis server to run. Dependancies are also managed
by Pipenv, so you'll need that to.

if you have docker `docker run --rm -p 6379:6379/tcp redis:latest` should do it.

# Summoning Ritual
```sh
$ pipenv sync --dev
```
