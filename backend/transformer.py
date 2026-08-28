"""
transformer.py — Apply database/schema mappings and repack a transformed ZIP.
"""

import io
import zipfile

import yaml

from dashboard_uuid import (
    backfill_dashboard_chart_uuids,
    chart_id_from_filename,
    harvest_uuids_from_dashboard,
    uuid_from_chart_yaml,
)
from models import TransformConfig, TransformSummary
from sql_schema import replace_query_schemas


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _dump_yaml(content: dict) -> bytes:
    """Serialise a dict back to YAML bytes, preserving unicode and field order."""
    return yaml.dump(
        content,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    ).encode("utf-8")


def _category(norm_path: str) -> str:
    """Return the category segment (databases / datasets / charts / dashboards)."""
    parts = norm_path.split("/")
    return parts[1] if len(parts) > 1 else ""


def _build_chart_id_to_uuid(entries: list[tuple]) -> dict[int, str]:
    """
    Build chartId -> uuid from chart YAMLs, then supplement from dashboard
    inventory nodes that already carry both fields.
    """
    id_to_uuid: dict[int, str] = {}

    for _entry, norm, data in entries:
        if _entry.is_dir() or not norm.endswith(".yaml"):
            continue
        cat = _category(norm)
        if cat == "charts":
            chart_id = chart_id_from_filename(norm)
            if chart_id is None:
                continue
            uid = uuid_from_chart_yaml(data)
            if uid:
                id_to_uuid[chart_id] = uid

    for _entry, norm, data in entries:
        if _entry.is_dir() or not norm.endswith(".yaml"):
            continue
        if _category(norm) != "dashboards":
            continue
        id_to_uuid.update(harvest_uuids_from_dashboard(data))

    return id_to_uuid


# ---------------------------------------------------------------------------
# Main transform function
# ---------------------------------------------------------------------------

def transform_export_zip(
    zip_bytes: bytes, config: TransformConfig
) -> tuple[bytes, TransformSummary]:
    """
    Apply database and schema mappings to a Superset export ZIP.

    Also backfills missing meta.uuid on dashboard position CHART nodes so
    Superset can remap chartIds on import.

    Returns:
        output_zip:  Transformed ZIP as bytes, ready for download.
        summary:     Counts of what was changed (for UI feedback).
    """
    # Build fast lookup dicts
    db_map = {m.source_name: m for m in config.database_mappings}
    schema_map = {m.source: m.target for m in config.schema_mappings}

    # Counters for summary
    databases_patched = 0
    datasets_patched = 0
    schemas_patched = 0
    chart_uuids_backfilled = 0
    files_unchanged = 0

    # Pass 1: materialise entries (charts may appear after dashboards in the ZIP)
    entries: list[tuple] = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf_in:
        for entry in zf_in.infolist():
            name = entry.filename
            data = zf_in.read(name)
            norm = name.replace("\\", "/")
            entries.append((entry, norm, data))

    id_to_uuid = _build_chart_id_to_uuid(entries)

    output_buf = io.BytesIO()
    with zipfile.ZipFile(output_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf_out:
        for entry, norm, data in entries:
            name = entry.filename

            # Pass directory entries through unchanged
            if entry.is_dir():
                zf_out.writestr(entry, data)
                continue

            cat = _category(norm)

            # ── databases/*.yaml ──────────────────────────────────────────
            if cat == "databases" and name.endswith(".yaml"):
                content = yaml.safe_load(data.decode("utf-8"))
                src_name = content.get("database_name", "")

                if src_name in db_map:
                    mapping = db_map[src_name]
                    content["database_name"] = mapping.target_name
                    content["sqlalchemy_uri"] = mapping.target_sqlalchemy_uri

                    # Rename file on disk if database_name changes
                    if mapping.target_name != src_name:
                        new_name = norm.replace(
                            f"databases/{src_name}.yaml",
                            f"databases/{mapping.target_name}.yaml",
                        )
                    else:
                        new_name = norm

                    zf_out.writestr(new_name, _dump_yaml(content))
                    databases_patched += 1
                else:
                    zf_out.writestr(name, data)
                    files_unchanged += 1

            # ── datasets/**/*.yaml ───────────────────────────────────────
            elif cat == "datasets" and name.endswith(".yaml"):
                content = yaml.safe_load(data.decode("utf-8"))
                parts = norm.split("/")
                changed = False
                new_name = norm

                # Rename dataset subfolder if its parent database was renamed
                if len(parts) >= 3:
                    folder_db_name = parts[2]
                    if folder_db_name in db_map:
                        mapping = db_map[folder_db_name]
                        if mapping.target_name != folder_db_name:
                            new_name = new_name.replace(
                                f"datasets/{folder_db_name}/",
                                f"datasets/{mapping.target_name}/",
                                1,
                            )
                            changed = True

                # Replace schema value
                src_schema = content.get("schema") or ""
                if src_schema in schema_map:
                    target_schema = schema_map[src_schema]
                    if target_schema != src_schema:
                        content["schema"] = target_schema
                        schemas_patched += 1
                        changed = True

                dataset_sql = content.get("sql")
                if isinstance(dataset_sql, str):
                    patched_sql, replacements = replace_query_schemas(
                        dataset_sql,
                        schema_map,
                    )
                    if replacements:
                        content["sql"] = patched_sql
                        schemas_patched += replacements
                        changed = True

                zf_out.writestr(new_name, _dump_yaml(content))
                if changed:
                    datasets_patched += 1
                else:
                    files_unchanged += 1

            # ── dashboards/*.yaml — backfill missing chart UUIDs ──────────
            elif cat == "dashboards" and name.endswith(".yaml"):
                text = data.decode("utf-8")
                patched_text, filled = backfill_dashboard_chart_uuids(
                    text, id_to_uuid
                )
                if filled:
                    zf_out.writestr(name, patched_text.encode("utf-8"))
                    chart_uuids_backfilled += filled
                else:
                    zf_out.writestr(name, data)
                    files_unchanged += 1

            # ── charts, metadata, other ───────────────────────────────────
            else:
                zf_out.writestr(name, data)
                files_unchanged += 1

    summary = TransformSummary(
        databases_patched=databases_patched,
        schemas_patched=schemas_patched,
        datasets_patched=datasets_patched,
        chart_uuids_backfilled=chart_uuids_backfilled,
        files_unchanged=files_unchanged,
    )

    return output_buf.getvalue(), summary
