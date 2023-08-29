# Player with an import error in move

TEAM_NAME = "Move import error"
def move(b, s):
    import this_module_does_not_exist
    return b.position
