TEAM_NAME="failing"
def move(b, s):
    if b.round == 2 and b.turn == 0:
        # introduce an error
        0 / 0
    return b.position