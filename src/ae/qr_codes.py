from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import qrcode


@dataclass(frozen=True)
class QrSpec:
    """A single QR output spec."""

    key: str
    data: str


def generate_qr_png(
    data: str,
    output_path: str | Path,
    *,
    box_size: int = 10,
    border: int = 4,
) -> str:
    """Generate a PNG QR code.

    v1: synchronous, local filesystem output.
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    img = qrcode.make(data, box_size=box_size, border=border)
    img.save(out)
    return str(out)


def batch_generate_qr_png(
    specs: Iterable[QrSpec],
    output_dir: str | Path,
    *,
    filename_prefix: str = "qr-",
    box_size: int = 10,
    border: int = 4,
) -> dict[str, str]:
    """Generate multiple PNG QR codes.

    Returns mapping: key -> file path.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, str] = {}
    for spec in specs:
        fname = f"{filename_prefix}{spec.key}.png"
        path = out_dir / fname
        results[spec.key] = generate_qr_png(spec.data, path, box_size=box_size, border=border)
    return results
