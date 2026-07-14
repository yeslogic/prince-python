"""Console entry point: `prince` on PATH, delegating to the bundled engine."""

import os
import subprocess
import sys

import prince_pdf


def main():
    try:
        argv = prince_pdf.command(*sys.argv[1:])
    except RuntimeError as exc:
        print(f"prince: {exc}", file=sys.stderr)
        return 1
    if os.name == "posix":
        os.execv(argv[0], argv)
    return subprocess.call(argv)


if __name__ == "__main__":
    sys.exit(main())
