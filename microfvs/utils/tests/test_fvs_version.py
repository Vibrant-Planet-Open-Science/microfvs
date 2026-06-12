import re
import shutil
from pathlib import Path

import pytest

from microfvs.enums import FvsVariant
from microfvs.utils.fvs_version import get_fvs_version, get_fvs_versions


@pytest.mark.parametrize("variant", FvsVariant)
def test_get_fvs_version_from_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    variant: FvsVariant,
):
    """FVS binaries are detected on PATH."""
    fvs_name = f"FVS{variant.lower()}"
    assert shutil.which(fvs_name) is not None
    assert not (tmp_path / fvs_name).exists()

    monkeypatch.chdir(tmp_path)
    version = get_fvs_version(variant)

    assert version != "not installed"
    assert re.fullmatch(r"\d{8}", version)


def test_get_fvs_versions(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    versions = get_fvs_versions()

    assert len(versions) == len(FvsVariant)
    assert all(v != "not installed" for v in versions.values())
