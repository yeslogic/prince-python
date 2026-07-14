"""Shared helpers for the packaging scripts."""

import hashlib
import json
import os
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path(os.environ.get("PRINCE_ARTIFACT_CACHE", ROOT / "downloads"))


def load_manifest():
    return json.loads((ROOT / "versions.json").read_text())


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url, expected_sha256=None):
    """Download url into the cache (skipping if already cached and valid)
    and verify its checksum. Returns the cached path."""
    CACHE.mkdir(parents=True, exist_ok=True)
    dest = CACHE / url.rsplit("/", 1)[1]
    cached_ok = dest.exists() and (
        expected_sha256 is None or sha256(dest) == expected_sha256
    )
    if not cached_ok:
        print(f"downloading {url}")
        tmp = dest.with_suffix(dest.suffix + ".part")
        with urllib.request.urlopen(url) as resp, open(tmp, "wb") as out:
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk)
        tmp.replace(dest)
    if expected_sha256:
        actual = sha256(dest)
        if actual != expected_sha256:
            dest.unlink()
            raise RuntimeError(
                f"checksum mismatch for {url}:\n"
                f"  expected {expected_sha256}\n"
                f"  actual   {actual}"
            )
    return dest


def extract(archive, dest):
    """Extract a .tar.gz or .zip, preserving executable permission bits."""
    archive = Path(archive)
    if archive.name.endswith((".tar.gz", ".tgz")):
        with tarfile.open(archive) as tf:
            try:
                tf.extractall(dest, filter="tar")
            except TypeError:  # Python < 3.12 has no filter argument
                tf.extractall(dest)
    elif archive.name.endswith(".zip"):
        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                extracted = zf.extract(info, dest)
                mode = (info.external_attr >> 16) & 0o7777
                if mode:
                    os.chmod(extracted, mode)
    else:
        raise ValueError(f"unsupported archive format: {archive.name}")


def discover_prefix(extract_dir):
    """Locate the Prince installation prefix inside an extracted artifact.

    The engine binary lives at <prefix>/bin/prince (or prince.exe); shell
    launcher scripts of the same name are excluded by taking the largest
    candidate. Returns (prefix_path, engine_filename).
    """
    candidates = [
        p
        for p in Path(extract_dir).rglob("*")
        if p.is_file() and p.name in ("prince", "prince.exe") and p.parent.name == "bin"
    ]
    if not candidates:
        raise RuntimeError(f"no prince engine binary found under {extract_dir}")
    engine = max(candidates, key=lambda p: p.stat().st_size)
    return engine.parent.parent, engine.name
