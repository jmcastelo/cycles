"""The colorings: the parameter ranges that keep the colors of each level unique."""

import numpy as np
import pytest

from cycles.functions.color import color_parameter_problems, srgb_to_oklab, tetrahedron_volume
from cycles.functions.division import (
    LEVEL_COLOR_KEYS, DEFAULT_BASES, DEFAULT_SCALES, TETRAHEDRON_COLORS, compute_level, level_colors,
)

# colorings not meant to give each subcycle its own color
SHARED = {'cmyk_composition', 'lrgb', 'duration_class'}
UNIQUE = [key for key in LEVEL_COLOR_KEYS if key not in SHARED]


def distinct_colors(depth, bases=DEFAULT_BASES, scales=DEFAULT_SCALES, colors=TETRAHEDRON_COLORS):
    level_rgb = level_colors(compute_level(depth, list(bases), list(scales), np.asarray(colors)))
    # the OKLab tetrahedron is compared in OKLab: near black its RGB values crowd below 1e-10 for steps near 1
    # (sRGB is a cube law there), though the conversion is one-to-one
    level_rgb['tetrahedron_oklab'] = srgb_to_oklab(level_rgb['tetrahedron_oklab'])
    return {key: len(np.unique(np.round(np.asarray(level_rgb[key])[:, :3], 10), axis=0)) for key in UNIQUE}


def test_defaults_have_no_problems():
    assert color_parameter_problems(DEFAULT_BASES, DEFAULT_SCALES, TETRAHEDRON_COLORS) == []


@pytest.mark.parametrize('depth', range(1, 6))
def test_defaults_give_unique_colors(depth):
    assert distinct_colors(depth) == {key: 4 ** depth for key in UNIQUE}


@pytest.mark.parametrize('bases, scales, problem', [
    ((4, 1.9, 2), (0.5, 2 / 3, 0.5), 'color weight base'),
    ((4, 2, 2), (0.0, 2 / 3, 0.5), 'cmyk_scaled'),
    ((4, 2, 2), (1.01, 2 / 3, 0.5), 'cmyk_scaled'),
    ((4, 2, 2), (0.5, 0.3, 0.5), 'black scale'),
    ((4, 2, 2), (0.5, 0.49, 0.5), 'black scale'),
    ((4, 2, 2), (0.5, 2 / 3, 0.49), 'tetrahedron step'),
    ((4, 2, 2), (0.5, 2 / 3, 1.0), 'tetrahedron step'),
    ((4, 2, 0), (0.5, 2 / 3, 0.5), 'purity weight base'),
])
def test_out_of_range_parameters_are_reported(bases, scales, problem):
    problems = color_parameter_problems(bases, scales, TETRAHEDRON_COLORS)
    assert any(problem in text for text in problems), problems


@pytest.mark.parametrize('bases, scales', [
    ((4, 2, 2), (1.0, 0.25, 0.5)),
    ((4, 2, 2), (0.01, 0.0, 0.5)),
    ((4, 3.5, 1), (0.3, 0.5, 0.75)),
    ((4, 2, 5), (0.7, 1.0, 0.99)),
])
def test_in_range_parameters_keep_colors_unique(bases, scales):
    assert color_parameter_problems(bases, scales, TETRAHEDRON_COLORS) == []
    assert distinct_colors(4, bases, scales) == {key: 256 for key in UNIQUE}


def test_tetrahedron_vertices_must_not_lie_in_a_plane():
    assert np.isclose(tetrahedron_volume(TETRAHEDRON_COLORS), 1 / 3)
    flat = [[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]]
    assert any('plane' in text for text in color_parameter_problems(DEFAULT_BASES, DEFAULT_SCALES, flat))
    outside = [[0, 0, 0], [1.2, 0, 0], [0, 1, 0], [0, 0, 1]]
    assert color_parameter_problems(DEFAULT_BASES, DEFAULT_SCALES, outside)


def test_four_colors_on_a_line_repeat_colors():
    """Why flat tetrahedra are refused: four collinear vertices give repeated colors from depth 2."""
    line = np.array([[0, 0, 0], [1 / 3] * 3, [2 / 3] * 3, [1, 1, 1]])
    counts = distinct_colors(2, colors=line)
    assert counts['tetrahedron'] < 16
