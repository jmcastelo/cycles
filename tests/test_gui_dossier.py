"""The subcycle dossier: its summary, the PDF with the chosen paper and sections, and the dialog."""

import re

import pytest

pytestmark = pytest.mark.gui


def _pages(path) -> int:
    return len(re.findall(rb'/Type\s*/Page[^s]', path.read_bytes()))


def _media_box(path) -> tuple[float, float]:
    x0, y0, x1, y1 = map(float, re.search(rb'/MediaBox\s*\[([^\]]+)\]', path.read_bytes()).group(1).split())
    return x1 - x0, y1 - y0


@pytest.fixture
def selected(window, spin):
    state = window.state
    state.set_focus((3,))
    state.select((3, 1, 2))
    state.add_bookmark((3, 1, 2), 'seed', 'a note on it')
    state.set_notes('What this session is about.')
    window.landscape_panel.resolution.setCurrentIndex(0)
    spin()
    return window


def test_the_summary_has_what_the_inspector_shows(selected):
    from cycles.gui.dossier import notes_html, summary_html
    text = summary_html(selected, (3, 1, 2))
    for expected in ('Kali › Treta › Dvapara', '20 Aug AD 881', '388.3 years', 'Measures by level', 'Dharma +',
                     'cmyk_normalised (shown)', 'seed', 'a note on it', 'Kali 3102 BC, midnight at Ujjain (a preset)',
                     'Code: '):
        assert expected in text, expected
    notes = notes_html(selected.state)
    assert 'What this session is about.' in notes and 'seed' in notes


def test_a_dossier_with_every_section(selected, tmp_path):
    from cycles.gui.dossier import SECTIONS, DossierOptions, write_dossier
    panel = selected.skycompare_panel
    size = panel.figure.get_size_inches().copy()
    path = tmp_path / 'all.pdf'
    sections = tuple(key for key in SECTIONS if key != 'sky' or selected.sky_panel.tables)
    pages = write_dossier(selected, (3, 1, 2), DossierOptions(path=path, sections=sections))
    assert _pages(path) == pages >= len(sections)
    width, height = _media_box(path)
    assert abs(width - 595.3) < 1 and abs(height - 841.9) < 1          # A4 portrait, in points
    assert (panel.figure.get_size_inches() == size).all()               # the panels keep their size on screen


def test_the_dialog_writes_on_the_chosen_paper(selected, spin, tmp_path):
    from cycles.gui.dossier import DossierDialog
    dialog = DossierDialog(selected)
    assert dialog.path.text().endswith('dossier-KTD.pdf')
    dialog.paper.setCurrentText('A5')
    dialog.orientation.setCurrentIndex(1)                              # landscape
    dialog.graphs.setCurrentIndex(dialog.graphs.findData('image'))
    dialog.dpi.setValue(100)
    for key, box in dialog.sections.items():
        box.setChecked(key in ('summary', 'navigator', 'measures'))
    dialog.open_after.setChecked(False)
    dialog.path.setText(str(tmp_path / 'small.pdf'))
    assert dialog.write()
    path = tmp_path / 'small.pdf'
    width, height = _media_box(path)
    assert abs(width - 595.3) < 1 and abs(height - 419.5) < 1          # A5 landscape
    assert _pages(path) >= 3 and 'Wrote' in dialog.status.text()
    again = DossierDialog(selected)                                     # the options are remembered
    assert again.paper.currentText() == 'A5' and again.orientation.currentIndex() == 1
    assert [k for k, box in again.sections.items() if box.isChecked()] == ['summary', 'navigator', 'measures']
    selected.state.select(None)
    again.refresh()
    assert not again.write_button.isEnabled() and not again.write()
