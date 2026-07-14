"""Hatchling build hook: tag the wheel for one platform and bundle the engine.

The staged engine tree must already exist at staging/<platform>/ (created by
scripts/build_wheels.py). PRINCE_WHEEL_PLATFORM selects which staging tree is
bundled and becomes the wheel's platform tag.
"""

import os
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class PrinceBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        plat = os.environ.get("PRINCE_WHEEL_PLATFORM")
        if not plat:
            raise RuntimeError(
                "PRINCE_WHEEL_PLATFORM is not set. Build wheels with "
                "scripts/build_wheels.py, not with `python -m build` directly."
            )
        staged = Path(self.root) / "staging" / plat
        if not (staged / "_meta.json").is_file():
            raise RuntimeError(
                f"No staged engine at {staged}. "
                f"Run: python scripts/build_wheels.py --platform {plat}"
            )
        build_data["tag"] = f"py3-none-{plat}"
        build_data["pure_python"] = False
        build_data["force_include"][str(staged)] = "prince_pdf/_bundle"
