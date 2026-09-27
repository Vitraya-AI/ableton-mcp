"""Bar/beat conversion helpers.

Positions are in beats (quarter notes), matching Live's API. Bars follow
Live's ruler: bar 1 starts at beat 0, and fractional bars are allowed
(bar 2.5 is half way through bar 2).
"""

from __future__ import annotations

_VALID_DENOMINATORS = (1, 2, 4, 8, 16)


def _check_signature(numerator, denominator) -> None:
    if not isinstance(numerator, int) or isinstance(numerator, bool) or numerator < 1:
        raise ValueError(f"Time signature numerator must be an integer >= 1, got {numerator!r}")
    if denominator not in _VALID_DENOMINATORS or isinstance(denominator, bool):
        raise ValueError(
            f"Time signature denominator must be one of {_VALID_DENOMINATORS}, "
            f"got {denominator!r}"
        )


def beats_per_bar(numerator: int, denominator: int) -> float:
    """Length of one bar in beats (quarter notes)."""
    _check_signature(numerator, denominator)
    return numerator * 4 / denominator


def bar_to_beat(bar: float, numerator: int, denominator: int) -> float:
    """Convert a 1-based bar position to beats. Bar 1 = beat 0."""
    per_bar = beats_per_bar(numerator, denominator)
    if bar < 1:
        raise ValueError(f"Bar must be >= 1 (bar 1 is the start of the song), got {bar}")
    return (bar - 1) * per_bar


def beat_to_bar(beat: float, numerator: int, denominator: int) -> float:
    """Convert a beat position to a 1-based bar position. Beat 0 = bar 1."""
    per_bar = beats_per_bar(numerator, denominator)
    if beat < 0:
        raise ValueError(f"Beat must be >= 0, got {beat}")
    return beat / per_bar + 1


def resolve_position(beat: float | None = None, bar: float | None = None,
                     numerator: int = 4, denominator: int = 4) -> float:
    """Return a position in beats from exactly one of ``beat`` or ``bar``."""
    if (beat is None) == (bar is None):
        raise ValueError("Give exactly one of beat or bar")
    if bar is not None:
        return bar_to_beat(bar, numerator, denominator)
    _check_signature(numerator, denominator)
    if beat < 0:
        raise ValueError(f"Beat must be >= 0, got {beat}")
    return float(beat)


def resolve_length(beats: float | None = None, bars: float | None = None,
                   numerator: int = 4, denominator: int = 4) -> float:
    """Return a length in beats from exactly one of ``beats`` or ``bars``."""
    if (beats is None) == (bars is None):
        raise ValueError("Give exactly one of beats or bars")
    if bars is not None:
        length = bars * beats_per_bar(numerator, denominator)
    else:
        _check_signature(numerator, denominator)
        length = float(beats)
    if length <= 0:
        raise ValueError(f"Length must be > 0, got {beats if bars is None else bars}")
    return length
