"""Public API for loading, saving, and creating .rotato files."""

from __future__ import annotations

import importlib.resources
import shutil
import subprocess
from pathlib import Path

from rotato.io import read_plist, write_plist
from rotato.model import RotatoDocument


def load(path: str | Path) -> RotatoDocument:
    """Load a .rotato file into a RotatoDocument."""
    data = read_plist(path)
    return RotatoDocument(data)


def save(doc: RotatoDocument, path: str | Path) -> None:
    """Save a RotatoDocument to a .rotato file."""
    write_plist(doc.raw, path)


def from_template(output_path: str | Path | None = None) -> RotatoDocument:
    """Create a new RotatoDocument from the built-in iPhone 14 Pro template.

    If output_path is provided, copies the template there first.
    Returns a RotatoDocument ready for modification.
    """
    template_path = _get_template_path()

    if output_path is not None:
        output_path = Path(output_path)
        shutil.copy2(template_path, output_path)
        return load(output_path)

    return load(template_path)


def open_in_rotato(path: str | Path) -> None:
    """Open a .rotato file in the Rotato app."""
    path = Path(path).resolve()
    subprocess.run(["open", "-a", "Rotato", str(path)], check=True)


def _get_template_path() -> Path:
    """Locate the bundled template file."""
    # Try relative to this package first (development layout)
    pkg_dir = Path(__file__).parent.parent.parent / "templates"
    candidate = pkg_dir / "iphone14pro.rotato"
    if candidate.exists():
        return candidate

    # Try importlib.resources for installed packages
    try:
        ref = importlib.resources.files("rotato").joinpath(
            "../../templates/iphone14pro.rotato"
        )
        with importlib.resources.as_file(ref) as p:
            if p.exists():
                return p
    except (TypeError, FileNotFoundError):
        pass

    raise FileNotFoundError(
        "Cannot find template file iphone14pro.rotato. "
        "Make sure the templates/ directory is present."
    )
