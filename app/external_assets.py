from __future__ import annotations

import hashlib
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ExternalAsset:
    key: str
    url: str
    filename: str


DEFAULT_ASSETS: list[ExternalAsset] = [
    ExternalAsset(
        key="player_icon",
        url="https://previews.123rf.com/images/elenvd/elenvd1703/elenvd170300004/73152195-contour-icon-standing-man-of-vector-illustration.jpg",
        filename="player_icon.jpg",
    ),
    ExternalAsset(
        key="wheel",
        url="https://bel.cultreg.ru/uploads/868de5770cd9e7dfc715dd0b92741d3d.jpeg",
        filename="wheel.jpeg",
    ),
    ExternalAsset(
        key="host",
        url="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSdU3ptPyyYXlWL5hHDRSqcLno5vUPDzaWgYA&s",
        filename="host.jpg",
    ),
]


def ensure_external_assets(project_root: str | Path) -> dict[str, Path]:
    """
    Downloads referenced images once and caches them under assets/external/.
    Returns mapping key -> local path (only for successfully present files).
    """
    root = Path(project_root)
    ext_dir = root / "assets" / "external"
    ext_dir.mkdir(parents=True, exist_ok=True)

    out: dict[str, Path] = {}
    for asset in DEFAULT_ASSETS:
        target = ext_dir / asset.filename
        if not target.exists():
            _download(asset.url, target)
        if target.exists():
            out[asset.key] = target
    return out


def _download(url: str, target: Path) -> None:
    tmp = target.with_suffix(target.suffix + ".part")
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            },
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            data = r.read()
        # tiny sanity check: don't write HTML error pages as images
        if data[:20].lstrip().startswith(b"<!DOCTYPE") or b"<html" in data[:200].lower():
            return
        tmp.write_bytes(data)
        tmp.replace(target)
    except Exception:
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass

