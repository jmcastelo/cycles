"""The version: one source (cycles.__version__), the changelog, the docs and the explorer stay in step."""

import re
import tomllib
from pathlib import Path

import pytest

import cycles

ROOT = Path(__file__).resolve().parents[1]
DOCS_INDEX = ROOT / 'docs' / 'es' / 'markdown' / '00_indice_y_glosario.md'


def test_the_version_is_major_minor_patch():
    assert re.fullmatch(r'\d+\.\d+\.\d+', cycles.__version__)


def test_pyproject_reads_the_version_from_the_package():
    project = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
    assert 'version' not in project['project'] and 'version' in project['project']['dynamic']
    assert project['tool']['setuptools']['dynamic']['version'] == {'attr': 'cycles.__version__'}


def test_the_changelog_describes_the_current_version_first():
    changelog = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
    versions = re.findall(r'^## (\d+\.\d+\.\d+)', changelog, flags=re.MULTILINE)
    assert versions and versions[0] == cycles.__version__
    assert versions == sorted(versions, key=lambda v: tuple(map(int, v.split('.'))), reverse=True)


def test_the_docs_describe_the_current_version():
    """The Spanish docs (docs/es) state the version they describe."""
    found = re.search(r'Versión del programa documentada: \*\*(\d+\.\d+\.\d+)\*\*', DOCS_INDEX.read_text(encoding='utf-8'))
    assert found, '00_indice_y_glosario.md must state the version it documents'
    assert found.group(1) == cycles.__version__, (
        f"the docs describe {found.group(1)}, the program is {cycles.__version__}: update them")


@pytest.mark.gui
def test_the_explorer_shows_its_version(window):
    assert window.windowTitle().endswith(f"Cycles explorer {cycles.__version__}")
    from cycles.gui.session import code_version
    assert code_version()['version'] == cycles.__version__
