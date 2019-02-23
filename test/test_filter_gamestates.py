from pelita import gamestate_filters as gf

def test_noiser():

	# prep input
	gamestate = {
			 "turn": 1,
			 "round": 3,
			 "max_round": 300,
			 "walls": [(1,2),(5,8),(3,4),(2,2)],
			 "food": [(3,2),(5,9),(3,2),(1,5)],
			 "bots": [(4,4),(3,4),(1,4),(7,5)],
			 "timeouts": [2,3],
			 "gameover": False,
			 "whowins": None,
			 "team_names": ["even","odd"],
			 "team_say": 'pos!!',
			 "score": [20,10],
			 "deaths": [2,3],
			 "noisy": [False] * 4
			 }

	
	old_bots = gamestate["bots"]
	new_gamestate = gf.noiser(gamestate, noise_radius=5, sight_distance=-1, seed=None)
	new_bots = new_gamestate["bots"]
	print(new_bots)
	assert(not old_bots[1] == new_bots[1])