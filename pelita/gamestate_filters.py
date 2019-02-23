""" collecting the game state filter functions """

### The main function

def noiser(game_state, noise_radius=5, sight_distance=5, seed=None):
	"""Function to make bot positions noisy in a game state.

    Applies uniform noise in maze space. Noise will only be applied if the enemy bot
	is farther away than a certain threshold (`sight_distance`), which is
	Manhattan distance disregarding walls.  A bot with distance of 1 in Manhattan space
    could still be much further away in maze distance.
	
	Distance to enemies measured in Manhattan space, disregarding walls. So, a bot
	distance of 1 in Manhattan space could still be much further away in maze
	distance.
	
	Given a `bot_index` (now 'turn' in game_state) the method looks up the enemies
	of this bot. It then adds uniform noise in maze space to the enemy positions, but
	only if bot is farther away than sight_distance
	
	If a position is noisy or not is indicated by the `noisy` attribute in the 
	game_state dictionary, and then also in the returned noisy game state

    Functions needed
    ----------------

    altered_pos(bot_pos):
        return the noised new position of an enemy bot.
		
	manhattan_dist(a,b):
		returns a scalar

    Parameters
    ----------
    game_state : holding all relevant information
    noise_radius : int, optional, default: 5
        the radius for the uniform noise
    sight_distance : int, optional, default: 5
        the distance at which noise is no longer applied.
    seed : int, optional
        seed which initialises the internal random number generator
		to make games replicable
		
	Returns
	-------
	noisy_game_state : game_state with noisy enemy positions
		
    """

	# set the random state
	rnd = random.Random(seed)
	
	# get the current bot
	bots        = game_state["bots"]
	current_bot = bots[turn]
	
	# get the enemy bots
	enemy_bots  = list(range(0,4))
	if current_bot % 2:
		# current bot is in the uneven team
		enemy_bots = bots[1::2]
	else:
		# current bot is in the even team
		enemy_bots = bots[0::2]
		
	# get the noisy information
	noisy = enemy_bots["noisy"]

	for count, b in enemy_bots:
		# Check that the distance between this bot and the enemy is larger
		# than `sight_distance`.
		cur_distance = manhattan_dist(current_bot, b)

		if cur_distance is None or cur_distance > sight_distance:
			# If so then alter the position of the enemy
			cur_altered_pos = alter_pos(b,noise_radius,rnd,walls)
			b               = cur_altered_pos[0]
			noisy[count]    = cur_altered_pos[1]

	return noisy_game_state
	
	
### The subfunctions

def alter_pos(bot_pos,noise_radius,rnd,walls):
	""" alter the position """

	# get a list of possible positions
	noise_radius = noise_radius
	x_min, x_max = bot_pos[0] - noise_radius, bot_pos[0] + noise_radius
	y_min, y_max = bot_pos[1] - noise_radius, bot_pos[1] + noise_radius
	possible_positions = [(i,j) for i in range(x_min, x_max)
								for j in range(y_min, y_max)
						  if manhattan_dist((i,j), bot_pos) <= noise_radius]

	# shuffle the list of positions
	rnd.shuffle(possible_positions)
	final_pos = bot_pos
	noisy     = False
	for pos in possible_positions:
		# check that the bot won't returned as positioned on a wall square
		if pos in walls:
			continue
		else:
			final_pos = pos
			noisy     = True
			break
	# return the final_pos and a flag if it is noisy or not
	return [final_pos, noisy] 