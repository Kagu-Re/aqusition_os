from pathlib import Path
import re

import ae


def test_version_ssot_consistency():
    root = Path(__file__).resolve().parents[1]

    v_ops = (root / "ops" / "VERSION.txt").read_text(encoding="utf-8").strip()

    pyproj = (root / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'version\s*=\s*"([0-9.]+)"', pyproj)
    assert m, "pyproject.toml missing version"
    v_py = m.group(1)

    v_init = ae.__version__

    assert v_ops == v_py == v_init
