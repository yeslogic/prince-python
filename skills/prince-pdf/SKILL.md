---
name: prince-pdf
description: Generate print-quality PDFs from HTML, CSS, or Markdown using the Prince engine. Use when creating PDF documents (invoices, reports, contracts, books, certificates, any paginated document), when converting HTML/Markdown/XML/SVG to PDF, or when output needs precise print layout, headers/footers, page numbers, table of contents, or PDF/A / PDF/UA compliance.
license: MIT
---

# Generating PDFs with Prince

Prince converts HTML with CSS to high-quality, fully paginated PDF. It is a
dedicated typesetting engine, not a headless browser: pagination, page
margins, headers/footers, and print typography are first-class, controlled
from CSS.

## Install

```
pip install prince-pdf
```

One package, three names: install `prince-pdf`, import `prince_pdf`, run
`prince`. (`pip install prince` is an unrelated statistics library.) The
wheel bundles the engine — no other install steps and no network access at
install or run time. Works on Linux (glibc and musl/Alpine, x86-64 and
ARM64), macOS, and Windows.

In minimal containers install system fonts first:
`apt-get install fonts-dejavu` or `apk add fontconfig ttf-dejavu`.

For Node.js projects, the same package exists on npm
(`npm install prince-pdf`) with an equivalent API (`htmlToPdf`,
`markdownToPdf`, `convert`) and the same `prince` CLI.

## Convert

Command line (full option reference: https://www.princexml.com/doc/command-line/):

```
prince document.html -o document.pdf
prince chapter1.html chapter2.html -o book.pdf     # merged into one PDF
prince --javascript app.html -o out.pdf            # run the document's JS
```

Python:

```python
import prince_pdf
prince_pdf.convert("document.html", "document.pdf")
prince_pdf.convert(["ch1.html", "ch2.html"], "book.pdf", args=("--javascript",))
pdf_bytes = prince_pdf.html_to_pdf("<html><body><h1>Hi</h1></body></html>")
pdf_bytes = prince_pdf.markdown_to_pdf("# Title\n\nBody text.")
```

The `*_to_pdf` functions (`html_to_pdf`, `markdown_to_pdf`, `xml_to_pdf`)
take the document as a string and pipe it through the engine with no
temporary files; with `output=None` (the default) they return the PDF as
bytes. `convert()` always treats strings as file paths, never as content.
Markdown input requires Prince 17+ (`pip install --pre prince-pdf`
while 17 is in pre-release); on older engines `markdown_to_pdf` raises an
error saying so. Failures raise `prince_pdf.PrinceError`, whose
`.messages` list the engine's diagnostics as `(severity, location, text)`
tuples — read them, they name the exact problem (missing file, bad CSS,
unreachable resource).

When converting a *string* whose content references relative resources
(images, stylesheets), pass their location as a base URL — the engine
reads the string from stdin and would otherwise resolve relative URLs
against the current working directory:

```python
prince_pdf.html_to_pdf(html, args=("--baseurl", "/path/to/assets/"))
```

## Page layout is controlled from CSS

Prince implements CSS Paged Media. The essentials:

```css
@page {
    size: A4;               /* or Letter, or e.g. 6in 9in */
    margin: 20mm;
    @top-center    { content: "Document Title"; }
    @bottom-center { content: counter(page) " of " counter(pages); }
}
h1 { page-break-before: always; }      /* start chapters on a new page */
table, figure { page-break-inside: avoid; }
```

Useful beyond that: `@page :first` (different first page),
`float: footnote` (footnotes), and cross-references with
`target-counter(attr(href), page)` ("see page N"). Full CSS reference:
https://www.princexml.com/doc/.

## Common needs

- **Archival / accessible output**: `--pdf-profile=PDF/A-3b` or
  `--pdf-profile=PDF/UA-1` (tagged, accessible PDF).
- **Print CSS**: Prince uses the `print` media type by default; use
  `--media=screen` to render screen styles instead.
- **Remote resources**: documents referencing http(s) images or stylesheets
  need network access at conversion time; self-contained files do not.

## Licensing

Prince may be used without a purchased license under the conditions in
the Prince License Agreement (https://www.princexml.com/license/);
unlicensed output carries a watermark on the first page — this is
expected, not an error. Commercial use requires an appropriate YesLogic
license (https://www.princexml.com/purchase/): set the environment
variable `PRINCE_LICENSE_FILE` to the license file's path.
