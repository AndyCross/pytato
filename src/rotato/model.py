"""Strongly-typed model wrapping a .rotato file's NSKeyedArchiver data.

RotatoDocument holds a reference to the raw plist + KeyedArchive so all
modifications write through directly to the underlying $objects array.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rotato.archive import KeyedArchive


@dataclass
class RgbColor:
    red: float
    green: float
    blue: float

    def to_dict(self) -> dict:
        return {"red": self.red, "green": self.green, "blue": self.blue}

    @classmethod
    def from_dict(cls, d: dict) -> RgbColor:
        return cls(red=d["red"], green=d["green"], blue=d["blue"])

    @classmethod
    def from_hex(cls, hex_str: str) -> RgbColor:
        h = hex_str.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return cls(red=r / 255.0, green=g / 255.0, blue=b / 255.0)


@dataclass
class EasingCurve:
    name: str
    friendly_name: str
    group: int
    c1x: float
    c1y: float
    c2x: float
    c2y: float

    @classmethod
    def from_archive(cls, archive: KeyedArchive, obj: dict) -> EasingCurve:
        func = archive.resolve(obj.get("function", {}))
        if isinstance(func, dict):
            func_resolved = {
                k: archive.resolve(v) if hasattr(v, "data") else v
                for k, v in func.items()
                if k != "$class"
            }
        else:
            func_resolved = {}
        return cls(
            name=archive.resolve(obj.get("name", "")) or "",
            friendly_name=archive.resolve(obj.get("friendlyName", "")) or "",
            group=obj.get("group", 0),
            c1x=func_resolved.get("c1x", 0.25),
            c1y=func_resolved.get("c1y", 0.1),
            c2x=func_resolved.get("c2x", 0.25),
            c2y=func_resolved.get("c2y", 1.0),
        )

    @classmethod
    def default(cls) -> EasingCurve:
        return cls(
            name="Default",
            friendly_name="Default",
            group=0,
            c1x=0.25, c1y=0.1,
            c2x=0.25, c2y=1.0,
        )


@dataclass
class Keyframe:
    """A single animation keyframe. Holds a reference to its archive object."""

    _archive: KeyedArchive
    _obj: dict

    @property
    def duration(self) -> float:
        return self._archive.resolve(self._obj["duration"])

    @duration.setter
    def duration(self, value: float) -> None:
        self._archive.set_value(self._obj, "duration", value)

    @property
    def rig_euler_angles(self) -> tuple[float, float, float, float]:
        return self._archive.get_nsvalue_vector4(self._obj["rigEulerAngles"])

    @rig_euler_angles.setter
    def rig_euler_angles(self, value: tuple[float, float, float, float]) -> None:
        self._archive.set_nsvalue_vector4(
            self._obj["rigEulerAngles"], *value
        )

    @property
    def position(self) -> tuple[float, float, float, float]:
        return self._archive.get_nsvalue_vector4(self._obj["position"])

    @property
    def focus_distance(self) -> float:
        return self._archive.resolve(self._obj.get("focusDistance", 2.5))

    @property
    def f_stop(self) -> float:
        return self._archive.resolve(self._obj.get("fStop", 0.056))

    @property
    def is_jumpcut(self) -> bool:
        return self._obj.get("isJumpcut", False)

    @property
    def easing(self) -> EasingCurve:
        easing_obj = self._archive.resolve(self._obj.get("easingV2"))
        if isinstance(easing_obj, dict):
            return EasingCurve.from_archive(self._archive, easing_obj)
        return EasingCurve.default()


@dataclass
class CameraConfig:
    """Camera/lens settings (stored as JSON string in the plist)."""

    field_of_view: float = 31.89
    saturation: float = 1.0
    contrast: float = 0.0
    motion_blur_intensity: float = 0.0
    wants_hdr: bool = False
    exposure_offset: float = 0.0
    white_point: float = 1.0
    wants_depth_of_field: bool = False
    focus_distance: float = 2.5
    f_stop: float = 0.1
    aperture_blade_count: int = 6
    vignette_power: float = 0.0
    vignette_intensity: float = 1.0
    color_fringe_strength: float = 0.0
    color_fringe_intensity: float = 1.0

    @classmethod
    def from_json(cls, data: dict) -> CameraConfig:
        hdr = data.get("hdr", {})
        focus = data.get("focus", {})
        vignette = data.get("vignette", {})
        fringe = data.get("fringe", {})
        return cls(
            field_of_view=data.get("fieldOfView", 31.89),
            saturation=data.get("saturation", 1.0),
            contrast=data.get("contrast", 0.0),
            motion_blur_intensity=data.get("motionBlurIntensity", 0.0),
            wants_hdr=hdr.get("wantsHDR", False),
            exposure_offset=hdr.get("exposureOffset", 0.0),
            white_point=hdr.get("whitePoint", 1.0),
            wants_depth_of_field=focus.get("wantsDepthOfField", False),
            focus_distance=focus.get("focusDistance", 2.5),
            f_stop=focus.get("fStop", 0.1),
            aperture_blade_count=focus.get("apertertureBladeCount", 6),
            vignette_power=vignette.get("vignettingPower", 0.0),
            vignette_intensity=vignette.get("vignettingIntensity", 1.0),
            color_fringe_strength=fringe.get("colorFringeStrength", 0.0),
            color_fringe_intensity=fringe.get("colorFringeIntensity", 1.0),
        )

    def to_json(self) -> dict:
        return {
            "fieldOfView": self.field_of_view,
            "saturation": self.saturation,
            "contrast": self.contrast,
            "motionBlurIntensity": self.motion_blur_intensity,
            "hdr": {
                "wantsHDR": self.wants_hdr,
                "exposureOffset": self.exposure_offset,
                "whitePoint": self.white_point,
                "averageGray": 0.18000000715255737,
                "wantsExposureAdaptation": True,
            },
            "focus": {
                "wantsDepthOfField": self.wants_depth_of_field,
                "focusDistance": self.focus_distance,
                "fStop": self.f_stop,
                "apertertureBladeCount": self.aperture_blade_count,
            },
            "vignette": {
                "vignettingPower": self.vignette_power,
                "vignettingIntensity": self.vignette_intensity,
            },
            "fringe": {
                "colorFringeStrength": self.color_fringe_strength,
                "colorFringeIntensity": self.color_fringe_intensity,
            },
        }


@dataclass
class BackgroundSettings:
    """Background/environment settings (stored as JSON string in the plist)."""

    content_type: str = "color"
    color: RgbColor = field(default_factory=lambda: RgbColor(1.0, 1.0, 1.0))
    gradient_start: RgbColor = field(default_factory=lambda: RgbColor(1.0, 0.5, 0.0))
    gradient_end: RgbColor = field(default_factory=lambda: RgbColor(1.0, 0.0, 0.0))
    gradient_preset_id: str = "Warm Flame"
    environment_preset_id: str = "ibl.hdr"

    _raw: dict = field(default_factory=dict, repr=False)

    @classmethod
    def from_json(cls, data: dict) -> BackgroundSettings:
        ct_dict = data.get("contentType", {})
        content_type = next(iter(ct_dict.keys()), "color") if ct_dict else "color"
        color_settings = data.get("colorSettings", {})
        color = RgbColor.from_dict(color_settings["color"]) if "color" in color_settings else RgbColor(1.0, 1.0, 1.0)
        gradient = data.get("gradientSettings", {})
        gs = RgbColor.from_dict(gradient["start"]) if "start" in gradient else RgbColor(1.0, 0.5, 0.0)
        ge = RgbColor.from_dict(gradient["end"]) if "end" in gradient else RgbColor(1.0, 0.0, 0.0)
        gp = data.get("gradientPresetSettings", {})
        ep = data.get("environmentPresetSettings", {})
        return cls(
            content_type=content_type,
            color=color,
            gradient_start=gs,
            gradient_end=ge,
            gradient_preset_id=gp.get("presetId", "Warm Flame"),
            environment_preset_id=ep.get("environmentPresetId", "ibl.hdr"),
            _raw=data,
        )

    def to_json(self) -> dict:
        result = dict(self._raw) if self._raw else {}
        result["contentType"] = {self.content_type: {}}
        cs = result.setdefault("colorSettings", {})
        cs["contentType"] = {"color": {}}
        cs["color"] = self.color.to_dict()
        cs.setdefault("preferredPreviewSize", {"none": {}})
        gs = result.setdefault("gradientSettings", {})
        gs["start"] = self.gradient_start.to_dict()
        gs["end"] = self.gradient_end.to_dict()
        gs.setdefault("noise", False)
        gs.setdefault("isCubeMap", False)
        return result


@dataclass
class RenderConfig:
    """Render output settings."""

    _archive: KeyedArchive
    _obj: dict

    @property
    def size(self) -> str:
        return self._archive.resolve(self._obj.get("size", "2K"))

    @size.setter
    def size(self, value: str) -> None:
        self._archive.set_value(self._obj, "size", value)

    @property
    def fps(self) -> float:
        return self._archive.resolve(self._obj.get("fps", 60.0))

    @fps.setter
    def fps(self, value: float) -> None:
        self._archive.set_value(self._obj, "fps", value)

    @property
    def video_codec(self) -> int:
        return self._archive.resolve(self._obj.get("videoCodec", 0))

    @property
    def compression(self) -> float:
        return self._archive.resolve(self._obj.get("compression", 1.0))

    @property
    def render_mode(self) -> str:
        return self._archive.resolve(self._obj.get("renderMode", "Movie"))


class RotatoDocument:
    """Top-level document wrapping a .rotato file.

    Holds a reference to the raw plist and KeyedArchive. All property
    modifications write through directly to the underlying data, so calling
    save() on the file API will persist them.
    """

    def __init__(self, plist_data: dict) -> None:
        self._archive = KeyedArchive(plist_data)
        self._root = self._archive.root

    @property
    def archive(self) -> KeyedArchive:
        return self._archive

    @property
    def raw(self) -> dict:
        return self._archive.raw

    @property
    def device_scene_name(self) -> str:
        return self._archive.get(self._root, "deviceSceneName")

    @property
    def total_duration(self) -> float:
        return self._root["totalDuration"]

    @total_duration.setter
    def total_duration(self, value: float) -> None:
        self._root["totalDuration"] = value

    @property
    def default_duration(self) -> float:
        return self._root["defaultDuration"]

    @default_duration.setter
    def default_duration(self, value: float) -> None:
        self._root["defaultDuration"] = value

    @property
    def scene_shadows(self) -> bool:
        return self._root["sceneShadows"]

    @scene_shadows.setter
    def scene_shadows(self, value: bool) -> None:
        self._root["sceneShadows"] = value

    @property
    def show_glass(self) -> bool:
        return self._root["showGlass"]

    @show_glass.setter
    def show_glass(self, value: bool) -> None:
        self._root["showGlass"] = value

    @property
    def clay_state(self) -> bool:
        return self._root["clayState"]

    @clay_state.setter
    def clay_state(self, value: bool) -> None:
        self._root["clayState"] = value

    @property
    def reflection_probe(self) -> bool:
        return self._root.get("reflectionProbe", False)

    @reflection_probe.setter
    def reflection_probe(self, value: bool) -> None:
        self._root["reflectionProbe"] = value

    @property
    def shadow_intensity(self) -> float:
        return self._archive.resolve(self._root["shadowIntensity"])

    @shadow_intensity.setter
    def shadow_intensity(self, value: float) -> None:
        self._archive.set_value(self._root, "shadowIntensity", value)

    # --- Keyframes ---

    @property
    def keyframes(self) -> list[Keyframe]:
        items = self._archive.get_array(self._root, "keyframes")
        return [
            Keyframe(_archive=self._archive, _obj=self._archive.resolve(uid))
            for uid in items
        ]

    # --- Camera Config (JSON) ---

    @property
    def camera_config(self) -> CameraConfig:
        data = self._archive.get_json(self._root, "cameraConfig")
        return CameraConfig.from_json(data)

    @camera_config.setter
    def camera_config(self, config: CameraConfig) -> None:
        self._archive.set_json(self._root, "cameraConfig", config.to_json())

    # --- Background (JSON) ---

    @property
    def background(self) -> BackgroundSettings:
        data = self._archive.get_json(self._root, "sceneBackgroundContents")
        return BackgroundSettings.from_json(data)

    @background.setter
    def background(self, settings: BackgroundSettings) -> None:
        self._archive.set_json(
            self._root, "sceneBackgroundContents", settings.to_json()
        )

    @property
    def environment(self) -> BackgroundSettings:
        data = self._archive.get_json(self._root, "environmentContents")
        return BackgroundSettings.from_json(data)

    @environment.setter
    def environment(self, settings: BackgroundSettings) -> None:
        self._archive.set_json(
            self._root, "environmentContents", settings.to_json()
        )

    # --- Render Config ---

    @property
    def render_config(self) -> RenderConfig:
        rc_obj = self._archive.resolve(self._root["renderConfig"])
        return RenderConfig(_archive=self._archive, _obj=rc_obj)
