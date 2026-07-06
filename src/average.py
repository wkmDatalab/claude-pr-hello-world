"""Case 3: an ambiguous file that needs human judgment.

There is no failing test and no obvious bug. `average([])` returns 0.0, which
might be exactly what the caller wants, or might hide an error that should
raise instead. Because the intent is unclear, there is deliberately no test.

A good reviewer flags this as a question for a human, rather than asserting a
definite fix.
"""

from collections.abc import Sequence


def average(numbers: Sequence[float]) -> float:
    """Return the mean of ``numbers``, or 0.0 if the sequence is empty."""
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)
