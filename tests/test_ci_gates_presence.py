from pathlib import Path


def test_ci_gate_script_exists():
    root = Path(__file__).resolve().parents[1]
    p = root / 'ops' / 'ci_release_gates.py'
    assert p.exists()
