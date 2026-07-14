"""Allow `python -m prince_pdf document.html -o document.pdf`."""

import sys

from prince_pdf._cli import main

if __name__ == "__main__":
    sys.exit(main())
