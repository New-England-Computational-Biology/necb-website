#!/usr/bin/env python
"""Build the NECB 2026 flyer: generate QR code + render HTML to PDF.

Run inside the necb_flyer_env conda environment:

    mamba activate /data/vazquez/users/iv064/software/miniforge3/envs/necb_flyer_env
    python flyer/build.py
"""
from pathlib import Path

import qrcode
from qrcode.constants import ERROR_CORRECT_M
from weasyprint import HTML

ROOT = Path(__file__).resolve().parent
SITE_URL = "https://newenglandcompbio.org"


def build_qr() -> Path:
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(SITE_URL)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1E3A8A", back_color="white")
    out = ROOT / "qr.png"
    img.save(out)
    print(f"[ok] wrote {out} ({out.stat().st_size / 1024:.1f} KB)")
    return out


def build_pdf() -> Path:
    src = ROOT / "flyer.html"
    out = ROOT / "necb2026-flyer.pdf"
    HTML(filename=str(src)).write_pdf(str(out))
    print(f"[ok] wrote {out} ({out.stat().st_size / 1024:.1f} KB)")
    return out


if __name__ == "__main__":
    build_qr()
    build_pdf()
