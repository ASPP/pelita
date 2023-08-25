import sys
TEAM_NAME="p1"
def move(b, s):
    print(f"{b.round} {b.turn} p1", file=sys.stdout)
    print(f"p1err", file=sys.stderr)
    return b.position