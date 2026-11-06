"""The cycle models: the presets, their time maps and boundaries."""

import numpy as np
import pytest

from cycles.functions.cycle_analysis import mismatch_by_depth
from cycles.functions.cycle_model import BUILTIN_PRESETS, DEFAULT_PRESET

PRESETS = list(BUILTIN_PRESETS)


@pytest.mark.parametrize('name', PRESETS)
def test_time_map_round_trip(name):
    time_map = BUILTIN_PRESETS[name].time_map()
    u = np.linspace(0, 1, 41)
    assert np.allclose(time_map.to_normalized(time_map.to_physical(u)), u, atol=1e-9)
    assert time_map.start < time_map.end


@pytest.mark.parametrize('name', PRESETS)
def test_boundaries_increase_and_span_the_cycle(name):
    model = BUILTIN_PRESETS[name]
    boundaries = np.asarray(model.boundaries())
    assert len(boundaries) == 5 and np.all(np.diff(boundaries) > 0)
    solution = model.solve()
    assert np.isclose(boundaries[0], solution['start']) and np.isclose(boundaries[-1], solution['end'])


def test_default_preset_starts_kali_at_midnight_in_ujjain():
    """Midnight starting 18 Feb 3102 BC at Ujjain (75.77° E, 5 h 03 min ahead) is 18:57 UT on 17 Feb."""
    pytest.importorskip('PySide6')         # datetime_text lives with the GUI helpers
    from cycles.gui.state import datetime_text
    kali = BUILTIN_PRESETS[DEFAULT_PRESET].boundaries()[3]
    assert datetime_text(kali) == '17 Feb 3102 BC, 18:57 UT'


@pytest.mark.parametrize('name', PRESETS)
def test_mismatch_is_reported_for_every_depth(name):
    rows = mismatch_by_depth(BUILTIN_PRESETS[name], max_depth=3)
    assert len(rows) == 3
