# prince-pdf

Python packaging of [Prince](https://www.princexml.com/), the HTML-with-CSS
to PDF engine. The wheel bundles the Prince engine for the current platform:
no separate installation, and neither installing the package nor launching
the engine downloads anything. (Prince will access the network only if a
document being converted references remote resources such as images or
stylesheets.)

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
[command-line interface](https://www.princexml.com/doc/command-line/) works
as documented:

```
prince document.html -o document.pdf
```

`python -m prince_pdf` also works anywhere the package is importable, even
when the script directory is not on `PATH`.

## Names

One package, three names: install it as **`prince-pdf`**, import it as
**`prince_pdf`**, run it as **`prince`**. Note that `pip install prince`
installs an unrelated statistics library, not this package.

## Files vs. strings

`convert()` always interprets strings as filesystem paths, never as
document content. To convert an HTML string, use `html_to_pdf()`.

The `*_to_pdf` functions pipe the document through the engine's standard
input, so the engine never sees a filename: relative URLs in the document
are resolved against the current working directory, not against wherever
the content originally came from. If a string derived from
`/tmp/report/index.html` references `images/chart.svg`, pass the original
location as a base URL:

```python
prince_pdf.html_to_pdf(html, args=("--baseurl", "/tmp/report/"))
```

## Python API

The package ships inline type annotations (`py.typed`).

- `prince_pdf.convert(inputs, output=None, args=())` — convert one or more
  files (HTML, XML, SVG; Markdown with Prince 17+; a list is merged into
  one PDF), with the format detected from each file. Extra command-line
  options go in `args` as a sequence of individual argument tokens —
  `args=("--baseurl", "https://x.example/")`, never a shell string like
  `"--baseurl https://x.example/"`. Returns the output path, or the PDF
  as `bytes` when `output` is None.
- `prince_pdf.html_to_pdf(html, output=None, args=())`,
  `prince_pdf.markdown_to_pdf(markdown, ...)`,
  `prince_pdf.xml_to_pdf(xml, ...)` — convert a document given as a string
  or bytes, without temporary files. Markdown input requires a bundled
  Prince 17 or later (`pip install --pre prince-pdf` while 17 is in
  pre-release); on older engines `markdown_to_pdf` raises an error saying
  exactly that.
- Failures raise `PrinceError` carrying `.returncode`, raw `.stderr`, and
  `.messages` — the engine's diagnostics parsed into
  `Message(severity, location, text)` tuples. Engine warnings during
  successful conversions are emitted on the `"prince_pdf"` logger.
- `prince_pdf.run(*args, **kwargs)` — a thin `subprocess.run()` wrapper
  for raw engine access. It does **not** apply the error handling or
  diagnostic parsing that `convert()` provides: nonzero exits do not
  raise (pass `check=True` for `CalledProcessError`), and output is not
  captured unless requested.
- `prince_pdf.command(*args)` — the argv list that would be run, for use
  with external process tooling (same caveats as `run()`).
- `prince_pdf.executable()` — path of the bundled engine binary.
- `prince_pdf.version()` — the engine's version string.
- `prince_pdf.license()` — the default license-file location inside the
  bundle (prefer `PRINCE_LICENSE_FILE`, which survives reinstalls).

## Licensing

Prince may be used without a purchased license under the conditions in the
included Prince License Agreement (`LICENSE-Prince.txt`); unlicensed output
carries a watermark on the first page. Commercial use requires an
appropriate [license from YesLogic](https://www.princexml.com/purchase/).
Point the engine at your license file with the `PRINCE_LICENSE_FILE`
environment variable (preferred — it survives reinstalls), or install it
at the path returned by `prince_pdf.license()`. The Python wrapper code
itself is MIT-licensed (`LICENSE`).

## Troubleshooting

- **Missing or wrong fonts in minimal containers**: the wheel bundles the
  engine but uses the system's fonts. Install some, e.g.
  `apt-get install fonts-dejavu fontconfig` (Debian/Ubuntu) or
  `apk add fontconfig ttf-dejavu` (Alpine).
- **`libfontconfig.so.1: cannot open shared object file` (Linux x86-64)**:
  install the system fontconfig library, e.g.
  `apt-get install libfontconfig1` — installing fonts as above also
  provides it.
- **Watermark on the first page**: expected without a license — see
  Licensing above.
- **Documents referencing remote resources**: fetching `http(s)` images or
  stylesheets requires network access at conversion time; self-contained
  local files need none.
- **Diagnosing failures**: `PrinceError.stderr` carries the engine's
  warnings and errors; add `--verbose` (or `-o` plus `--log=FILE`) for
  more detail.

## Supported platforms

Linux x86-64 and ARM64 (glibc), musl/Alpine ARM64, macOS 10.13+
(universal), Windows x64 and ARM64. On Linux x86-64 the engine
additionally needs the system fontconfig library — in minimal containers,
`apt-get install libfontconfig1` (it usually arrives with fonts anyway).

---

Maintainer documentation — how wheels are built, verified, and released —
is in [RELEASING.md](RELEASING.md).
