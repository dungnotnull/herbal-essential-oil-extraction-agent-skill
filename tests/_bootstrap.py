"""Put src/ and config/ on sys.path for tests. Import once in each test module."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for p in (ROOT / "src", ROOT / "config"):
    s = str(p)
    if s not in sys.path:
        sys.path.insert(0, s)