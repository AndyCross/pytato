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
    """Search a material property subtree for an NSImage/NSBitmapImageRep and replace its PNG data."""
    contents_ref = material_prop.get("contents")
    if contents_ref is None:
        raise ValueError("Material property has no contents")

    contents = archive.resolve(contents_ref)
    if not isinstance(contents, dict):
        raise ValueError(f"Unexpected contents type: {type(contents)}")

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
