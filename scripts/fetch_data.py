"""Download the public inputs used by this repo into data/raw/.

Sources (both public, no login):
  * NeuroConv/Neo's Blackrock test recordings on G-Node GIN
    (https://gin.g-node.org/NeuralEnsemble/ephy_testing_data), set blackrock_2_1:
    a 2.1-spec .ns5 (30 kHz), .ns2, .nev, and MATLAB exports of the same files.
  * One session of DANDI:000004 (Chandravadia et al. 2020, human MTL single
    neurons during a recognition-memory task), already in NWB.

Writes data/raw/MANIFEST.json with each file's size and SHA-256.
Stdlib only, so it runs before the environment is installed.
"""
from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

GIN = "https://gin.g-node.org/NeuralEnsemble/ephy_testing_data/raw/master/blackrock/"
BLACKROCK_FILES = [
    "blackrock_2_1/l101210-001.ns5",
    "blackrock_2_1/l101210-001.ns2",
    "blackrock_2_1/l101210-001.nev",
    "blackrock_2_1/l101210-001.mat",  # MATLAB export of the .nev + .ns2
    "blackrock_2_1/l101210-001_nev-02_ns5.mat",  # MATLAB export incl. the .ns5
]

DANDI_VERSION = "0.220126.1852"
DANDI_ASSET = {
    "path": "sub-P19HMH/sub-P19HMH_ses-20080601_obj-uw5up9_ecephys+image.nwb",
    "asset_id": "5b2d5087-4a72-42ac-866a-4e7d53811414",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "blackrock-nwb-roundtrip/0.1"})
    with urllib.request.urlopen(req, timeout=120) as r, tmp.open("wb") as f:
        expected = r.headers.get("Content-Length")
        n = 0
        for chunk in iter(lambda: r.read(1 << 20), b""):
            f.write(chunk)
            n += len(chunk)
    if expected is not None and int(expected) != n:
        tmp.unlink(missing_ok=True)
        raise IOError(f"{url}: got {n} bytes, expected {expected}")
    tmp.replace(dest)


def main() -> int:
    manifest = {}
    jobs = [(GIN + f, RAW / "blackrock" / Path(f).name) for f in BLACKROCK_FILES]
    jobs.append(
        (
            f"https://api.dandiarchive.org/api/assets/{DANDI_ASSET['asset_id']}/download/",
            RAW / "dandi_000004" / Path(DANDI_ASSET["path"]).name,
        )
    )
    for url, dest in jobs:
        if not dest.exists():
            print(f"downloading {dest.name} ...", flush=True)
            download(url, dest)
        manifest[str(dest.relative_to(ROOT)).replace("\\", "/")] = {
            "source": url,
            "bytes": dest.stat().st_size,
            "sha256": sha256(dest),
        }
        print(f"  ok {dest.name}: {dest.stat().st_size:,} bytes", flush=True)
    manifest["_dandi"] = {"dandiset": "000004", "version": DANDI_VERSION, **DANDI_ASSET}
    (RAW / "MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
