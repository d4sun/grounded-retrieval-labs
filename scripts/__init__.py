"""CLI entrypoints. Run as modules, e.g. ``python -m scripts.run_ingest``.

Adds ``src/`` to sys.path so the scripts work without installing the package.
"""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
