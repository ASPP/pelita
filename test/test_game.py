from pelita.game import initial_positions


def test_initial_positions():
    walls = [(0, 0),
             (0, 1),
             (0, 2),
             (0, 3),
             (1, 0),
             (1, 3),
             (2, 0),
             (2, 1),
             (2, 3),
             (3, 0),
             (3, 1),
             (3, 3),
             (4, 0),
             (4, 1),
             (4, 3),
             (5, 0),
             (5, 3),
             (6, 0),
             (6, 3),
             (7, 0),
             (7, 1),
             (7, 2),
             (7, 3)]
    out = initial_positions(walls)
    exp = [(1, 2), (6, 1), (1, 1), (6, 2)]
    assert len(out) == 4
    assert out == exp
