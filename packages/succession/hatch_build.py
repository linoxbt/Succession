"""Ship the two files an installed CLI cannot work without.

`contracts/out/artifacts.json` is a Foundry build product and gitignored, and
`deployments/base-sepolia.json` lives at the repo root. Neither is under
`src/succession/`, so neither reached the wheel, and the chain commands — the
three the product is actually about — were unreachable for anyone who installed
rather than cloned.

Copying them into `src/succession/data/` at build time keeps one copy in the
repo as the source of truth while making the wheel self-contained. The ABI has
to be compiled first; a build without it is refused rather than producing a
wheel that installs cleanly and then fails on the first chain read, which is the
failure mode this whole file exists to prevent.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parent / "src" / "succession" / "data"

SOURCES = {
    "artifacts.json": ROOT / "contracts" / "out" / "artifacts.json",
    "base-sepolia.json": ROOT / "deployments" / "base-sepolia.json",
}


class SuccessionBuildHook(BuildHookInterface):
    PLUGIN_NAME = "succession-data"

    def initialize(self, version: str, build_data: dict) -> None:
        DATA.mkdir(parents=True, exist_ok=True)
        (DATA / "__init__.py").write_text(
            '"""Data files shipped with the wheel. See hatch_build.py."""\n',
            encoding="utf-8",
        )

        missing = [name for name, path in SOURCES.items() if not path.is_file()]
        if missing:
            raise RuntimeError(
                "cannot build a working wheel without "
                + ", ".join(missing)
                + ". Run `npm run build` in contracts/ first; a wheel without "
                "the ABI installs cleanly and then fails on every chain "
                "command, which is worse than a failed build."
            )

        for name, path in SOURCES.items():
            shutil.copyfile(path, DATA / name)
