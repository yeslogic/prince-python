# Release engineering

This repo contains no Prince binaries and no engine source — only packaging.

## How this repository works

- `versions.json` — the release manifest: for each wheel platform tag, the
  princexml.com artifact URL and its SHA-256. Wheels are built only from
  artifacts that verify against this manifest, so a commit of this repo
  fully determines the bytes that reach PyPI.
- `src/prince_pdf/` — the wrapper module and `prince` console script. At
  build time the engine's installation prefix is bundled as
  `prince_pdf/_bundle/`, and the wrapper invokes
  `_bundle/bin/prince --prefix=<bundle>` (the same thing the shipped
  launcher script does).
- `build_hook.py` — hatchling hook that sets the wheel's platform tag and
  pulls in the staged engine tree.
- `scripts/build_wheels.py` — download → verify → stage → build, for one
  or all platforms.
- `scripts/update_versions.py <version>` — regenerate the manifest for a
  new Prince release: downloads the artifacts, computes checksums, and
  scans the Linux binaries' `GLIBC_*` symbols so the manylinux tags stay
  honest.
- `.github/workflows/wheels.yml` — builds all wheels on one Linux runner
  (repackaging only, no compilation), smoke-tests each wheel on its real
  platform (including installing and running the full smoke test with
  networking disabled), and publishes to PyPI via trusted publishing when
  a `v*` tag is pushed. The publish job refuses tags that do not match
  the manifest's package version.

There is no musllinux x86-64 wheel yet: the Alpine engine builds link many
system libraries dynamically (declared by the `.apk`, unexpressible in a
wheel). It returns once a self-contained `linux-generic-x86_64-musl`
tarball exists, mirroring the aarch64 one.

## Building locally

```
pip install build hatchling
python scripts/build_wheels.py --platform macosx_10_13_universal2
pip install dist/prince_pdf-*.whl
python tests/smoke.py
```

## Releasing a new Prince version

1. `python scripts/update_versions.py 17`
2. Review the diff, commit, and push a tag matching the new package
   version (`v17.0.0`).
3. CI builds, tests, and publishes to PyPI. Packaging-only fixes between
   engine releases use PEP 440 post-releases: `17.0.0.post1`.

Pre-release builds map to PEP 440 versions that pip hides from ordinary
users (installed only with `--pre` or an exact version pin):

- Betas: `python scripts/update_versions.py 17b1` → package `17.0.0b1`.
- Dated builds: `python scripts/update_versions.py 20260630 --dev-of 17`
  → package `17.0.0.dev2026063000`. The `--dev-of` mapping is required — a
  raw date used as a version would sort above every real release forever.
  `.dev` versions sort *before* the release they lead to
  (`17.0.0.dev… < 17.0.0b1 < 17.0.0`), so once 17.0.0 ships, dated builds
  must target the next release: `--dev-of 17.1`.
- The dev number is `date*100 + revision`: PEP 440 puts `.devN` last, so
  post-style suffixes are impossible on dev releases and the revision must
  live inside N. A wrapper-only refresh of a dev release is
  `python scripts/update_versions.py 20260630 --dev-of 17 --rev 1`
  → `17.0.0.dev2026063001`. Stable releases use `.postN` for the same
  purpose (e.g. `16.2.0.post1`).

Publish selected milestones, not nightlies: each release uploads ~200 MB
of wheels against PyPI's default 10 GB per-project quota. Old `.dev`
releases can be deleted from PyPI to reclaim space, and quota increases
can be requested if needed.

## PyPI setup (already done; recorded for reference)

The project publishes via a PyPI trusted publisher bound to this
repository (`yeslogic/prince-python`, workflow `wheels.yml`, environment
`pypi`). The `pypi` environment exists in the GitHub repo settings;
protect it with required reviewers. No sdist is published — there is
nothing to build from source.
