
type User:
    required property name -> str


type Room:
    required property name -> str:
        constraint unique
    required link owner -> User
    property password -> str
    multi link members -> User
    required link game -> Game


type Game:
    multi link rounds -> Round


type Round:
    required property choices -> array<str>
    property choice -> str
    required link artist -> User
    multi link scores -> Score


type Score:
    link user -> User
    required property value -> int16
