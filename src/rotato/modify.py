"""Modification functions for RotatoDocument.

Each function takes a RotatoDocument and modifies it in-place.
Changes write through to the underlying plist data.
"""

from __future__ import annotations

import plistlib
from pathlib import Path
from typing import Literal

from rotato.model import (
    BackgroundSettings,
    CameraConfig,
    RgbColor,
    RotatoDocument,
)

LABEL_SLOTS = (
    "sceneLabelTop",
    "sceneLabelBottom",
    "sceneLabelLeft",
    "sceneLabelRight",
)


def set_background_color(doc: RotatoDocument, r: float, g: float, b: float) -> None:
    """Set a solid background color (0.0-1.0 range)."""
    bg = doc.background
    bg.content_type = "color"
    bg.color = RgbColor(r, g, b)
    doc.background = bg

    env = doc.environment
    env.content_type = "color"
    env.color = RgbColor(r, g, b)
    doc.environment = env


def set_background_color_hex(doc: RotatoDocument, hex_color: str) -> None:
    """Set a solid background color from hex string like '#FF0000'."""
    c = RgbColor.from_hex(hex_color)
    set_background_color(doc, c.red, c.green, c.blue)


def set_background_gradient(
    doc: RotatoDocument,
    start_hex: str,
    end_hex: str,
    gradient_type: Literal["linear", "radial"] = "linear",
) -> None:
    """Set a gradient background using hex colors."""
    start = RgbColor.from_hex(start_hex)
    end = RgbColor.from_hex(end_hex)

    bg = doc.background
    bg.content_type = gradient_type
    bg.gradient_start = start
    bg.gradient_end = end
    doc.background = bg

    env = doc.environment
    env.content_type = gradient_type
    env.gradient_start = start
    env.gradient_end = end
    doc.environment = env


def set_background_transparent(doc: RotatoDocument) -> None:
    """Set background to transparent."""
    bg = doc.background
    bg.content_type = "transparent"
    doc.background = bg

    env = doc.environment
    env.content_type = "transparent"
    doc.environment = env


def set_camera_angles(
    doc: RotatoDocument,
    keyframe_index: int,
    pitch: float,
    yaw: float,
) -> None:
    """Set camera pitch (up/down) and yaw (left/right) for a keyframe.

    Pitch and yaw are in radians. Typical ranges:
      pitch: -1.5 (looking up) to 1.5 (looking down)
      yaw: -3.14 to 3.14 (full rotation)
    """
    kfs = doc.keyframes
    if keyframe_index < 0 or keyframe_index >= len(kfs):
        raise IndexError(f"Keyframe index {keyframe_index} out of range (0-{len(kfs) - 1})")
    kfs[keyframe_index].rig_euler_angles = (pitch, yaw, 0.0, 0.0)


def set_duration(doc: RotatoDocument, seconds: float) -> None:
    """Set total animation duration, distributing time across keyframes."""
    kfs = doc.keyframes
    if not kfs:
        return
    doc.total_duration = seconds
    per_kf = seconds / len(kfs)
    for kf in kfs:
        kf.duration = per_kf


def set_render_config(
    doc: RotatoDocument,
    resolution: str = "2K",
    fps: int = 60,
) -> None:
    """Set render output resolution and frame rate."""
    rc = doc.render_config
    rc.size = resolution
    rc.fps = float(fps)


def toggle_shadows(doc: RotatoDocument, enabled: bool) -> None:
    """Toggle scene shadows on or off."""
    doc.scene_shadows = enabled


def toggle_glass(doc: RotatoDocument, enabled: bool) -> None:
    """Toggle glass effect on device."""
    doc.show_glass = enabled


def toggle_clay(doc: RotatoDocument, enabled: bool) -> None:
    """Toggle clay rendering mode."""
    doc.clay_state = enabled


def set_shadow_intensity(doc: RotatoDocument, intensity: float) -> None:
    """Set shadow intensity (0.0-1.0)."""
    doc.shadow_intensity = intensity


def set_field_of_view(doc: RotatoDocument, fov: float) -> None:
    """Set camera field of view in degrees."""
    cam = doc.camera_config
    cam.field_of_view = fov
    doc.camera_config = cam


def replace_screen_image(doc: RotatoDocument, png_path: str | Path) -> None:
    """Replace the device screen image with a PNG file.

    Finds the SCNNode named 'Screen', locates its material's diffuse
    texture, and replaces the embedded image data.
    """
    png_data = Path(png_path).read_bytes()
    archive = doc.archive

    screen_node = archive.find_node_by_name("Screen")
    if screen_node is None:
        raise ValueError("No 'Screen' SCNNode found in this document")

    _, node_obj = screen_node

    _replace_node_texture(archive, node_obj, png_data)


def _replace_node_texture(archive, node_obj: dict, png_data: bytes) -> None:
    """Walk from an SCNNode to its material's diffuse property and replace the image."""
    geometry_ref = node_obj.get("geometry")
    if geometry_ref is None:
        raise ValueError("Screen node has no geometry")

    geometry = archive.resolve(geometry_ref)
    materials_ref = geometry.get("materials")
    if materials_ref is None:
        raise ValueError("Screen geometry has no materials")

    materials_arr = archive.resolve(materials_ref)
    if isinstance(materials_arr, dict) and "NS.objects" in materials_arr:
        mat_uids = materials_arr["NS.objects"]
    else:
        raise ValueError("Cannot resolve materials array")

    if not mat_uids:
        raise ValueError("No materials on Screen geometry")

    material = archive.resolve(mat_uids[0])
    diffuse_ref = material.get("diffuse")
    if diffuse_ref is None:
        raise ValueError("Screen material has no diffuse property")

    diffuse = archive.resolve(diffuse_ref)
    contents_ref = diffuse.get("contentsTransform") or diffuse.get("contents")

    _find_and_replace_image(archive, diffuse, png_data)


def _find_and_replace_image(archive, material_prop: dict, png_data: bytes) -> None:
    """Replace the image on a material property.

    If the property already has contents (NSImage/NSBitmapImageRep), replace the
    image data in-place. Otherwise inject the PNG bytes as a new $objects entry
    and point the property's contents at it.
    """
    contents_ref = material_prop.get("contents")

    if contents_ref is None:
        idx = len(archive.objects)
        archive.objects.append(png_data)
        material_prop["contents"] = plistlib.UID(idx)
        return

    contents = archive.resolve(contents_ref)
    if not isinstance(contents, dict):
        if isinstance(contents_ref, plistlib.UID):
            archive.objects[contents_ref.data] = png_data
        else:
            idx = len(archive.objects)
            archive.objects.append(png_data)
            material_prop["contents"] = plistlib.UID(idx)
        return

    class_name = archive.get_class_name(contents)

    if class_name == "NSImage":
        reps_ref = contents.get("NSRepresentations")
        if reps_ref is None:
            raise ValueError("NSImage has no NSRepresentations")
        reps_arr = archive.resolve(reps_ref)
        if isinstance(reps_arr, dict) and "NS.objects" in reps_arr:
            rep_uids = reps_arr["NS.objects"]
        elif isinstance(reps_arr, list):
            rep_uids = reps_arr
        else:
            raise ValueError("Cannot resolve NSRepresentations")
        for rep_uid in rep_uids:
            rep = archive.resolve(rep_uid)
            if isinstance(rep, dict):
                rep_class = archive.get_class_name(rep)
                if rep_class == "NSBitmapImageRep":
                    _replace_bitmap_rep_data(archive, rep, png_data)
                    return
        raise ValueError("No NSBitmapImageRep found in NSImage")

    elif class_name == "NSBitmapImageRep":
        _replace_bitmap_rep_data(archive, contents, png_data)

    else:
        raise ValueError(f"Don't know how to replace image in {class_name}")


def _replace_bitmap_rep_data(archive, rep: dict, png_data: bytes) -> None:
    """Replace the TIFF/PNG data in an NSBitmapImageRep."""
    tiff_ref = rep.get("NSTIFFRepresentation")
    if tiff_ref is not None:
        if isinstance(tiff_ref, plistlib.UID):
            archive.objects[tiff_ref.data] = png_data
            return

    ns_data_ref = rep.get("NSData")
    if ns_data_ref is not None:
        if isinstance(ns_data_ref, plistlib.UID):
            archive.objects[ns_data_ref.data] = png_data
            return

    for key in rep:
        if key.startswith("$"):
            continue
        val = rep[key]
        if isinstance(val, plistlib.UID):
            obj = archive.objects[val.data]
            if isinstance(obj, bytes) and len(obj) > 1000:
                archive.objects[val.data] = png_data
                return

    raise ValueError("Could not find image data to replace in NSBitmapImageRep")


# ---------------------------------------------------------------------------
# Label helpers
# ---------------------------------------------------------------------------

def _get_label_store(archive):
    """Find the SceneLabelStore and return (label_store_dict, keys_list, objects_list)."""
    root = archive.root
    label_ref = root.get("sceneLabelStore")
    if label_ref is None:
        raise ValueError("No sceneLabelStore in this document")
    label_store = archive.resolve(label_ref)

    all_ref = label_store.get("all")
    if all_ref is None:
        raise ValueError("sceneLabelStore has no 'all' dict")
    all_dict = archive.resolve(all_ref)

    raw_keys = [archive.resolve(k) for k in all_dict["NS.keys"]]
    return label_store, raw_keys, all_dict


def _find_label(archive, slot: str):
    """Return the resolved label dict for a named slot."""
    _, keys, all_dict = _get_label_store(archive)
    for i, k in enumerate(keys):
        if k == slot:
            return archive.resolve(all_dict["NS.objects"][i])
    raise ValueError(f"Label slot '{slot}' not found. Available: {keys}")


def _make_attributed_string_plist(text: str, font_name: str, font_size: float) -> dict:
    """Create an NSKeyedArchiver plist for an NSMutableAttributedString via PyObjC."""
    import Foundation
    import AppKit

    astr = Foundation.NSMutableAttributedString.alloc().initWithString_(text)
    font = AppKit.NSFont.fontWithName_size_(font_name, font_size)
    if font is None:
        font = AppKit.NSFont.systemFontOfSize_(font_size)
    astr.setAttributes_range_(
        {AppKit.NSFontAttributeName: font},
        Foundation.NSMakeRange(0, astr.length()),
    )
    archiver = Foundation.NSKeyedArchiver.alloc().initRequiringSecureCoding_(False)
    archiver.encodeObject_forKey_(astr, "root")
    archiver.finishEncoding()
    return plistlib.loads(bytes(archiver.encodedData()))


def _graft_plist(target_objects: list, src_plist: dict) -> plistlib.UID:
    """Graft a standalone NSKeyedArchiver plist's object graph into target_objects.

    Returns the UID (in target_objects) of the source's root object.
    """
    src_objects = src_plist["$objects"]
    src_top = src_plist["$top"]["root"]
    src_root_idx = src_top.data if isinstance(src_top, plistlib.UID) else src_top

    base = len(target_objects)
    uid_map = {0: plistlib.UID(0)}

    for old_idx in range(len(src_objects)):
        if old_idx == 0:
            continue
        new_idx = base + old_idx - 1
        uid_map[old_idx] = plistlib.UID(new_idx)

    def remap(val):
        if isinstance(val, plistlib.UID):
            return uid_map.get(val.data, val)
        if isinstance(val, dict):
            return {k: remap(v) for k, v in val.items()}
        if isinstance(val, list):
            return [remap(v) for v in val]
        return val

    for old_idx in range(1, len(src_objects)):
        target_objects.append(remap(src_objects[old_idx]))

    return uid_map[src_root_idx]


def _make_nscolor(archive, r: float, g: float, b: float) -> plistlib.UID:
    """Create a new NSColor object in the archive and return its UID.

    Uses NSColorSpace=1 (device RGB) with NSRGB bytes encoding.
    """
    existing_colors = archive.find_objects_by_class("NSColor")
    if not existing_colors:
        raise ValueError("No existing NSColor in document to borrow $class from")
    _, sample = existing_colors[0]
    class_ref = sample["$class"]

    color_obj = {
        "$class": class_ref,
        "NSColorSpace": 1,
        "NSRGB": f"{r} {g} {b}\x00".encode("ascii"),
    }
    idx = len(archive.objects)
    archive.objects.append(color_obj)
    return plistlib.UID(idx)


def set_label_text(
    doc: RotatoDocument,
    slot: str,
    text: str,
    font_name: str = "HelveticaNeue-Bold",
    font_size: float = 3.5,
) -> None:
    """Set the text content of a scene label with proper attributed string encoding.

    Args:
        doc: The RotatoDocument to modify.
        slot: One of 'sceneLabelTop', 'sceneLabelBottom', 'sceneLabelLeft', 'sceneLabelRight'.
        text: The text to display.
        font_name: macOS font name (e.g. 'HelveticaNeue-Bold', 'Helvetica', 'AlBayan-Bold').
        font_size: Font size in scene units (template scale is ~100, so 2-5 is typical).
    """
    if slot not in LABEL_SLOTS:
        raise ValueError(f"Invalid slot '{slot}'. Must be one of {LABEL_SLOTS}")

    archive = doc.archive
    label = _find_label(archive, slot)

    astr_plist = _make_attributed_string_plist(text, font_name, font_size)
    new_uid = _graft_plist(archive.objects, astr_plist)
    label["text"] = new_uid


def set_label_color(
    doc: RotatoDocument,
    slot: str,
    r: float,
    g: float,
    b: float,
) -> None:
    """Set the color of a scene label.

    Always creates a new NSColor object so labels can have independent colors.

    Args:
        doc: The RotatoDocument to modify.
        slot: One of 'sceneLabelTop', 'sceneLabelBottom', 'sceneLabelLeft', 'sceneLabelRight'.
        r: Red component (0.0 to 1.0).
        g: Green component (0.0 to 1.0).
        b: Blue component (0.0 to 1.0).
    """
    if slot not in LABEL_SLOTS:
        raise ValueError(f"Invalid slot '{slot}'. Must be one of {LABEL_SLOTS}")

    archive = doc.archive
    label = _find_label(archive, slot)
    label["color"] = _make_nscolor(archive, r, g, b)


def clear_label(doc: RotatoDocument, slot: str) -> None:
    """Clear a label's text (set to empty string)."""
    if slot not in LABEL_SLOTS:
        raise ValueError(f"Invalid slot '{slot}'. Must be one of {LABEL_SLOTS}")

    archive = doc.archive
    label = _find_label(archive, slot)
    astr_plist = _make_attributed_string_plist("", "HelveticaNeue", 3.0)
    new_uid = _graft_plist(archive.objects, astr_plist)
    label["text"] = new_uid
