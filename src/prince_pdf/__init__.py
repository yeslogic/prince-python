"""Python packaging of the Prince PDF engine (https://www.princexml.com/).

The Prince engine is bundled inside this package; no separate installation
is required. Free for non-commercial use (output carries a watermark on the
first page until a license is installed); commercial use requires a license
from YesLogic. See https://www.princexml.com/purchase/ and the license()
function below.

Basic usage:

    import prince_pdf
    prince_pdf.convert("document.html", "document.pdf")
    pdf_bytes = prince_pdf.html_to_pdf("<h1>Hello</h1>")
    pdf_bytes = prince_pdf.markdown_to_pdf("# Hello")   # Prince 17+

or from the command line:

    prince document.html -o document.pdf
"""

import collections
import json
import logging
import os
import re
import subprocess
from pathlib import Path

__all__ = [
    "Message",
    "PrinceError",
    "command",
    "convert",
    "executable",
    "html_to_pdf",
    "license",
    "markdown_to_pdf",
    "run",
    "version",
    "xml_to_pdf",
]

_log = logging.getLogger("prince_pdf")

#: One engine diagnostic, parsed from structured log output.
#: severity is "err", "wrn", "inf" or "dbg"; location is the resource
#: (file or URL) the message refers to.
Message = collections.namedtuple("Message", ["severity", "location", "text"])

try:
    from importlib.metadata import version as _dist_version

    __version__ = _dist_version("prince-pdf")
except Exception:  # pragma: no cover - source checkout or Python < 3.8
    __version__ = "unknown"

_BUNDLE = Path(__file__).resolve().parent / "_bundle"


class PrinceError(RuntimeError):
    """Raised when a conversion fails.

    messages holds the engine's parsed diagnostics (Message tuples);
    stderr holds its raw log output.
    """

    def __init__(self, returncode, stderr, messages=()):
        self.returncode = returncode
        self.stderr = stderr or ""
        self.messages = list(messages)
        errors = [m for m in self.messages if m.severity == "err"]
        if errors:
            detail = "\n".join(
                f"{m.location}: {m.text}" if m.location else m.text
                for m in errors
            )
        else:
            detail = self.stderr.strip()
        message = f"prince exited with status {returncode}"
        if detail:
            message += "\n" + detail
        super().__init__(message)


def _meta():
    path = _BUNDLE / "_meta.json"
    if not path.is_file():
        raise RuntimeError(
            "No bundled Prince engine found. prince-pdf was imported from a "
            "source checkout; install a built wheel (pip install prince-pdf) "
            "or build one with scripts/build_wheels.py."
        )
    return json.loads(path.read_text())


def executable():
    """Path to the bundled Prince engine binary."""
    return _BUNDLE / _meta()["engine"]


def command(*args):
    """The full argv used to invoke the bundled engine with *args*.

    If the PRINCE_LICENSE_FILE environment variable is set, the engine is
    pointed at that license file; this avoids writing into site-packages,
    which may not be writable and is replaced on every reinstall.
    """
    argv = [str(executable()), f"--prefix={_BUNDLE}"]
    license_file = os.environ.get("PRINCE_LICENSE_FILE")
    if license_file:
        argv.append(f"--license-file={license_file}")
    argv.extend(args)
    return argv


def run(*args, **kwargs):
    """Invoke Prince with *args*; returns subprocess.CompletedProcess.

    Keyword arguments are passed through to subprocess.run().
    """
    return subprocess.run(command(*args), **kwargs)


def _parse_structured_log(stderr):
    """Parse --structured-log=normal output into (messages, final_status)."""
    messages, final = [], None
    for line in stderr.splitlines():
        if line.startswith("msg|"):
            parts = line.split("|", 3)
            if len(parts) == 4:
                messages.append(Message(parts[1], parts[2], parts[3]))
        elif line.startswith("fin|"):
            final = line.split("|", 1)[1]
    return messages, final


def _convert(cli_args, output, stdin=None):
    proc = run(
        "--structured-log=normal",
        *cli_args,
        "-o",
        "-" if output is None else str(output),
        input=stdin,
        capture_output=True,
    )
    stderr = proc.stderr.decode("utf-8", errors="replace")
    messages, final = _parse_structured_log(stderr)
    for m in messages:
        if m.severity == "wrn":
            _log.warning("%s: %s", m.location, m.text)
    if proc.returncode != 0 or final == "failure":
        raise PrinceError(proc.returncode, stderr, messages)
    return proc.stdout if output is None else Path(output)


def convert(inputs, output=None, *, args=()):
    """Convert one or more input files to a PDF.

    Formats are detected per file: HTML, XML, SVG, and (with a bundled
    Prince 17 or later) Markdown.

    inputs: a path, or a list of paths merged into one PDF.
    output: the PDF path to write, or None to return the PDF as bytes.
    args:   extra command-line arguments, e.g. ("--javascript",).

    Returns the output path (or the PDF bytes when output is None).
    Raises PrinceError on failure; engine warnings are emitted on the
    "prince_pdf" logger.
    """
    if isinstance(inputs, (str, os.PathLike)):
        inputs = [inputs]
    return _convert([*args, *[str(p) for p in inputs]], output)


def _string_to_pdf(input_format, content, output, args):
    """Pipe a document string through the engine with an explicit format."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return _convert(
        [f"--input={input_format}", *args, "-"], output, stdin=content
    )


def html_to_pdf(html, output=None, *, args=()):
    """Convert an HTML document given as a string (or bytes) to a PDF.

    No temporary files are used: the document is piped to the engine's
    stdin. Relative URLs in the document are resolved against the current
    directory unless a base URL is supplied in args, e.g.
    args=("--baseurl", "https://example.org/").

    Returns the output path (or the PDF bytes when output is None).
    Raises PrinceError on failure.
    """
    return _string_to_pdf("html", html, output, args)


def markdown_to_pdf(markdown, output=None, *, args=()):
    """Convert a Markdown document given as a string (or bytes) to a PDF.

    Requires a bundled engine with Markdown support (Prince 17 or later,
    including 17 pre-release builds). Otherwise identical to html_to_pdf().
    """
    engine = _meta()["prince_version"]
    # Dated pre-release builds (e.g. 20260630) trivially satisfy >= 17.
    major = int(re.match(r"\d+", engine).group())
    if major < 17:
        raise RuntimeError(
            f"Markdown input requires Prince 17 or later; this package "
            f"bundles Prince {engine}. Install a 17 build with "
            f"`pip install --pre prince-pdf`, or convert the Markdown to "
            f"HTML and use html_to_pdf()."
        )
    return _string_to_pdf("markdown", markdown, output, args)


def xml_to_pdf(xml, output=None, *, args=()):
    """Convert an XML document given as a string (or bytes) to a PDF.

    Otherwise identical to html_to_pdf().
    """
    return _string_to_pdf("xml", xml, output, args)


def version():
    """The bundled Prince engine's version string.

    Raises PrinceError if the engine cannot run at all (for example a
    missing system library), with the loader's message attached.
    """
    proc = run("--version", capture_output=True, text=True)
    if proc.returncode != 0 or not proc.stdout.strip():
        raise PrinceError(proc.returncode, proc.stderr)
    return proc.stdout.splitlines()[0].strip()


def license():
    """Where the bundled engine looks for its license file by default.

    Prefer setting the PRINCE_LICENSE_FILE environment variable to the
    license file's path instead of writing here: this location may not be
    writable and is replaced whenever the package is reinstalled.
    """
    return _BUNDLE / "license" / "license.dat"
