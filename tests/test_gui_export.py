"""Saving graphs: paper sizes, formats and resolution, and the panels keep their size on screen."""

import re

import pytest

pytestmark = pytest.mark.gui

A6 = (148.0 / 25.4, 105.0 / 25.4)      # inches, landscape
DPI = 100


@pytest.fixture
def dialog(window, spin):
    window.state.set_focus((3,))
    window.state.select((3, 1, 2))
    window.save_graph('measures')
    spin()
    d = window.export_dialog
    d.paper.setCurrentText('A5')
    d.orientation.setCurrentText('Landscape')
    d.width.setValue(148)
    d.height.setValue(105)          # custom: A6 landscape
    d.margin.setValue(5)
    d.dpi.setValue(DPI)
    d.title_box.setChecked(True)
    return d


def save(dialog, path, key, fmt, transparent=False):
    dialog.select(key)
    dialog.format.setCurrentIndex(dialog.format.findData(fmt))
    dialog.background.setCurrentText('Transparent' if transparent else 'White')
    dialog.path.setText(str(path / f"{key}.{fmt}"))
    dialog.save()
    out = path / f"{key}.{fmt}"
    assert out.exists() and out.stat().st_size > 500, dialog.status.text()
    return out


def test_the_dialog_converts_sizes_and_units(window, spin):
    window.save_graph('measures')
    d = window.export_dialog
    d.paper.setCurrentText('A4')
    d.orientation.setCurrentText('Landscape')
    assert abs(d.width.value() - 297) < 0.1 and abs(d.height.value() - 210) < 0.1
    d.orientation.setCurrentText('Portrait')
    assert abs(d.width.value() - 210) < 0.1
    d.unit.setCurrentText('cm')
    assert abs(d.width.value() - 21) < 0.01
    d.unit.setCurrentText('mm')
    d.width.setValue(200)
    assert d.paper.currentText() == 'Custom'


@pytest.mark.parametrize('key', ['navigator', 'measures', 'colorspace', 'permutations', 'compositions'])
def test_graphs_are_saved_in_every_format(dialog, tmp_path, key):
    from PySide6.QtGui import QImage
    for fmt in ('png', 'jpg', 'pdf', 'svg') + (('eps',) if key != 'navigator' else ()):
        out = save(dialog, tmp_path, key, fmt)
        if fmt in ('png', 'jpg'):
            image = QImage(str(out))
            # Matplotlib truncates the pixel size, Qt rounds it
            assert abs(image.width() - A6[0] * DPI) < 1 and abs(image.height() - A6[1] * DPI) < 1
        if fmt == 'pdf':
            box = re.search(rb'/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)', out.read_bytes())
            assert abs(float(box[3]) / 72 * 25.4 - 148) < 1 and abs(float(box[4]) / 72 * 25.4 - 105) < 1


def test_backgrounds(dialog, tmp_path):
    from PySide6.QtGui import QImage
    white = save(dialog, tmp_path, 'measures', 'png')
    assert QImage(str(white)).pixelColor(1, 1).name() == '#ffffff'
    clear = save(dialog, tmp_path, 'colorspace', 'png', transparent=True)
    assert QImage(str(clear)).pixelColor(1, 1).alpha() == 0


def test_panels_keep_their_size_on_screen(window, dialog, tmp_path, spin):
    panels = [window.measures_panel, window.colorspace_panel, window.permutations_panel]
    before = [tuple(p.figure.get_size_inches()) for p in panels]
    for key in ('measures', 'colorspace', 'permutations'):
        save(dialog, tmp_path, key, 'png')
    spin()
    assert [tuple(p.figure.get_size_inches()) for p in panels] == before


def test_file_names_follow_the_graph_and_the_format(dialog, tmp_path):
    dialog.select('measures')
    dialog.path.setText(str(tmp_path / 'measures.png'))
    dialog.select('colorspace')
    assert dialog.path.text().endswith('colorspace.png')
    dialog.format.setCurrentIndex(dialog.format.findData('pdf'))
    assert dialog.path.text().endswith('colorspace.pdf')
    dialog.select('navigator')
    assert dialog.format.findData('eps') == -1


def test_too_large_margins_are_refused(dialog, tmp_path):
    dialog.margin.setValue(60)
    dialog.path.setText(str(tmp_path / 'measures.png'))
    dialog.save()
    assert not (tmp_path / 'measures.png').exists()
    assert 'too little room' in dialog.status.text()
