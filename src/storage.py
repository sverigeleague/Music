"""Raw documents: stored once, gzipped, never changed; raw/manifest.csv holds each file's SHA-256."""
import csv
import gzip
import hashlib
from datetime import datetime, timezone

from .config import RAW

MANIFEST = RAW / "manifest.csv"
FIELDS = ["path", "url", "fetched_at", "sha256", "size"]


def archive(rel_path: str, url: str, content: bytes) -> str:
    """Write raw/<rel_path>.gz unless it exists; returns the SHA-256 of the uncompressed content."""
    digest = hashlib.sha256(content).hexdigest()
    path = RAW / (rel_path + ".gz")
    if path.exists():
        return digest
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.GzipFile(path, "wb", mtime=0) as f:
        f.write(content)
    new = not MANIFEST.exists()
    with MANIFEST.open("a", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        if new:
            w.writeheader()
        w.writerow({"path": str(path.relative_to(RAW)), "url": url,
                    "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "sha256": digest, "size": len(content)})
    return digest


def read(rel_path: str) -> bytes:
    with gzip.open(RAW / (rel_path + ".gz"), "rb") as f:
        return f.read()
