import time
TEAM_NAME = "500ms timeout"
def move(b, s):
    if b.round == 1 and b.turn == 1:
        return (-2, 0)
    time.sleep(0.5)
    return b.position