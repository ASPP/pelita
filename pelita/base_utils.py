from random import Random

def default_rng(seed=None):
    """Construct a new RNG from a given seed or return the same RNG.

    Parameters
    ----------
    seed : Random | int | None
        RNG to re-use or seed to initialise a new RNG or None to initialise a RNG without seed
    """
    if isinstance(seed, Random):
        return seed
    return Random(seed)
