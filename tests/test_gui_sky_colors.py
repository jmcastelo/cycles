"""The sky chart (needs the ephemeris tables) and the color parameters dialog."""

import pytest

pytestmark = pytest.mark.gui


@pytest.mark.ephemeris
def test_the_sky_disk_keeps_its_size_as_the_axes_turn(window, spin, ephemeris):
    window.show_panel('sky')
    spin()
    sky = window.sky_panel
    sizes = []
    for year in (-3101.1, 500.0, 2026.8):
        window.state.set_sky_time(year)
        spin()
        assert sky.ax is not None
        sizes.append(round(sky.ax.get_position().width * sky.figure.bbox.width, 1))
    assert max(sizes) - min(sizes) < 1.0, sizes


@pytest.mark.ephemeris
def test_the_sky_chart_has_the_key_of_the_axis_glyphs(window, spin, ephemeris):
    window.show_panel('sky')
    window.state.set_sky_time(2026.8)
    spin()
    texts = {t.get_text() for legend in window.sky_panel.ax.findobj(lambda a: hasattr(a, 'get_texts'))
             for t in legend.get_texts()}
    assert {'equinoxes', 'solstices'} <= texts


def test_color_parameters_apply_only_when_valid(window, spin):
    from cycles.gui.colordialog import ColorDialog
    state = window.state
    dialog = ColorDialog(state, window)
    dialog.show()
    spin()
    dialog.color_base.setValue(3)
    dialog.apply()
    assert state.color_parameters[0][1] == 3
    dialog.black_scale.setValue(0.3)          # in the gap (0.25, 0.5): refused
    dialog._changed()
    dialog.apply()
    assert state.color_parameters[1][1] != 0.3
    assert 'Not applied' in dialog.problems.text()
    dialog.load(*dialog._original)
    dialog.apply()
    assert state.color_parameters[0][1] == 2
    dialog.close()


def test_two_thirds_survives_the_dialog(window, spin):
    """Fields left alone keep their exact values (2/3 is not rounded to 0.667)."""
    from cycles.gui.colordialog import ColorDialog
    dialog = ColorDialog(window.state, window)
    assert dialog.parameters()[1][1] == 2 / 3
    dialog.close()
