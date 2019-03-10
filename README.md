# current api state
## meta schema
http://localhost:8000/graphql?query={__schema%20{%20types%20{%20name%20kind%20description%20fields%20{%20name%20}%20}%20}}

## login
http://localhost:8000/graphql?query=mutation%20myFirstMutation{login(name:%22bill%22){me%20{uuid,name}}}

## me and rooms
http://localhost:8000/graphql?query={me{uuid,name},rooms{name,capacity}}
