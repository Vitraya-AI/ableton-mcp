"""Bar/beat conversion helpers (MCP_Server/timing.py)."""

import pytest

from MCP_Server import timing


@pytest.mark.parametrize("num, den, expected", [
    (4, 4, 4.0), (3, 4, 3.0), (6, 8, 3.0), (7, 8, 3.5), (2, 2, 4.0), (5, 16, 1.25),
])
def test_beats_per_bar(num, den, expected):
    assert timing.beats_per_bar(num, den) == expected


@pytest.mark.parametrize("bar, num, den, beat", [
    (1, 4, 4, 0.0), (2, 4, 4, 4.0), (5, 4, 4, 16.0),
    (1, 3, 4, 0.0), (3, 3, 4, 6.0),
    (2, 6, 8, 3.0), (4, 6, 8, 9.0),
    (2, 7, 8, 3.5), (3, 7, 8, 7.0),
])
def test_bar_to_beat(bar, num, den, beat):
    assert timing.bar_to_beat(bar, num, den) == beat
    assert timing.beat_to_bar(beat, num, den) == bar


def test_fractional_bars():
    assert timing.bar_to_beat(2.5, 4, 4) == 6.0
    assert timing.bar_to_beat(1.5, 7, 8) == 1.75
    assert timing.beat_to_bar(6.0, 4, 4) == 2.5
    assert timing.beat_to_bar(1.5, 3, 4) == 1.5


@pytest.mark.parametrize("num, den", [(4, 4), (3, 4), (6, 8), (7, 8), (5, 16)])
@pytest.mark.parametrize("beat", [0.0, 0.25, 1.0, 3.5, 17.75, 100.0])
def test_round_trip(num, den, beat):
    bar = timing.beat_to_bar(beat, num, den)
    assert timing.bar_to_beat(bar, num, den) == pytest.approx(beat)


def test_bar_below_one_rejected():
    with pytest.raises(ValueError):
        timing.bar_to_beat(0.99, 4, 4)
    with pytest.raises(ValueError):
        timing.bar_to_beat(0, 4, 4)


def test_negative_beat_rejected():
    with pytest.raises(ValueError):
        timing.beat_to_bar(-0.5, 4, 4)


@pytest.mark.parametrize("num, den", [(0, 4), (-1, 4), (4, 3), (4, 0), (4, 32), (4.5, 4)])
def test_invalid_signature_rejected(num, den):
    with pytest.raises(ValueError):
        timing.beats_per_bar(num, den)
    with pytest.raises(ValueError):
        timing.bar_to_beat(1, num, den)
    with pytest.raises(ValueError):
        timing.resolve_position(beat=0, numerator=num, denominator=den)


def test_resolve_position():
    assert timing.resolve_position(beat=5) == 5.0
    assert timing.resolve_position(bar=3) == 8.0
    assert timing.resolve_position(bar=3, numerator=6, denominator=8) == 6.0
    with pytest.raises(ValueError):
        timing.resolve_position()
    with pytest.raises(ValueError):
        timing.resolve_position(beat=0, bar=1)
    with pytest.raises(ValueError):
        timing.resolve_position(bar=0.5)
    with pytest.raises(ValueError):
        timing.resolve_position(beat=-1)


def test_resolve_length():
    assert timing.resolve_length(beats=2) == 2.0
    assert timing.resolve_length(bars=2) == 8.0
    assert timing.resolve_length(bars=0.5, numerator=7, denominator=8) == 1.75
    with pytest.raises(ValueError):
        timing.resolve_length()
    with pytest.raises(ValueError):
        timing.resolve_length(beats=4, bars=1)
    for bad in ({"beats": 0}, {"beats": -1}, {"bars": 0}, {"bars": -2}):
        with pytest.raises(ValueError):
            timing.resolve_length(**bad)
