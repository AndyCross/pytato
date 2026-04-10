# Rotato MCP

Conversational [Rotato](https://rotato.app) file builder -- read, modify, and create `.rotato` 3D mockup files through an MCP server.

Rotato has no public SDK or API. This project reverse-engineers the `.rotato` file format (LZFSE-compressed NSKeyedArchiver binary plist) and exposes 18 tools via the [Model Context Protocol](https://modelcontextprotocol.io), so AI assistants can create and customize 3D device mockups conversationally.

> **macOS only** -- depends on PyObjC for native `NSAttributedString` / `NSFont` / `NSColor` serialization and `plutil` for binary plist normalization.

## Setup

Requires Python 3.13+, [uv](https://docs.astral.sh/uv/), and [Rotato](https://rotato.app) installed at `/Applications/Rotato.app`.

```bash
# Clone and install
git clone <repo-url> && cd video-gen
uv sync

# Copy a device template into the templates/ directory
mkdir -p templates
cp ~/Downloads/sample.rotato templates/iphone14pro.rotato
```

The template file is gitignored since it contains Rotato's proprietary 3D assets. You need to provide your own by saving a blank scene from Rotato.

## Usage

### With Cursor

Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "rotato": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/video-gen", "rotato-mcp"]
    }
  }
}
```

### With Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "rotato": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/video-gen", "rotato-mcp"]
    }
  }
}
```

Restart the application after editing the config.

### Standalone

```bash
uv run rotato-mcp
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `create_rotato` | Create a new document from the iPhone 14 Pro template |
| `get_document_info` | Inspect an existing `.rotato` file |
| `set_screen_image` | Set the device screen to a PNG image |
| `set_label_text` | Set text on a scene label (top/bottom/left/right) with font control |
| `set_label_color` | Set independent RGB color on a scene label |
| `set_background_color` | Solid RGB background |
| `set_background_color_hex` | Solid background from hex string |
| `set_background_gradient` | Linear or radial gradient background |
| `set_background_transparent` | Transparent background |
| `set_camera_angle` | Set pitch/yaw for a keyframe |
| `set_field_of_view` | Set camera FOV in degrees |
| `set_duration` | Set total animation duration |
| `apply_animation_preset` | Apply a built-in animation (dangle, flip-in, hover, etc.) |
| `list_animation_presets` | List available animation presets |
| `set_render_config` | Set resolution (2K/4K/8K) and FPS |
| `toggle_scene_property` | Toggle shadows, glass, or clay mode |
| `set_shadow_intensity` | Set shadow intensity (0.0--1.0) |
| `open_in_rotato` | Open the file in Rotato for preview |

## Architecture

```
src/
├── rotato/
│   ├── io.py          # LZFSE compression + plist serialization (plutil round-trip)
│   ├── archive.py     # NSKeyedArchiver UID resolution and in-place modification
│   ├── model.py       # Typed wrappers: RotatoDocument, Keyframe, CameraConfig, etc.
│   ├── modify.py      # High-level mutation functions (labels, backgrounds, screen, etc.)
│   ├── presets.py     # Animation preset loader from Rotato.app resources
│   └── file.py        # Public API: load, save, from_template, open_in_rotato
└── rotato_mcp/
    └── server.py      # FastMCP server exposing all tools
```

## File Format

A `.rotato` file is:

1. **LZFSE-compressed** (Apple's compression format)
2. **NSKeyedArchiver binary plist** with a flat `$objects` array and `CF$UID` references
3. Contains an embedded **SceneKit** 3D scene with geometry, materials, and textures
4. Stores background/camera/environment settings as **JSON strings** encoded as bytes within the plist
5. Stores label text as **NSMutableAttributedString** objects (requiring PyObjC for correct font serialization)
6. Stores label colors as **NSColor** objects (each label needs its own instance to avoid shared-UID overwrites)

## Known Limitations

- **Levitation bug**: Rotato does not correctly reload the `levitation` property from saved files. After opening a generated file, you need to manually set levitation in the Rotato UI.
- **Template required**: You must provide your own `.rotato` template file since it contains Rotato's proprietary 3D models.
- **macOS only**: PyObjC and `plutil` are macOS-specific dependencies.
