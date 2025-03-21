from typing import TypeAlias, TypedDict, Any
from random import Random

from .team import Team

Shape: TypeAlias = tuple[int, int]
Pos: TypeAlias = tuple[int, int]
FoodAges: TypeAlias = dict[Pos, int]

class GameState(TypedDict):
    walls: set[Pos]
    shape: Shape
    food: tuple[set[Pos], set[Pos]]
    food_age: tuple[FoodAges, FoodAges]
    turn: None|int
    round: None|int
    gameover: bool
    whowins: None|int
    bots: list[Pos]
    score: list[int]
    fatal_errors: tuple[list[Any], list[Any]]
    errors: tuple[Any, Any]
    max_rounds: int
    timeout: int
    noise_radius: int
    sight_distance: int
    max_food_age: int
    shadow_distance: int
    layout_name: str
    team_names: tuple[str, str]
    team_infos: tuple[None|str, None|str]
    team_time: tuple[float, float]
    deaths: list[int]
    kills: list[int]
    bot_was_killed: list[bool]
    noisy_positions: list[None|Pos]
    requested_moves: list[None|Pos]
    say: list[str]
    teams: list[None|Team]
    rng: Random
    timeout_length: int
    error_limit: int
    viewers: list[Any]
    controller: None|Any
