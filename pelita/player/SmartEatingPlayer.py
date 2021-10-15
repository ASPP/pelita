
from pelita.player import food_eating_player

def smart_eating_player(bot, state):
    # food eating player but won’t do kamikaze (although a sufficently smart
    # enemy will be able to kill the bot in its next turn as it doesn’t flee)
    next_pos = food_eating_player(bot, state)

    dangerous_enemy_pos = [enemy.position for enemy in bot.enemy if enemy.position in enemy.homezone]

    # check, if the next_pos has an enemy on it
    if next_pos in dangerous_enemy_pos:
        # whoops, better wait this round and take another food next time
        state[bot.turn]['next_food'] = None
        return bot.position

    return next_pos


TEAM_NAME = "Smart Eating Players"
move = smart_eating_player
