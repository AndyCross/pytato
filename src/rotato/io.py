"""LZFSE compression and plist serialization for .rotato files.

The .rotato format is: LZFSE-compressed NSKeyedArchiver binary plist.
Reading uses plistlib (stdlib). Writing uses plutil for Apple-native binary
plist encoding, which preserves the exact format NSKeyedUnarchiver expects.
"""

from pathlib import Path
import plistlib
import subprocess
import tempfile

import liblzfse


def read_plist(path: str | Path) -> dict:
    """Read a .rotato file: LZFSE decompress -> parse binary plist."""
    compressed = Path(path).read_bytes()
    raw = decompress(compressed)
    return plistlib.loads(raw)


def write_plist(data: dict, path: str | Path) -> None:
    """Write a .rotato file: serialize binary plist -> LZFSE compress.

    Writes binary plist via plistlib, then round-trips through plutil
    to normalize the encoding to match what NSKeyedUnarchiver expects.
    """
    with tempfile.NamedTemporaryFile(suffix=".plist", delete=False) as tmp:
        tmp_path = tmp.name
        plistlib.dump(data, tmp, fmt=plistlib.FMT_BINARY)
    try:
        subprocess.run(
            ["plutil", "-convert", "xml1", tmp_path],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["plutil", "-convert", "binary1", tmp_path],
            check=True, capture_output=True,
        )
        raw = Path(tmp_path).read_bytes()
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    compressed = compress(raw)
    Path(path).write_bytes(compressed)


def read_plain_plist(path: str | Path) -> dict:
    """Read a plain binary plist (no LZFSE layer). Used for .keyframes files."""
    with open(path, "rb") as f:
        return plistlib.load(f)


def decompress(data: bytes) -> bytes:
    """LZFSE decompress raw bytes."""
    return liblzfse.decompress(data)


def compress(data: bytes) -> bytes:
    """LZFSE compress raw bytes."""
    return liblzfse.compress(data)
