# prince-pdf

Python packaging of [Prince](https://www.princexml.com/), the HTML-with-CSS to
PDF engine. The wheel bundles the Prince engine for the current platform — no
separate installation, no network access at install or run time.

```
pip install prince-pdf
```

```python
import prince_pdf

prince_pdf.convert("document.html", "document.pdf")

pdf_bytes = prince_pdf.html_to_pdf("<h1>Hello</h1>")        # in-memory
pdf_bytes = prince_pdf.markdown_to_pdf("# Hello")           # Prince 17+
```

The package also puts `prince` on `PATH`, so the full
[command-line interface](https://www.princexml.com/doc/command-line/) works as
documented:

```
prince document.html -o document.pdf
```

`python -m prince_pdf` also works anywhere the package is importable, even
when the script directory is not on `PATH`.

Prince is free for non-commercial use (output carries a watermark on the
first page until a license is installed). Commercial use requires a
[license from YesLogic](https://www.princexml.com/purchase/). Point the
engine at your license file with the `PRINCE_LICENSE_FILE` environment
variable (preferred — it survives reinstalls), or install it at the path
returned by `prince_pdf.license()`.

Supported platforms: Linux x86-64 and ARM64 (glibc), musl/Alpine ARM64,
macOS 10.13+ (universal), Windows x64 and ARM64. On Linux x86-64 the engine
additionally needs the system fontconfig library — in minimal containers,
`apt-get install libfontconfig1` (it usually arrives with fonts anyway).

## Names

One package, three names: install it as **`prince-pdf`**, import it as
**`prince_pdf`**, run it as **`prince`**. Note that `pip install prince`
installs an unrelated statistics library, not this package.

## Python API

- `prince_pdf.convert(inputs, output=None, args=())` — convert one or more
  files (HTML, XML, SVG; Markdown with Prince 17+; a list is merged into
  one PDF), with the format detected from each file. Extra command-line
  options go in `args`, e.g. `args=("--javascript",)`. Returns the output
  path, or the PDF as `bytes` when `output` is None.
- `prince_pdf.html_to_pdf(html, output=None, args=())`,
  `prince_pdf.markdown_to_pdf(markdown, ...)`,
  `prince_pdf.xml_to_pdf(xml, ...)` — convert a document given as a string
  or bytes, without temporary files. Combine with `output=None` for fully
  in-memory conversion. Markdown input requires a bundled Prince 17 or
  later (`pip install --pre prince-pdf` while 17 is in pre-release);
  on older engines `markdown_to_pdf` raises an error saying exactly that.
- Failures raise `PrinceError` carrying `.returncode`, raw `.stderr`, and
  `.messages` — the engine's diagnostics parsed into
  `Message(severity, location, text)` tuples. Engine warnings during
  successful conversions are emitted on the `"prince_pdf"` logger.
- `prince_pdf.run(*args, **kwargs)` — invoke the engine with raw
  command-line arguments; `kwargs` pass through to `subprocess.run()`.
- `prince_pdf.command(*args)` — the argv list that would be run, for use
  with external process tooling.
- `prince_pdf.executable()` — path of the bundled engine binary.
- `prince_pdf.version()` — the engine's version string.
- `prince_pdf.license()` — the default license-file location inside the
  bundle (prefer `PRINCE_LICENSE_FILE`, which survives reinstalls).

## Troubleshooting

- **Missing or wrong fonts in minimal containers**: the wheel bundles the
  engine but uses the system's fonts. Install some, e.g.
  `apt-get install fonts-dejavu fontconfig` (Debian/Ubuntu) or
  `apk add fontconfig ttf-dejavu` (Alpine).
- **`libfontconfig.so.1: cannot open shared object file` (Linux x86-64)**:
  install the system fontconfig library, e.g.
  `apt-get install libfontconfig1` — installing fonts as above also
  provides it.
- **Watermark on the first page**: expected without a license — the engine
  is fully functional for evaluation and non-commercial use. A purchased
  license (via `PRINCE_LICENSE_FILE`) removes it.
- **Documents referencing remote resources**: fetching `http(s)` images or
  stylesheets requires network access at conversion time; self-contained
  local files need none.
- **Diagnosing failures**: `PrinceError.stderr` carries the engine's
  warnings and errors; add `--verbose` (or `-o` plus `--log=FILE`) for more
  detail.

## How this repository works

This repo contains no Prince binaries and no engine source — only packaging.

- `versions.json` — the release manifest: for each wheel platform tag, the
  princexml.com artifact URL and its SHA-256. Wheels are built only from
  artifacts that verify against this manifest, so a commit of this repo fully
  determines the bytes that reach PyPI.
- `src/prince_pdf/` — the wrapper module and `prince` console script. At
  build time the engine's installation prefix is bundled as
  `prince_pdf/_bundle/`, and the wrapper invokes
  `_bundle/bin/prince --prefix=<bundle>` (the same thing the shipped launcher
  script does).
- `build_hook.py` — hatchling hook that sets the wheel's platform tag and
  pulls in the staged engine tree.
- `scripts/build_wheels.py` — download → verify → stage → build, for one or
  all platforms.
- `scripts/update_versions.py <version>` — regenerate the manifest for a new
  Prince release: downloads the artifacts, computes checksums, and scans the
  Linux binaries' `GLIBC_*` symbols so the manylinux tags stay honest.
- `.github/workflows/wheels.yml` — builds all wheels on one Linux runner
  (repackaging only, no compilation), smoke-tests each wheel on its real
  platform (including installing and running with networking disabled), and
  publishes to PyPI via trusted publishing when a `v*` tag is pushed.

## Building locally

```
pip install build hatchling
python scripts/build_wheels.py --platform macosx_10_13_universal2
pip install dist/prince_pdf-*.whl
python tests/smoke.py
```

## Releasing a new Prince version

1. `python scripts/update_versions.py 17`
2. Review the diff, commit, and push a tag matching the new package version
   (`v17.0.0`).
3. CI builds, tests, and publishes to PyPI. Packaging-only fixes between
   engine releases use PEP 440 post-releases: `17.0.0.post1`.

Pre-release builds map to PEP 440 versions that pip hides from ordinary
users (installed only with `--pre` or an exact version pin):

- Betas: `python scripts/update_versions.py 17b1` → package `17.0.0b1`.
- Dated builds: `python scripts/update_versions.py 20260630 --dev-of 17`
  → package `17.0.0.dev20260630`. The `--dev-of` mapping is required — a
  raw date used as a version would sort above every real release forever.
  `.dev` versions sort *before* the release they lead to
  (`17.0.0.dev20260630 < 17.0.0b1 < 17.0.0`), so once 17.0.0 ships, dated
  builds must target the next release: `--dev-of 17.1`.
- The pre-release channel may build for a different Alpine range than the
  stable channel; pass `--alpine-oldest 3.21` accordingly.

Publish selected milestones, not nightlies: each release uploads ~200 MB of
wheels against PyPI's default 10 GB per-project quota. Old `.dev` releases
can be deleted from PyPI to reclaim space, and quota increases can be
requested if needed.

One-time setup on PyPI: create the `prince-pdf` project and add a trusted
publisher for this repository (`yeslogic/prince-python`, workflow
`wheels.yml`, environment `pypi`), and create the `pypi` environment in the
GitHub repo settings (protect it with required reviewers). No sdist is
published — there is nothing to build from source.
