#!/usr/bin/env python3
"""Update versions.json and pyproject.toml for a new Prince release.

Downloads each release artifact from princexml.com, computes its SHA-256,
scans the generic Linux binaries for their glibc floor to derive honest
manylinux tags, and rewrites versions.json plus the version in pyproject.toml.

Usage:
  python scripts/update_versions.py 17                      # final release
  python scripts/update_versions.py 17b1                    # beta -> 17.0.0b1
  python scripts/update_versions.py 20260630 --dev-of 17    # dated pre-release
                                                            # -> 17.0.0.dev20260630

Dated pre-release builds MUST use --dev-of: without the mapping to a PEP 440
.dev version, a date like 20260630 would become a package version that sorts
above every real release forever. pip only installs pre-release and dev
versions when asked (--pre or an exact version pin), matching how the
pre-release channel is meant to be consumed.
"""

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

from _common import ROOT, download, extract, sha256

DOWNLOAD_BASE = "https://www.princexml.com/download/"

# Oldest Alpine release built for the channel; its build backs the x86_64
# musl wheel (there is no linux-generic x86_64 musl tarball). The stable and
# pre-release channels can differ - override with --alpine-oldest.
ALPINE_OLDEST = "3.19"


def pep440(prince_version, dev_of=None):
    """Map a Prince version to a PEP 440 package version.

    "17" -> "17.0.0";  "16.2" -> "16.2.0";  "17b1" -> "17.0.0b1";
    "20260630" with dev_of="17" -> "17.0.0.dev20260630".
    """

    def pad(release):
        parts = release.split(".")
        return ".".join(parts + ["0"] * (3 - len(parts)))

    if dev_of:
        return f"{pad(dev_of)}.dev{prince_version}"
    m = re.fullmatch(r"(\d+(?:\.\d+)*)(?:(a|b|rc)(\d+))?", prince_version)
    if not m:
        sys.exit(f"cannot map Prince version {prince_version!r} to PEP 440")
    release, pre_kind, pre_num = m.groups()
    if len(release) == 8 and release.isdigit():
        sys.exit(
            f"{prince_version!r} looks like a dated pre-release build; "
            "use --dev-of to map it to a .dev version"
        )
    return pad(release) + (f"{pre_kind}{pre_num}" if pre_kind else "")

# Verified against the LC_BUILD_VERSION / LC_VERSION_MIN_MACOSX load commands
# of the 16.2 universal binary (10.13 on Intel, 11.0 on ARM). Re-check with
# `otool -l lib/prince/bin/prince` if the deployment target ever changes.
MACOS_TAG = "macosx_10_13_universal2"

# musl has kept ABI compatibility within the 1.2 series (Alpine 3.13+).
MUSL = "1_2"


def glibc_floor(tarball):
    """Max GLIBC_x.y symbol version required by any binary in the tarball."""
    floor = (0, 0)
    with tempfile.TemporaryDirectory() as tmp:
        extract(tarball, tmp)
        for path in Path(tmp).rglob("*"):
            if path.is_file() and (path.name == "prince" or ".so" in path.name):
                for match in re.finditer(rb"GLIBC_(\d+)\.(\d+)", path.read_bytes()):
                    floor = max(floor, (int(match.group(1)), int(match.group(2))))
    if floor == (0, 0):
        raise RuntimeError(f"no GLIBC version symbols found in {tarball}")
    return f"{floor[0]}_{floor[1]}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="Prince version, e.g. 17, 16.2, 17b1, 20260630")
    parser.add_argument(
        "--dev-of",
        metavar="RELEASE",
        help="the upcoming release this dated pre-release build leads to, e.g. 17",
    )
    parser.add_argument("--alpine-oldest", default=ALPINE_OLDEST, metavar="X.Y")
    args = parser.parse_args()
    version = args.version

    # Map the version first: an unmappable one should fail before we
    # download ~300 MB of artifacts.
    package_version = pep440(version, args.dev_of)

    def url(filename):
        return DOWNLOAD_BASE + filename.format(v=version)

    artifacts = {}

    for arch in ("x86_64", "aarch64"):
        path = download(url("prince-{v}-linux-generic-" + arch + ".tar.gz"))
        artifacts[f"manylinux_{glibc_floor(path)}_{arch}"] = path
    artifacts[f"musllinux_{MUSL}_x86_64"] = download(
        url("prince-{v}-alpine" + args.alpine_oldest + "-x86_64.tar.gz")
    )
    artifacts[f"musllinux_{MUSL}_aarch64"] = download(
        url("prince-{v}-linux-generic-aarch64-musl.tar.gz")
    )
    artifacts[MACOS_TAG] = download(url("prince-{v}-macos.zip"))
    artifacts["win_amd64"] = download(url("prince-{v}-win64.zip"))
    artifacts["win_arm64"] = download(url("prince-{v}-win-arm64.zip"))

    manifest = {
        "prince_version": version,
        "package_version": package_version,
        "artifacts": {
            tag: {"url": DOWNLOAD_BASE + path.name, "sha256": sha256(path)}
            for tag, path in artifacts.items()
        },
    }
    (ROOT / "versions.json").write_text(json.dumps(manifest, indent=2) + "\n")

    pyproject = ROOT / "pyproject.toml"
    pyproject.write_text(
        re.sub(
            r'^version = "[^"]+"$',
            f'version = "{package_version}"',
            pyproject.read_text(),
            count=1,
            flags=re.M,
        )
    )

    print(f"updated versions.json and pyproject.toml for Prince {version}")
    print("review the diff, then commit and tag to release")


if __name__ == "__main__":
    main()
