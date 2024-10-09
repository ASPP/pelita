# Pelita changelog

  * v2.5.1 (09. Oct 2024)

    - 1000 new layouts with dead ends
    - Matches will be played on a maze with dead ends/chambers with 25% chance
    - Reduced the radius of the food shadow
    - Streamlined handling of random numbers and seeding

  * v2.5.0 (08. Aug 2024)

     - Food ageing and relocation to discourage camping strategies
     - New attribute bot.shaded_food
     - Fullscreen mode added to UI
     - Enhanced CI engine
     - New and enlarged collection of layouts
     - New attribute bot.team_time in bot
     - Add send queue to server to avoid stalling
     - Fewer failures in Github CI

  * v2.4.0 (23. May 2024)

     - Greatly improved server mode
     - Bot.legal_positions becomes a static attribute
     - Bot has a new cached attribute graph
     - Small timeout improvements

  * v2.3.2 (16. Oct 2023)

     - Give advice when tkinter is not available
     - Fix colours in --ascii mode on Windows
     - Improved --progress bar

  * v2.3.1 (2. Sep 2023)

     - Tournament can be configured to include name of host and local salutation

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
