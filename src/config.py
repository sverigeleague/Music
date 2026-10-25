"""Paths and shared settings."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
DATA = ROOT / "data"
REGISTRY = ROOT / "registry"
REVIEW = ROOT / "review"
SITE = ROOT / "site"

# Contact address for User-Agent headers (owner's rule: this address only).
CONTACT = "hello@tventy.se"
USER_AGENT = f"music-ledger/0.1 (+https://github.com/sverigeleague/Music; {CONTACT})"
