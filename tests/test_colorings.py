"""The colorings beyond the address: OKLab, duration classes, measures and the vernal point."""

import numpy as np
import pytest

from cycles.functions.color import (
    ELEMENT_COLORS, duration_class_colors, measure_colors, oklab_tetrahedron, oklab_to_srgb, srgb_to_oklab,
    vernal_colors, vernal_point_longitude,
)
from cycles.functions.division import (
    COLOR_DESCRIPTIONS, COLOR_KEYS, LEVEL_COLOR_KEYS, MEASURE_COLOR_KEYS, MODEL_COLOR_KEYS, TETRAHEDRON_COLORS,
    compute_level, level_colors,
)


def test_every_coloring_is_described_once():
    assert len(set(COLOR_KEYS)) == len(COLOR_KEYS) == len(LEVEL_COLOR_KEYS) + len(MEASURE_COLOR_KEYS) + 3
    assert set(COLOR_DESCRIPTIONS) == set(COLOR_KEYS)


def test_oklab():
    lab = srgb_to_oklab([[1, 1, 1], [0, 0, 0], [1, 0, 0]])
    assert np.allclose(lab[0], [1, 0, 0], atol=1e-4) and np.allclose(lab[1], 0)
    assert np.allclose(lab[2], [0.628, 0.2249, 0.1258], atol=1e-3)                   # Ottosson's red
    rgb = np.random.default_rng(1).uniform(0, 1, (500, 3))
    assert np.allclose(oklab_to_srgb(srgb_to_oklab(rgb)), rgb, atol=1e-9)


def test_the_oklab_tetrahedron_is_even_and_inside_the_gamut():
    vertices = oklab_tetrahedron(TETRAHEDRON_COLORS, 0.5)
    full = srgb_to_oklab(TETRAHEDRON_COLORS)
    shrink = np.linalg.norm(vertices - vertices.mean(0), axis=1) / np.linalg.norm(full - full.mean(0), axis=1)
    assert np.allclose(shrink, shrink[0]) and 0.95 < shrink[0] < 1                # the same factor for all
    level = compute_level(6)
    lab = srgb_to_oklab(level_colors(level)['tetrahedron_oklab'])
    raw = oklab_to_srgb(lab)
    assert np.all((raw > -1e-6) & (raw < 1 + 1e-6))                                  # nothing clipped
    # the four regions of the last digit look equally large (in RGB the largest is a quarter larger)
    spreads = [np.linalg.norm(g - g.mean(0), axis=1).mean() for g in (lab[level.lcoords[:, -1] == a] for a in range(4))]
    assert max(spreads) / min(spreads) < 1.01
    rgb = srgb_to_oklab(level_colors(level)['tetrahedron'])
    spreads = [np.linalg.norm(g - g.mean(0), axis=1).mean() for g in (rgb[level.lcoords[:, -1] == a] for a in range(4))]
    assert max(spreads) / min(spreads) > 1.2


def test_duration_classes():
    level = compute_level(5)
    colors = level_colors(level)['duration_class']
    same_color = np.all(np.isclose(colors[:, None], colors[None]), axis=2)
    same_duration = np.isclose(level.durations[:, None], level.durations[None], rtol=1e-9, atol=0)
    assert np.array_equal(same_color, same_duration)                    # one color per class, 36 classes
    assert len(np.unique(np.round(colors, 9), axis=0)) == 36
    assert np.allclose(duration_class_colors([0.4, 0.4, 0.1])[0], duration_class_colors([0.4, 0.4, 0.1])[1])


def test_measure_colors():
    signed, mappable = measure_colors(np.array([-1.0, 0.0, 1.0]), 'trend')
    assert np.allclose(signed[1], signed[1].mean(), atol=0.05)          # 0 is the neutral middle of RdBu
    assert signed[0][2] > signed[0][0] and signed[2][0] > signed[2][2]  # − blue, + red
    assert mappable.norm.vmin == -1 and mappable.norm.vmax == 1
    _, density = measure_colors(np.array([0.97, 1.02]), 'density')
    assert np.isclose(density.norm.vmin + density.norm.vmax, 2)         # centred on the mean rate


def test_the_vernal_point():
    # today the vernal point is in sidereal Pisces (water); at the start of the Kali, in Taurus (earth)
    assert np.isclose(vernal_point_longitude([23.85])[0], 336.15)
    assert np.allclose(vernal_colors([23.85], 'element'), ELEMENT_COLORS[3])
    assert np.allclose(vernal_colors([-45.0], 'element'), ELEMENT_COLORS[1])
    signs = vernal_colors(-np.arange(12) * 30.0 - 15, 'sign')
    assert len(np.unique(np.round(signs, 6), axis=0)) == 12


@pytest.mark.gui
def test_the_colorings_in_the_explorer(window, spin):
    from cycles.functions.color import measure_colors
    state = window.state
    trend = state.colors(3, 'trend')
    assert np.allclose(trend, measure_colors(state.cache.measure(3, 'trend'), 'trend')[0])
    # with the default model the vernal point at the start of the Kali (3102 BC) is in Taurus: earth
    kali = 3 * 16
    assert np.allclose(state.colors(3, 'vernal_element')[kali], ELEMENT_COLORS[1])
    years = state.time_map.to_physical(state.cache.level(3).starts)
    longitudes = vernal_point_longitude(state.model.ayanamsa(np.asarray(years)))
    assert np.array_equal(state.colors(3, 'vernal_element'), ELEMENT_COLORS[(longitudes // 30).astype(int) % 4])
    model = state.model
    state.set_model(None)
    assert np.allclose(state.colors(3, 'vernal_sign'), 0.85)              # gray without a model
    for key in MODEL_COLOR_KEYS:
        window.color_box.setCurrentText(key)
        spin()
        assert state.color_key == key
    state.select((3, 0, 1))
    spin()
    row = COLOR_KEYS.index('vernal_sign')
    assert window.inspector.colors.item(row, 1).text() == 'needs a cycle model'
    state.set_model(model)
    spin()
    assert window.inspector.colors.item(row, 1).text().startswith('#')
    for key in COLOR_KEYS:                                               # every coloring paints the navigator
        window.color_box.setCurrentText(key)
        spin()
        window.navigator.repaint()
    assert window.color_box.count() == len(COLOR_KEYS) + 2                 # two separators
