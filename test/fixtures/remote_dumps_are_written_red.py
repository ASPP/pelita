import sys
TEAM_NAME="p2"
def move(b, s):
    print(f"{b.round} {b.turn} p2", file=sys.stdout)
    print("p2err", file=sys.stderr)
    return b.position