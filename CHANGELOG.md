# Pelita changelog

  * v2.3.0 (31. Aug 2023)

     - Switching to pyproject.toml
     - Bot.walls and Bot.homezone are tuples of tuples for reproducibility

  * v2.2.0 (08. Sep 2022)

    - Do not have a team play two matches in a row during round-robin mode
    - Show the tournament group names in the UI and on the CLI
    - Automatic detection of network players via zeroconf

  * v2.1.0 (25. Sep 2021)

    - Bot API uses a fixed state dict instead of returning `(position, state)`
    - Layout unification: Use a,b,x,y as Bot characters instead of indexes
    - Adding shape tuple to API
    - Walls/Homezone are stored in a set for faster lookup
    - Improved debug UI
    - Changed primary branch to ‘main’
    - Use Gitlab CI actions instead of travis

  * v2.0.1 (27. Sep 2019)

    - Fixes a bug in Tk

  * v2.0.0 (3. Sep 2019)

    - Major rewrite to functional Bot API (no more `AbstractPlayer`)
    - Major rewrite of Pelita core

  * v0.9.2 (29. Oct 2018)

    - Bug fixes and API improvements

  * v0.9.1 (18. Jan 2018)

    - Minor API changes and bug fixes

  * v0.9.0 (31. Aug. 2017)

    - Python 3
    - Pelita is installable with setup.py

  * v0.2.0 (7. Sep. 2012)

    - Revised actor model to use zmq

  * v0.1.1 (23. May 2012)

    - Fixes and updates

  * v0.1.0 (21. Sep. 2011)

    - First usable version

  * v0.0.0 (1. Jun. 2011)

    - Initial commit of this repo
