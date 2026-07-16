#!/usr/bin/env python3
"""Smoke test for an installed prince-pdf wheel.

Checks that the bundled engine runs and (unless --version-only) converts an
HTML document to a well-formed PDF. --version-only exists for environments
without fonts or network, where a conversion is not meaningful.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import prince_pdf

HTML = """<html>
  <head><title>prince-pdf smoke test</title></head>
  <body>
    <h1>prince-pdf smoke test</h1>
    <p>If this document converts to a well-formed PDF, the bundled engine,
    its prefix resolution, and its resource tree are all working.</p>
  </body>
</html>
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version-only", action="store_true")
    args = parser.parse_args()

    print(f"engine: {prince_pdf.executable()}")
    version = prince_pdf.version()
    print(f"version: {version}")
    assert version.startswith("Prince "), f"unexpected version output: {version!r}"

    cli = shutil.which("prince")
    assert cli, "prince console script not found on PATH"
    out = subprocess.run([cli, "--version"], capture_output=True, text=True, check=True)
    assert out.stdout.startswith("Prince "), f"unexpected CLI output: {out.stdout!r}"
    print(f"cli: {cli}")

    out = subprocess.run(
        [sys.executable, "-m", "prince_pdf", "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert out.stdout.startswith("Prince "), f"unexpected -m output: {out.stdout!r}"
    print("python -m prince_pdf: ok")

    if not args.version_only:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "in.html"
            src.write_text(HTML)
            pdf = prince_pdf.convert(src, Path(tmp) / "out.pdf")
            data = pdf.read_bytes()
        assert data[:5] == b"%PDF-", f"output does not look like a PDF: {data[:16]!r}"
        assert len(data) > 1000, f"suspiciously small PDF ({len(data)} bytes)"
        print(f"converted test document: {len(data)} byte PDF")

        data = prince_pdf.html_to_pdf(HTML)
        assert data[:5] == b"%PDF-", f"html_to_pdf output: {data[:16]!r}"
        print(f"html_to_pdf (in-memory): {len(data)} byte PDF")

        try:
            data = prince_pdf.markdown_to_pdf("# Smoke test\n\nMarkdown *works*.\n")
        except RuntimeError as exc:
            # Engines before Prince 17 have no Markdown support; the wrapper
            # must say so instead of surfacing a misleading XML parse error.
            assert "Prince 17" in str(exc), f"unhelpful markdown error: {exc}"
            print("markdown_to_pdf: no engine support, guarded correctly")
        else:
            assert data[:5] == b"%PDF-", f"markdown_to_pdf output: {data[:16]!r}"
            print(f"markdown_to_pdf: {len(data)} byte PDF")

        if os.name == "posix":
            # A separately installed Prince, emulated by a launcher script
            # of the same shape system installations use (exec with
            # --prefix).
            with tempfile.TemporaryDirectory() as tmp:
                engine = prince_pdf.executable()
                launcher = Path(tmp) / "prince"
                launcher.write_text(
                    f'#!/bin/sh\nexec "{engine}" '
                    f'--prefix="{engine.parent.parent}" "$@"\n'
                )
                launcher.chmod(0o755)
                data = prince_pdf.html_to_pdf(HTML, executable=launcher)
                assert data[:5] == b"%PDF-", "external engine via executable="
                os.environ["PRINCE_PATH"] = str(launcher)
                try:
                    assert prince_pdf.executable() == launcher
                    v = prince_pdf.version()
                    assert v.startswith("Prince "), f"via PRINCE_PATH: {v!r}"
                finally:
                    del os.environ["PRINCE_PATH"]
                try:
                    prince_pdf.html_to_pdf(HTML, executable=tmp)
                except RuntimeError as exc:
                    assert "not a directory" in str(exc), exc
                else:
                    raise AssertionError("directory executable= not rejected")
            print("external engine (executable=, PRINCE_PATH): ok")

        try:
            prince_pdf.convert([])
        except ValueError as exc:
            assert "at least one path" in str(exc), exc
            print("empty inputs rejected with ValueError")
        else:
            raise AssertionError("convert([]) did not raise")

        try:
            prince_pdf.convert("/nonexistent/input.html")
        except prince_pdf.PrinceError as exc:
            assert exc.messages, "expected parsed engine messages on failure"
            assert exc.messages[0].severity == "err", exc.messages
            print(f"error reporting: {exc.messages[0].text!r}")
        else:
            raise AssertionError("conversion of a missing file did not fail")

        seen = []
        try:
            prince_pdf.convert("/nonexistent/input.html", on_message=seen.append)
        except prince_pdf.PrinceError:
            pass
        assert seen and seen[0].severity == "err", seen
        def raising_callback(message):
            raise ValueError(message)

        try:
            prince_pdf.convert("/nonexistent/input.html", on_message=raising_callback)
        except ValueError:
            print("on_message: diagnostics delivered, exceptions propagate")
        else:
            raise AssertionError("on_message exception did not propagate")

    print("smoke test passed")


if __name__ == "__main__":
    sys.exit(main())
