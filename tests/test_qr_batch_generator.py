from __future__ import annotations

from pathlib import Path

from ae.qr_codes import generate_qr_png, batch_generate_qr_png, QrSpec


PNG_SIG = b"\x89PNG\r\n\x1a\n"


def test_generate_qr_png_writes_png(tmp_path: Path):
    out = tmp_path / "one.png"
    p = generate_qr_png("https://example.com/menu", out, box_size=2, border=1)
    fp = Path(p)
    assert fp.exists()
    data = fp.read_bytes()
    assert data[:8] == PNG_SIG


def test_batch_generate_qr_png(tmp_path: Path):
    specs = [QrSpec(key="a", data="https://example.com/a"), QrSpec(key="b", data="https://example.com/b")]
    res = batch_generate_qr_png(specs, tmp_path, box_size=2, border=1)
    assert set(res.keys()) == {"a", "b"}
    for k, p in res.items():
        fp = Path(p)
        assert fp.exists()
        assert fp.read_bytes()[:8] == PNG_SIG
