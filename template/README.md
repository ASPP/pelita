pelita script:
  --stop-at
  --no-timeout
  --null
  --seed

in pelita TK interface
show-grid, play/pause, selecting square when grid is active, bot numbers

origin is top left
coordinates -> tuple (x, y)

```python
bot = game.team[0]
```
-> utils

pelita.utils (write doc strings):
 - setup_test_game
 - create_layout
 - Graph

print(game) and use the output for setup_test_game
python -m pytest

move function interface API
## The Game object

- **`game.team`** is a list of the two `Bot` objects

## The Bot object

- **`bot.position`** is a tuple of the coordinates your bot is on at the moment. For example `(3, 9)`.

- **`bot.legal_moves`** is a list of moves your bot can make without hitting a wall. Note that not moving, i.e. `(0, 0)` is always a legal move.

- **`bot.walls`** is a list of the coordinates of the walls in the maze: 
    ```python
    [(0, 0), (1, 0), (2, 0), ..., (29, 15), (30, 15), (31, 15)]
    ```
    so, if for example you want to test if position `(3, 9)` in the maze is a wall, you can do:
    ```python
    (3, 9) in bot.walls
    ```
    The maze can be represented as a graph. Pelita has its own minimal implementation of a graph, which offers
    a couple of short-path algorithm implementations. The maze can be converted to a graph with
    ```python
    from pelita.utils import Graph
    
    graph = Graph(bot.position, bot.walls)
    ```
    Example usage of `Graph` can be found in [demo05_basic_defender.py](demo05_basic_defender.py). More advanced graph features can be obtained by converting the maze to a [networkx](https://networkx.github.io/) graph. For this you can use the `walls_to_nxgraph` function in [utils.py](utils.py)

- **`bot.homezone`** is a list of all the coordinates of your side of the maze, so if for example you are the red team in a maze of size `16x32` your homezone will be:
    ```python
    [(16, 0), (16, 1), (16, 2), (16, 3), ..., (31, 13), (31, 14), (31, 15)]
    ```
    as with `bot.walls` you can test if position `(3, 9)` is in your homezone with
    ```python
    (3, 9) in bot.homezone
    ```
    You can check if you got assigned the blue team – your homezone is the left side of the maze – with **`bot.is_blue`**. Otherwise you are the red team and your homezone is the right side of the maze. The blue team plays the first move.

- **`bot.food`** is the list of the coordinates of the food pellets in your own homezone
    ```python
    [(17, 8), (24, 8), (17, 7), ...]
    ```
    as soon as the enemy will start eating your food pellets this list will shorten up!


- **`bot.track`** is a list of the coordinates of the positions that the bot has taken until now. It gets reset every time the bot gets eaten by an enemy ghost. When you are eaten, the property **`bot.eaten`** is set to `True` until the next round.

- **`bot.score`** and **`bot.round`** tell you the score of your team and the round you are playing.

- **`bot.get_move(next_position)`** is a method of the `Bot` object which gives you the move you have to make to get to the position `next_position`. If `next_position` can not be reached with a legal move you'll get a `ValueError`.

- **`bot.get_position(next_move)`** is a methof of the `Bot` object which gives you the position you will have if you execute the move `next_move`. If `next_move` is not a legal move you'll get a `ValueError`

- **`bot.random`** is an instance of the Python internal pseudo-random number generator. Do not import the Python `random` module in your code, just use this for all your random operations. Example of using it are found in [demo02_random.py](demo02_random.py), [demo03_smartrandom.py](demo03_smartrandom.py), and several others. If you need to use the `numpy` random module, initialize it with a seed taken from this instance like this:
    ```python
    np.random.seed(bot.random.randint(0, 2**32-1))
    ```
    Note that you want to do it only **once** per game!

- **`bot.timeout_count`** is a count of the timeouts your team has got. Remember that after 5 timeouts you lose the game, independent of the score.

- **`bot.say(text)`** allows you to print `text` as a sort of speech bubble attached to your bot in the graphical user interface.

- **`bot.enemy`** is a list containing the references to the two enemy bots, which are also `Bot` objects, so they have all the properties we have just seen above. So, for example the position of the first enemy bot:
    ```python
    bot.enemy[0].position
    ```
    Note that enemy position is noisy if the enemy is more than 5 squares away (independent of walls positions!). This is indicated by the **`is_noisy`** property: `bot.enemy[0].is_noisy`. The noise is uniformely distributed in the interval `+/- 5` squares.
    You can also inspect the enemy team name with `bot.enemy[0].team_name`.





