""" collecting the game state filter functions """
import random
import copy

### The main function

def noiser(gamestate, noise_radius=5, sight_distance=-1, seed=None):
	"""Function to make bot positions noisy in a game state.

    Applies uniform noise in maze space. Noise will only be applied if the enemy bot
	is farther away than a certain threshold (`sight_distance`), which is
	Manhattan distance disregarding walls.  A bot with distance of 1 in Manhattan space
    could still be much further away in maze distance.
	
	Distance to enemies measured in Manhattan space, disregarding walls. So, a bot
	distance of 1 in Manhattan space could still be much further away in maze
	distance.
	
	Given a `bot_index` (now 'turn' in gamestate) the method looks up the enemies
	of this bot. It then adds uniform noise in maze space to the enemy positions, but
	only if bot is farther away than sight_distance
	
	If a position is noisy or not is indicated by the `noisy` attribute in the 
	gamestate dictionary, and then also in the returned noisy game state

    Functions needed
    ----------------

    altered_pos(bot_pos):
        return the noised new position of an enemy bot.
		
	manhattan_dist(a,b):
		returns a scalar

    Parameters
    ----------
    gamestate : holding all relevant information
    noise_radius : int, optional, default: 5
        the radius for the uniform noise
    sight_distance : int, optional, default: 5
        the distance at which noise is no longer applied.
    seed : int, optional
        seed which initialises the internal random number generator
		to make games replicable
		
	Returns
	-------
	noisy_gamestate : gamestate with noisy enemy positions
		
    """

	# set the random state
	rnd = random.Random(seed)
	
	# maka a new game state
	#cp_gs = copy.deepcopy(gamestate)
	# using a shallow copy
	cp_gs = {}
	cp_gs.update(gamestate)
	
	# get the current turn (ie the bot_index)
	turn = cp_gs["turn"]
	
	# get the walls
	walls = cp_gs["walls"]
	
	# get the current bot
	# [:] makes a copy
	bots        = cp_gs["bots"][:]
	current_bot = bots[turn]
	
	# get the enemy bots
	enemy_bots  = list(range(0,4))
	if turn % 2:
		# current bot is in the uneven team
		enemy_slice = slice(1,4,2)
	else:
		# current bot is in the even team
		enemy_slice = slice(0,4,2)
	enemy_bots = bots[enemy_slice]
	
	# get the noisy information
	noisy = cp_gs["noisy"]
	
	print(len(enemy_bots))

	for count, b in enumerate(enemy_bots):
		# Check that the distance between this bot and the enemy is larger
		# than `sight_distance`.
		cur_distance = manhattan_dist(current_bot, b)
		print('cur_distance')
		print(cur_distance)
		print('sight_distance')
		print(sight_distance)

		if cur_distance is None or cur_distance > sight_distance:
			# If so then alter the position of the enemy
			print('now changing position')
			cur_altered_pos = alter_pos(b,noise_radius,rnd,walls)
			print(cur_altered_pos)
			enemy_bots[count] = cur_altered_pos[0]
			noisy[count]      = cur_altered_pos[1]
	
	# packing before return
	print(enemy_bots)
	bots[enemy_slice] = enemy_bots
	cp_gs["noisy"] = noisy
	cp_gs["bots"] = bots
	
	# return
	return cp_gs
	
	
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
	#return [(0,0), True]
	
def manhattan_dist(pos1, pos2):
    """ Manhattan distance between two points.

    Parameters
    ----------
    pos1 : tuple of (int, int)
        the first position
    pos2 : tuple of (int, int)
        the second position

    Returns
    -------
    manhattan_dist : int
        Manhattan distance between two points
    """
    return abs(pos1[0]-pos2[0]) + abs(pos1[1]-pos2[1])