"""MCP server exposing Rotato file manipulation tools.

Run with: uv run rotato-mcp
Or:       uv run python -m rotato_mcp.server
"""

from __future__ import annotations

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

import rotato
from rotato import modify
from rotato.presets import apply_preset as _apply_preset
from rotato.presets import list_presets as _list_presets

mcp = FastMCP(
    "Rotato",
    instructions=(
        "Tools for creating and modifying Rotato 3D mockup files (.rotato). "
        "Start by creating a new document with create_rotato, then modify it "
        "with the other tools, and finally open it in Rotato to preview."
    ),
)


@mcp.tool()
def create_rotato(output_path: str) -> str:
    """Create a new Rotato document from the built-in iPhone 14 Pro template.

    Args:
        output_path: Where to save the new .rotato file.

    Returns:
        Confirmation message with the file path.
    """
    doc = rotato.from_template(output_path)
    return json.dumps({
        "status": "created",
        "path": str(Path(output_path).resolve()),
        "device": doc.device_scene_name,
        "duration": doc.total_duration,
        "keyframes": len(doc.keyframes),
    })


@mcp.tool()
def set_background_color(path: str, r: float, g: float, b: float) -> str:
    """Set the background to a solid RGB color.

    Args:
        path: Path to the .rotato file.
        r: Red component (0.0 to 1.0).
        g: Green component (0.0 to 1.0).
        b: Blue component (0.0 to 1.0).
    """
    doc = rotato.load(path)
    modify.set_background_color(doc, r, g, b)
    rotato.save(doc, path)
    return json.dumps({"status": "ok", "background": f"rgb({r:.2f}, {g:.2f}, {b:.2f})"})


@mcp.tool()
def set_background_color_hex(path: str, hex_color: str) -> str:
    """Set the background to a solid color using a hex string.

    Args:
        path: Path to the .rotato file.
        hex_color: Hex color string like '#FF0000' or 'FF0000'.
    """
    doc = rotato.load(path)
    modify.set_background_color_hex(doc, hex_color)
    rotato.save(doc, path)
    return json.dumps({"status": "ok", "background": hex_color})


@mcp.tool()
def set_background_gradient(
    path: str,
    start_hex: str,
    end_hex: str,
    gradient_type: str = "linear",
) -> str:
    """Set a gradient background.

    Args:
        path: Path to the .rotato file.
        start_hex: Start color as hex string like '#FF0000'.
        end_hex: End color as hex string like '#0000FF'.
        gradient_type: Either 'linear' or 'radial'.
    """
    doc = rotato.load(path)
    modify.set_background_gradient(doc, start_hex, end_hex, gradient_type)  # type: ignore[arg-type]
    rotato.save(doc, path)
    return json.dumps({
        "status": "ok",
        "gradient": f"{start_hex} -> {end_hex} ({gradient_type})",
    })


@mcp.tool()
def set_background_transparent(path: str) -> str:
    """Set the background to transparent.

    Args:
        path: Path to the .rotato file.
    """
    doc = rotato.load(path)
    modify.set_background_transparent(doc)
    rotato.save(doc, path)
    return json.dumps({"status": "ok", "background": "transparent"})


@mcp.tool()
def set_camera_angle(
    path: str,
    keyframe_index: int,
    pitch: float,
    yaw: float,
) -> str:
    """Set camera pitch and yaw for a specific keyframe.

    Args:
        path: Path to the .rotato file.
        keyframe_index: Which keyframe to modify (0-based).
        pitch: Camera pitch in radians (-1.5 = looking up, 1.5 = looking down).
        yaw: Camera yaw in radians (-3.14 to 3.14, full rotation).
    """
    doc = rotato.load(path)
    modify.set_camera_angles(doc, keyframe_index, pitch, yaw)
    rotato.save(doc, path)
    return json.dumps({
        "status": "ok",
        "keyframe": keyframe_index,
        "pitch": pitch,
        "yaw": yaw,
    })


@mcp.tool()
def set_duration(path: str, seconds: float) -> str:
    """Set total animation duration, distributing time across keyframes.

    Args:
        path: Path to the .rotato file.
        seconds: Total duration in seconds.
    """
    doc = rotato.load(path)
    modify.set_duration(doc, seconds)
    rotato.save(doc, path)
    return json.dumps({"status": "ok", "duration": seconds})


@mcp.tool()
def apply_animation_preset(path: str, preset_name: str) -> str:
    """Apply a built-in animation preset.

    Args:
        path: Path to the .rotato file.
        preset_name: Name of the preset (use list_presets to see available ones).
    """
    doc = rotato.load(path)
    _apply_preset(doc.archive, preset_name)
    rotato.save(doc, path)
    return json.dumps({"status": "ok", "preset": preset_name})


@mcp.tool()
def set_render_config(path: str, resolution: str = "2K", fps: int = 60) -> str:
    """Set render output settings.

    Args:
        path: Path to the .rotato file.
        resolution: Output resolution - '2K', '4K', or '8K'.
        fps: Frames per second (30 or 60).
    """
    doc = rotato.load(path)
    modify.set_render_config(doc, resolution, fps)
    rotato.save(doc, path)
    return json.dumps({"status": "ok", "resolution": resolution, "fps": fps})


@mcp.tool()
def toggle_scene_property(path: str, property_name: str, enabled: bool) -> str:
    """Toggle a scene property on or off.

    Args:
        path: Path to the .rotato file.
        property_name: One of 'shadows', 'glass', 'clay'.
        enabled: True to enable, False to disable.
    """
    doc = rotato.load(path)
    toggles = {
        "shadows": modify.toggle_shadows,
        "glass": modify.toggle_glass,
        "clay": modify.toggle_clay,
    }
    fn = toggles.get(property_name)
    if fn is None:
        return json.dumps({
            "status": "error",
            "message": f"Unknown property '{property_name}'. Use: {list(toggles.keys())}",
        })
    fn(doc, enabled)
    rotato.save(doc, path)
    return json.dumps({"status": "ok", "property": property_name, "enabled": enabled})


@mcp.tool()
def set_shadow_intensity(path: str, intensity: float) -> str:
    """Set shadow intensity.

    Args:
        path: Path to the .rotato file.
        intensity: Shadow intensity from 0.0 (none) to 1.0 (full).
    """
    doc = rotato.load(path)
    modify.set_shadow_intensity(doc, intensity)
    rotato.save(doc, path)
    return json.dumps({"status": "ok", "shadow_intensity": intensity})


@mcp.tool()
def set_field_of_view(path: str, fov: float) -> str:
    """Set camera field of view.

    Args:
        path: Path to the .rotato file.
        fov: Field of view in degrees (typical range: 20-60).
    """
    doc = rotato.load(path)
    modify.set_field_of_view(doc, fov)
    rotato.save(doc, path)
    return json.dumps({"status": "ok", "fov": fov})


@mcp.tool()
def set_screen_image(path: str, image_path: str) -> str:
    """Replace the device screen image with a PNG file.

    Args:
        path: Path to the .rotato file.
        image_path: Path to the PNG image to display on the device screen.
    """
    doc = rotato.load(path)
    modify.replace_screen_image(doc, image_path)
    rotato.save(doc, path)
    return json.dumps({"status": "ok", "screen_image": image_path})


@mcp.tool()
def set_label_text(
    path: str,
    slot: str,
    text: str,
    font_name: str = "HelveticaNeue-Bold",
    font_size: float = 3.5,
) -> str:
    """Set text on a scene label with proper attributed string encoding.

    Uses PyObjC to create a native NSMutableAttributedString with the specified
    font, which Rotato requires for correct text rendering.

    Args:
        path: Path to the .rotato file.
        slot: Label position - one of 'sceneLabelTop', 'sceneLabelBottom',
              'sceneLabelLeft', 'sceneLabelRight'.
        text: The text to display. Use empty string to clear.
        font_name: macOS font name (e.g. 'HelveticaNeue-Bold', 'Helvetica-Light',
                   'AlBayan-Bold'). Defaults to HelveticaNeue-Bold.
        font_size: Size in scene units. Template scale is ~100, so 2-5 is typical
                   (3.5 = headline, 1.8 = subtitle).
    """
    doc = rotato.load(path)
    if text:
        modify.set_label_text(doc, slot, text, font_name, font_size)
    else:
        modify.clear_label(doc, slot)
    rotato.save(doc, path)
    return json.dumps({
        "status": "ok",
        "slot": slot,
        "text": text,
        "font": font_name,
        "size": font_size,
    })


@mcp.tool()
def set_label_color(
    path: str,
    slot: str,
    r: float,
    g: float,
    b: float,
) -> str:
    """Set the color of a scene label.

    Creates a new NSColor object for each call, so labels can have independent
    colors (Rotato's internal format shares color objects by default).

    Args:
        path: Path to the .rotato file.
        slot: Label position - one of 'sceneLabelTop', 'sceneLabelBottom',
              'sceneLabelLeft', 'sceneLabelRight'.
        r: Red component (0.0 to 1.0).
        g: Green component (0.0 to 1.0).
        b: Blue component (0.0 to 1.0).
    """
    doc = rotato.load(path)
    modify.set_label_color(doc, slot, r, g, b)
    rotato.save(doc, path)
    return json.dumps({
        "status": "ok",
        "slot": slot,
        "color": f"rgb({r:.2f}, {g:.2f}, {b:.2f})",
    })


@mcp.tool()
def open_in_rotato(path: str) -> str:
    """Open a .rotato file in the Rotato app for preview and rendering.

    Args:
        path: Path to the .rotato file.
    """
    rotato.open_in_rotato(path)
    return json.dumps({"status": "ok", "opened": path})


@mcp.tool()
def list_animation_presets() -> str:
    """List all available animation presets that can be applied with apply_animation_preset."""
    presets = _list_presets()
    return json.dumps({"presets": presets})


@mcp.tool()
def get_document_info(path: str) -> str:
    """Get information about an existing .rotato document.

    Args:
        path: Path to the .rotato file.
    """
    doc = rotato.load(path)
    kfs = doc.keyframes
    return json.dumps({
        "device": doc.device_scene_name,
        "duration": doc.total_duration,
        "keyframes": len(kfs),
        "keyframe_details": [
            {
                "index": i,
                "duration": kf.duration,
                "rig_euler_angles": list(kf.rig_euler_angles),
            }
            for i, kf in enumerate(kfs)
        ],
        "shadows": doc.scene_shadows,
        "glass": doc.show_glass,
        "clay": doc.clay_state,
        "shadow_intensity": doc.shadow_intensity,
        "render_size": doc.render_config.size,
        "render_fps": doc.render_config.fps,
        "background_type": doc.background.content_type,
        "fov": doc.camera_config.field_of_view,
    })


def main():
    """Entry point for the MCP server."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
