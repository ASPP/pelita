# The Pelita tournament

## Setup

All configuration is done with a yaml file:

    ---
    location: Pelipolis
    date: 2525
    speak: false
    seed: null
    bonusmatch: True

    teams:
      - spec: RandomPlayer
        members:
          - "Member One"
      - spec: StoppingPlayer
        members:
          - "I stop"
      - spec: SmartRandomPlayer
        members:
          - "I am smart"
      - spec: FoodEatingPlayer
        members:
          - "no-one"
        id: group3

Apart from additional information regarding the event, the file allows for some basic configuration, such as the initial seed or whether there is supposed to be a final bonusmatch.

The most important part, of course, is the definition of the different teams.
Each entry in the `teams` list is enumerated and internally referenced to by either its index or its `id`. The id parameter can therefore be used to distinguish between a `student_group0` and `tutor_group2`, for example.
This is mainly used when outputting the members list.

The `spec` is the usual team specification that is also used on the `pelita` command line.
It is usually the path to the module (or team factory) where the participants `Player` is defined.
`StoppingPlayer` or `../group3/group_player:team2` are therefore possible.

## Running

Given a tournament.yaml file, a tournament can be started as

    pelita-tournament --config tournament.yaml --rounds 300

## Speech synthesis

Spoken output can be activated with the command line flag `--speak` and defaults to `/usr/bin/flite`.
Alternative outputs can be specified with the `--speaker flag`, which can be any callable expression that expects a file parameter (containing the text) as last argument.

An example using OS X’s `say`:

    pelita-tournament --config tournament.yaml --speak --speaker "/usr/bin/say -v 'Good News' -f"
