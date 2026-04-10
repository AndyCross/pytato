"""NSKeyedArchiver resolution layer.

Apple's NSKeyedArchiver format stores objects in a flat `$objects` array and
references them via UID integers. This module provides:

- `KeyedArchive`: wraps a raw plist dict and provides UID-based access to
  the $objects array, with in-place modification support.

We intentionally do NOT rebuild the UID graph. Instead we modify objects
in-place in the $objects array, which preserves all references to the
SCNScene geometry, materials, and textures we don't want to touch.
"""

from __future__ import annotations

import json
import plistlib
from typing import Any


class KeyedArchive:
    """Wrapper around an NSKeyedArchiver plist providing object resolution."""

    def __init__(self, plist_data: dict) -> None:
        if plist_data.get("$archiver") != "NSKeyedArchiver":
            raise ValueError("Not an NSKeyedArchiver plist")
        self._data = plist_data
        self._objects: list = plist_data["$objects"]

    @property
    def raw(self) -> dict:
        """The underlying plist dict. Modifications here persist to save."""
        return self._data

    @property
    def objects(self) -> list:
        """The $objects array. Modify entries in-place."""
        return self._objects

    @property
    def root_uid(self) -> int:
        """The UID of the root object."""
        top = self._data["$top"]
        return self._resolve_uid(top["root"])

    @property
    def root(self) -> dict:
        """The root RotatoState dict from the $objects array."""
        return self._objects[self.root_uid]

    def get(self, obj: dict, key: str) -> Any:
        """Resolve a key on an archived object, following UID references."""
        val = obj[key]
        return self.resolve(val)

    def resolve(self, val: Any) -> Any:
        """Resolve a value: if it's a UID, dereference it from $objects."""
        if isinstance(val, plistlib.UID):
            idx = val.data
            if idx == 0:
                return None
            return self._objects[idx]
        return val

    def resolve_deep(self, val: Any, max_depth: int = 4) -> Any:
        """Recursively resolve a value, following UIDs up to max_depth."""
        if max_depth <= 0:
            return val
        if isinstance(val, plistlib.UID):
            idx = val.data
            if idx == 0:
                return None
            return self.resolve_deep(self._objects[idx], max_depth - 1)
        if isinstance(val, dict):
            if "$class" in val:
                return {
                    k: self.resolve_deep(v, max_depth - 1)
                    for k, v in val.items()
                    if k != "$class"
                }
            return {k: self.resolve_deep(v, max_depth - 1) for k, v in val.items()}
        if isinstance(val, list):
            return [self.resolve_deep(item, max_depth - 1) for item in val]
        return val

    def get_class_name(self, obj: dict) -> str | None:
        """Get the $classname for an archived object."""
        class_ref = obj.get("$class")
        if class_ref is None:
            return None
        class_obj = self.resolve(class_ref)
        if isinstance(class_obj, dict):
            return class_obj.get("$classname")
        return None

    def get_json(self, obj: dict, key: str) -> Any:
        """Resolve a key that contains a JSON-encoded string or bytes."""
        val = self.resolve(obj[key])
        if isinstance(val, bytes):
            val = val.decode("utf-8")
        if isinstance(val, str):
            return json.loads(val)
        return val

    def set_json(self, obj: dict, key: str, value: Any) -> None:
        """Serialize a value as JSON and store it at the object's key.

        Replaces the referenced object in $objects in-place.
        """
        uid = obj[key]
        if not isinstance(uid, plistlib.UID):
            raise ValueError(f"Expected UID for key {key}, got {type(uid)}")
        encoded = json.dumps(value, separators=(",", ":"))
        existing = self._objects[uid.data]
        if isinstance(existing, bytes):
            self._objects[uid.data] = encoded.encode("utf-8")
        else:
            self._objects[uid.data] = encoded

    def set_value(self, obj: dict, key: str, value: Any) -> None:
        """Set a scalar value on an object, resolving UIDs as needed."""
        current = obj.get(key)
        if isinstance(current, plistlib.UID):
            self._objects[current.data] = value
        else:
            obj[key] = value

    def get_array(self, obj: dict, key: str) -> list:
        """Resolve a key that points to an NSArray, returning the items."""
        arr_obj = self.resolve(obj[key])
        if isinstance(arr_obj, dict) and "NS.objects" in arr_obj:
            return arr_obj["NS.objects"]
        if isinstance(arr_obj, list):
            return arr_obj
        raise ValueError(f"Expected NSArray at key {key}, got {type(arr_obj)}")

    def get_nsvalue_vector4(self, val: Any) -> tuple[float, float, float, float]:
        """Extract x, y, z, w from an NSValue encoded as NS.rectval string.

        NSValue stores SCNVector4 as '{{x, y}, {z, w}}' in the NS.rectval field.
        Both the NSValue dict and the NS.rectval string may be behind UIDs.
        """
        obj = self._resolve_through_uids(val)
        if isinstance(obj, dict) and "NS.rectval" in obj:
            s = self._resolve_through_uids(obj["NS.rectval"])
            nums = [float(x) for x in s.replace("{", "").replace("}", "").split(",")]
            return (nums[0], nums[1], nums[2], nums[3])
        raise ValueError(f"Cannot extract vector4 from {obj!r}")

    def set_nsvalue_vector4(
        self, val: Any, x: float, y: float, z: float, w: float
    ) -> None:
        """Set an NSValue SCNVector4 in-place."""
        obj = self._resolve_through_uids(val)
        if isinstance(obj, dict) and "NS.rectval" in obj:
            rectval_ref = obj["NS.rectval"]
            formatted = f"{{{{{x}, {y}}}, {{{z}, {w}}}}}"
            if isinstance(rectval_ref, plistlib.UID):
                self._objects[rectval_ref.data] = formatted
            else:
                obj["NS.rectval"] = formatted
        else:
            raise ValueError(f"Cannot set vector4 on {obj!r}")

    def _resolve_through_uids(self, val: Any, max_hops: int = 5) -> Any:
        """Follow a chain of UIDs until we reach a non-UID value."""
        for _ in range(max_hops):
            if isinstance(val, plistlib.UID):
                idx = val.data
                if idx == 0:
                    return None
                val = self._objects[idx]
            else:
                return val
        return val

    def find_objects_by_class(self, class_name: str) -> list[tuple[int, dict]]:
        """Find all objects in $objects with the given class name."""
        results = []
        for i, obj in enumerate(self._objects):
            if isinstance(obj, dict) and self.get_class_name(obj) == class_name:
                results.append((i, obj))
        return results

    def find_node_by_name(self, name: str) -> tuple[int, dict] | None:
        """Find an SCNNode by its name field."""
        for i, obj in enumerate(self._objects):
            if not isinstance(obj, dict):
                continue
            name_ref = obj.get("name")
            if name_ref is not None:
                resolved_name = self.resolve(name_ref)
                if resolved_name == name and self.get_class_name(obj) == "SCNNode":
                    return (i, obj)
        return None

    @staticmethod
    def _resolve_uid(val: Any) -> int:
        if isinstance(val, plistlib.UID):
            return val.data
        raise ValueError(f"Expected UID, got {type(val)}")
