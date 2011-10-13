from _test_factory import TestMovementSettings, GeneratedTests, tests_from_list
from pelita.datamodel import north, south, west, east, stop

error = TestMovementSettings(
name   = "ValueError",
layout =
"""########
   #2    1#
   #.  ##.#
   #.  0#.#
   #   ##3#
   ########""",
expect= ({0: (6,1), 5:(4,1)},
         {0: (6,4)}),
enemy_moves = ([west, stop, stop, stop],
               [west, west, stop, east, east]),
second_team = True
)

tracking_2 = TestMovementSettings(
name   = "stop tracking 2",
layout =
"""########
   #0  ##1#
   #    # #
   #      #
   #.####.#
   #   2  #
   ########
   #     3#
   ########""",
   expect= ({0: (6,1), 1:(6,2), 2:(6,3), 3:(5,3)}),
enemy_moves = ([],[west, stop]),
second_team = True
)

tracking_0 = TestMovementSettings(
name   = "stop tracking 0",
layout =
"""########
   #2  ##1#
   #    # #
   #      #
   #.####.#
   #   0  #
   ########
   #     3#
   ########""",
   expect= ({0: (6,1), 1:(6,2), 2:(6,3), 3:(5,3)}),
enemy_moves = ([west, stop],[]),
second_team = True
)

tests_from_list([error, tracking_2, tracking_0])
#GeneratedTests.silent = False

if __name__ == '__main__':
    import unittest
    from pelita.player import BasicDefensePlayer
    GeneratedTests.player = BasicDefensePlayer
    unittest.main()
