from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

import tkinter as tk


@dataclass
class SpritePack:
    player1: tk.PhotoImage | None = None
    player2: tk.PhotoImage | None = None
    player3: tk.PhotoImage | None = None
    host: tk.PhotoImage | None = None
    audience: tk.PhotoImage | None = None


SPRITE_NAMES: Final[dict[str, str]] = {
    "player1": "player1.png",
    "player2": "player2.png",
    "player3": "player3.png",
    "host": "host.png",
    "audience": "audience.png",
}


def load_sprites(project_root: str | Path, *, max_width: int, max_height: int) -> SpritePack:
    """
    Tkinter PhotoImage supports PNG/GIF on modern Python builds.
    We keep it dependency-free: no Pillow.
    """
    root = Path(project_root)
    assets_dir = root / "assets"

    pack = SpritePack()
    if not assets_dir.exists():
        return pack

    for key, filename in SPRITE_NAMES.items():
        path = assets_dir / filename
        if not path.exists():
            continue
        try:
            img = tk.PhotoImage(file=str(path))
            img = _scale_to_fit(img, max_width=max_width, max_height=max_height)
            setattr(pack, key, img)
        except Exception:
            # invalid image or unsupported format
            continue

    return pack


def _scale_to_fit(img: tk.PhotoImage, *, max_width: int, max_height: int) -> tk.PhotoImage:
    w = img.width()
    h = img.height()
    if w <= 0 or h <= 0:
        return img
    if w <= max_width and h <= max_height:
        return img

    # integer downscale only (PhotoImage.subsample). Choose the smallest k that fits.
    kx = max(1, (w + max_width - 1) // max_width)
    ky = max(1, (h + max_height - 1) // max_height)
    k = max(kx, ky)
    return img.subsample(k, k)

