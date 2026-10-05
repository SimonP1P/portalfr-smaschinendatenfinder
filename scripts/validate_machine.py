#!/usr/bin/env python3
"""Deterministic validation for one machine JSON.

Uses only the Python standard library so the orchestrator has no mandatory
third-party dependency.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schemas" / "machine.schema.json"


def fail(message):
    print(f"FAIL: {message}")
    return 1


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/validate_machine.py <machine.json>")
        return 2

    path = Path(sys.argv[1])
    if not path.is_absolute():
        path = ROOT / path

    if not path.exists():
        return fail(f"file not found: {path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return fail(f"invalid JSON: {exc}")

    required = [
        "id", "manufacturer", "series", "model", "variant", "revision",
        "machine_type", "axis_count", "axes", "workspace", "spindle",
        "mechanics", "limits", "homing", "probe", "tool_changer",
        "controller", "status", "source", "version"
    ]

    missing = [key for key in required if key not in data]
    if missing:
        return fail("missing fields: " + ", ".join(missing))

    for section, fields in {
        "manufacturer": ["id", "name"],
        "series": ["id", "name"],
        "model": ["id", "name"],
        "workspace": ["x_mm", "y_mm", "z_mm"],
        "spindle": ["type", "power_w", "min_rpm", "max_rpm"],
        "mechanics": ["frame_material", "drive_x", "drive_y", "drive_z", "linear_guides"],
        "limits": ["software_limits", "limit_switches", "hard_limits"],
        "homing": ["supported"],
        "probe": ["supported", "workpiece_probe", "tool_length_probe"],
        "tool_changer": ["supported", "type", "capacity"],
        "controller": ["controller_profile_id"],
        "source": ["type", "verified", "urls"],
    }.items():
        value = data.get(section)
        if not isinstance(value, dict):
            return fail(f"{section} must be an object")
        for field in fields:
            if field not in value:
                return fail(f"missing {section}.{field}")

    for axis in ("X", "Y", "Z"):
        value = data["axes"].get(axis)
        if not isinstance(value, dict):
            return fail(f"axes.{axis} must be an object")
        for field in ("travel_mm", "max_feed_mm_min", "max_acceleration_mm_s2"):
            if field not in value:
                return fail(f"missing axes.{axis}.{field}")

    if not isinstance(data["source"]["urls"], list):
        return fail("source.urls must be an array")

    if not data["source"]["urls"]:
        return fail("source.urls must contain at least one source")

    if data["status"] not in {"certified", "draft", "needs_review"}:
        return fail("invalid machine status")

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
