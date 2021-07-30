
def smart_random_player(bot, state):
    dangerous_enemy_pos = [enemy.position
        for enemy in bot.enemy if enemy.position in enemy.homezone]
    killable_enemy_pos = [enemy.position
        for enemy in bot.enemy if enemy.position not in enemy.homezone]

    smart_positions = []
    for new_pos in bot.legal_positions[:]:
        if (new_pos == bot.position or
            new_pos in dangerous_enemy_pos):
            continue # bad idea
        elif (new_pos in killable_enemy_pos or
              new_pos in bot.enemy[0].food):
            return new_pos # get it
        else:
            smart_positions.append(new_pos)

    if smart_positions:
        return bot.random.choice(smart_positions)
    else:
        # we ran out of smart moves
        return bot.position


TEAM_NAME = "Smart Random Players"
move = smart_random_player
