"""Animation preset loader.

Loads keyframe presets from Rotato's bundled .keyframes files and applies
them to a RotatoDocument by replacing the keyframes in the $objects array.
"""

from __future__ import annotations

import plistlib
from pathlib import Path
from typing import Any

from rotato.archive import KeyedArchive

ROTATO_RESOURCES = Path("/Applications/Rotato.app/Contents/Resources")

PRESET_MAP: dict[str, str] = {
    "topturn": "01-topturn.keyframes",
    "bottom-turn": "02-bottom-turn.keyframes",
    "flip-in": "03-flip-in.keyframes",
    "flip-up": "04-flip-up.keyframes",
    "pan-across": "05-pan-across.keyframes",
    "hover": "06-hover.keyframes",
    "slide-in": "08-slide-in.keyframes",
    "dangle": "09-dangle.keyframes",
    "hoist-down": "10-hoist-down.keyframes",
    "edging": "11-edging.keyframes",
    "slide-in-2": "12-slide-in.keyframes",
}


def list_presets() -> list[str]:
    """Return names of all available animation presets."""
    available = []
    for name, filename in PRESET_MAP.items():
        if (ROTATO_RESOURCES / filename).exists():
            available.append(name)
    return available


def load_preset_keyframes(preset_name: str) -> list[dict]:
    """Load raw keyframe dicts from a preset file.

    Returns a list of keyframe objects with all UIDs resolved to values.
    """
    filename = PRESET_MAP.get(preset_name)
    if filename is None:
        raise ValueError(
            f"Unknown preset '{preset_name}'. Available: {list(PRESET_MAP.keys())}"
        )
    path = ROTATO_RESOURCES / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Preset file not found: {path}. Is Rotato installed?"
        )

    with open(path, "rb") as f:
        data = plistlib.load(f)

    archive = KeyedArchive(data)
    root = archive.root
    items = root.get("NS.objects", [])

    resolved_keyframes = []
    for uid in items:
        kf = archive.resolve(uid)
        if isinstance(kf, dict):
            resolved_keyframes.append(
                _deep_resolve_keyframe(archive, kf)
            )

    return resolved_keyframes


def apply_preset(doc_archive: KeyedArchive, preset_name: str) -> None:
    """Apply an animation preset to a document.

    Copies the keyframe camera angles and transforms from the preset into
    the document's existing keyframes. If the preset has more keyframes
    than the document, extra ones are ignored. If fewer, remaining document
    keyframes keep their current values.
    """
    preset_kfs = load_preset_keyframes(preset_name)
    root = doc_archive.root

    doc_kf_items = doc_archive.get_array(root, "keyframes")

    for i, preset_kf in enumerate(preset_kfs):
        if i >= len(doc_kf_items):
            break
        doc_kf = doc_archive.resolve(doc_kf_items[i])
        _apply_keyframe_values(doc_archive, doc_kf, preset_kf)


def _apply_keyframe_values(
    archive: KeyedArchive, target: dict, source: dict
) -> None:
    """Copy camera angle/transform values from a resolved preset keyframe to a document keyframe."""
    if "rigEulerAngles" in source and "rigEulerAngles" in target:
        src_angles = source["rigEulerAngles"]
        if isinstance(src_angles, tuple) and len(src_angles) == 4:
            archive.set_nsvalue_vector4(
                target["rigEulerAngles"], *src_angles
            )

    if "position" in source and "position" in target:
        src_pos = source["position"]
        if isinstance(src_pos, tuple) and len(src_pos) == 4:
            archive.set_nsvalue_vector4(target["position"], *src_pos)

    if "duration" in source and "duration" in target:
        archive.set_value(target, "duration", source["duration"])


def _deep_resolve_keyframe(archive: KeyedArchive, kf: dict) -> dict:
    """Resolve a keyframe's key fields into plain Python values."""
    result: dict[str, Any] = {}

    for key in ["rigEulerAngles", "position", "eulerAngles", "orientation",
                "rotation", "labelsPosition"]:
        if key in kf:
            try:
                result[key] = archive.get_nsvalue_vector4(kf[key])
            except (ValueError, KeyError):
                pass

    for key in ["duration", "focusDistance", "fStop", "artboardItemLevitation"]:
        if key in kf:
            val = archive.resolve(kf[key])
            if isinstance(val, (int, float)):
                result[key] = float(val)

    for key in ["isJumpcut"]:
        if key in kf:
            result[key] = kf[key]

    return result
