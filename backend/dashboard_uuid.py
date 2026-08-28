"""
dashboard_uuid.py — Backfill missing meta.uuid on dashboard position CHART nodes.

Superset import remaps chartId via uuid. CHART tiles without meta.uuid keep stale
source IDs and render as MissingChart after cross-environment import.
"""

from __future__ import annotations

import re
from typing import Dict, Tuple

import yaml

_CHART_ID_LINE = re.compile(r"^(\s*)chartId:\s*(\d+)\s*$")
_CHART_FILE_ID = re.compile(r"_(\d+)\.yaml$", re.IGNORECASE)


def chart_id_from_filename(filename: str) -> int | None:
    """Extract numeric chart id from export filename like My_Chart_334.yaml."""
    base = filename.replace("\\", "/").rsplit("/", 1)[-1]
    match = _CHART_FILE_ID.search(base)
    return int(match.group(1)) if match else None


def uuid_from_chart_yaml(data: bytes) -> str | None:
    """Return chart uuid from chart YAML bytes, if present."""
    content = yaml.safe_load(data.decode("utf-8"))
    if not isinstance(content, dict):
        return None
    uid = content.get("uuid")
    return str(uid) if uid else None


def harvest_uuids_from_dashboard(data: bytes) -> Dict[int, str]:
    """
    Collect chartId -> uuid from position CHART nodes that already have both.
    Used as a supplement when chart YAML map is incomplete.
    """
    content = yaml.safe_load(data.decode("utf-8"))
    if not isinstance(content, dict):
        return {}

    found: Dict[int, str] = {}
    position = content.get("position") or {}
    if not isinstance(position, dict):
        return {}

    for node in position.values():
        if not isinstance(node, dict) or node.get("type") != "CHART":
            continue
        meta = node.get("meta") or {}
        chart_id = meta.get("chartId")
        uid = meta.get("uuid")
        if chart_id is None or not uid:
            continue
        found[int(chart_id)] = str(uid)

    return found


def backfill_dashboard_chart_uuids(
    yaml_text: str, id_to_uuid: Dict[int, str]
) -> Tuple[str, int]:
    """
    Insert meta.uuid after chartId when a CHART meta block is missing uuid.

    Uses a line-preserving text patch (not a full YAML dump) so CSS and layout
    formatting stay intact for Superset import.

    Returns:
        (patched_text, number_of_uuids_inserted)
    """
    if not id_to_uuid:
        return yaml_text, 0

    lines = yaml_text.splitlines(keepends=True)
    out: list[str] = []
    filled = 0
    i = 0

    while i < len(lines):
        line = lines[i]
        out.append(line)
        match = _CHART_ID_LINE.match(line.rstrip("\r\n"))
        if match:
            indent, chart_id_s = match.group(1), match.group(2)
            chart_id = int(chart_id_s)
            has_uuid = False
            j = i + 1
            while j < len(lines):
                look = lines[j]
                if look.strip() == "":
                    j += 1
                    continue
                look_indent = len(look) - len(look.lstrip(" "))
                if look_indent < len(indent):
                    break
                if look.startswith(f"{indent}uuid:"):
                    has_uuid = True
                    break
                j += 1

            if not has_uuid:
                uid = id_to_uuid.get(chart_id)
                if uid:
                    newline = "\r\n" if line.endswith("\r\n") else "\n"
                    out.append(f"{indent}uuid: {uid}{newline}")
                    filled += 1
        i += 1

    return "".join(out), filled
