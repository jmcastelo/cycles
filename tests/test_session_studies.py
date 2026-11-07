"""Studies run with a session saved by the explorer (runner --session)."""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from cycles.functions.cycle_model import BUILTIN_PRESETS, DEFAULT_PRESET

SANDBOX = Path(__file__).resolve().parents[1] / 'sandbox'


def _session(tmp_path, turns=2.25, bases=(4, 3, 2)):
    model = BUILTIN_PRESETS[DEFAULT_PRESET].replace(name='Moved', turns=turns)
    data = {'format': 'cycles-session', 'version': 1,
            'state': {'model': model.to_dict(),
                      'color_parameters': {'bases': list(bases), 'scales': [0.5, 2 / 3, 0.5],
                                           'colors': [[1, 1, 0], [0, 1, 1], [1, 0, 1], [0, 0, 0]]}}}
    path = tmp_path / 'for-studies.cycles.json'
    path.write_text(json.dumps(data))
    return path, model


def test_apply_session_reaches_the_study_module(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(SANDBOX))
    import common
    import types
    path, model = _session(tmp_path)
    study = types.SimpleNamespace(BASES=None, SCALES=None, other=1)
    saved = (common.BASES, common.SCALES, common.TETRAHEDRON_COLORS, common.MODEL, common.SESSION)
    try:
        text = common.apply_session(json.loads(path.read_text()), study)
        assert "cycle model 'Moved'" in text and common.MODEL == model
        assert study.BASES == [4, 3, 2] and common.BASES == [4, 3, 2] and study.other == 1
        from cycles.functions.division import compute_level
        session_level = common.compute_levels(2)[1]                 # with the session's parameters
        assert np.allclose(session_level.dharmas, compute_level(2, [4, 3, 2], common.SCALES,
                                                                common.TETRAHEDRON_COLORS).dharmas)
        with pytest.raises(ValueError):
            common.apply_session({'format': 'other'})
    finally:
        common.BASES, common.SCALES, common.TETRAHEDRON_COLORS, common.MODEL, common.SESSION = saved


def _run(*args):
    return subprocess.run([sys.executable, *args], cwd=SANDBOX.parent, capture_output=True, text=True, timeout=300)


def test_a_study_runs_with_the_sessions_model(tmp_path):
    path, model = _session(tmp_path)
    plain = _run(str(SANDBOX / 'study_of_precession.py'), 'yuga_epochs', '--no-show')
    moved = _run(str(SANDBOX / 'study_of_precession.py'), 'yuga_epochs', '--no-show', '--session', str(path))
    assert plain.returncode == 0 and moved.returncode == 0, moved.stderr
    assert "Session for-studies.cycles.json: cycle model 'Moved'" in moved.stdout
    assert 'Cycle model: Moved' in moved.stdout and 'Cycle model: Moved' not in plain.stdout
    assert moved.stdout.split('Cycle model')[1] != plain.stdout.split('Cycle model')[1]


def test_a_bad_session_is_refused(tmp_path):
    bad = tmp_path / 'bad.json'
    bad.write_text('{"format": "something else"}')
    result = _run(str(SANDBOX / 'study_of_division.py'), 'checks', '--no-show', '--session', str(bad))
    assert result.returncode != 0 and 'cannot use the session' in result.stderr
