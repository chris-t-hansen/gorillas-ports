"""qb_runtime.rng — QBASIC RND / RANDOMIZE.

Wraps Python's random module. Exact QBASIC LCG sequences are NOT reproduced
(per user decision); seeding from time.time() matches RANDOMIZE TIMER semantics.
"""

import random
import time

_rng = random.Random()


def randomize(seed=None) -> None:
    """RANDOMIZE [seed]. No argument → seed from time (like RANDOMIZE TIMER)."""
    if seed is None:
        _rng.seed(time.time())
    else:
        _rng.seed(seed)


def rnd(n: float = 1.0) -> float:
    """RND(n).

    QBASIC RND behavior:
      n > 0  → next random number in sequence (the common case)
      n = 0  → repeat last number
      n < 0  → restart sequence with seed derived from n

    We approximate: n > 0 → new value, n = 0 → cached, n < 0 → reseed.
    The generated values are in [0, 1), matching QBASIC.
    """
    if n > 0:
        rnd._last = _rng.random()
    elif n < 0:
        # QBASIC reseeds from the argument; we use it as a seed.
        _rng.seed(n)
        rnd._last = _rng.random()
    # n == 0: return last value (or 0 if never called)
    return getattr(rnd, "_last", 0.0)


# Initialize last-value cache.
rnd._last = 0.0


def fn_ran(x: int) -> int:
    """DEF FnRan(x) = INT(RND(1) * x) + 1  — random integer in [1, x]."""
    return int(rnd(1.0) * x) + 1
