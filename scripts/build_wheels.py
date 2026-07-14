#!/usr/bin/env python3
"""Build platform wheels for prince-pdf.

For each platform tag in versions.json: download the Prince release artifact
(reusing the downloads/ cache when present), verify its SHA-256 against the
manifest, stage the engine's installation prefix into staging/<tag>/, and
build a wheel tagged py3-none-<tag> into dist/.

Usage:
  python scripts/build_wheels.py                          # all platforms
  python scripts/build_wheels.py --platform win_amd64     # one platform
  python scripts/build_wheels.py --stage-only             # skip wheel build
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from _common import ROOT, discover_prefix, download, extract, load_manifest


def check_version_sync(manifest):
    pyproject = (ROOT / "pyproject.toml").read_text()
    version = re.search(r'^version = "([^"]+)"$', pyproject, re.M).group(1)
    if version != manifest["package_version"]:
        sys.exit(
            f"version mismatch: pyproject.toml has {version} but versions.json "
            f"has {manifest['package_version']} (run scripts/update_versions.py)"
        )


def stage(tag, entry, manifest):
    archive = download(entry["url"], entry["sha256"])
    staging = ROOT / "staging" / tag
    if staging.exists():
        shutil.rmtree(staging)
    with tempfile.TemporaryDirectory() as tmp:
        extract(archive, tmp)
        prefix, engine = discover_prefix(tmp)
        shutil.copytree(prefix, staging)
        # The EULA and third-party notices sit outside the prefix in the
        # Linux and macOS artifacts (the Windows prefix is the artifact
        # root, where they are already included).
        artifact_root = Path(tmp) / prefix.relative_to(tmp).parts[0]
        for name in ("LICENSE", "LICENSE.txt", "CREDITS", "CREDITS.txt", "contrib"):
            src = artifact_root / name
            if src.exists() and not (staging / name).exists():
                if src.is_dir():
                    shutil.copytree(src, staging / name)
                else:
                    shutil.copy2(src, staging / name)
    meta = {
        "engine": f"bin/{engine}",
        "prince_version": manifest["prince_version"],
        "platform": tag,
    }
    (staging / "_meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"staged {tag} (engine: {meta['engine']})")


def build(tag):
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel"],
        cwd=ROOT,
        check=True,
        env={**os.environ, "PRINCE_WHEEL_PLATFORM": tag},
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", action="append", help="platform tag(s) to build")
    parser.add_argument("--stage-only", action="store_true", help="stage but do not build")
    args = parser.parse_args()

    manifest = load_manifest()
    check_version_sync(manifest)
    tags = args.platform or list(manifest["artifacts"])
    for tag in tags:
        if tag not in manifest["artifacts"]:
            sys.exit(f"unknown platform tag {tag}; known: {', '.join(manifest['artifacts'])}")
        stage(tag, manifest["artifacts"][tag], manifest)
        if not args.stage_only:
            build(tag)

    if not args.stage_only:
        print("\nbuilt wheels:")
        for wheel in sorted((ROOT / "dist").glob("*.whl")):
            print(f"  {wheel.name}")


if __name__ == "__main__":
    main()
