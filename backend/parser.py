"""
parser.py — Unpack a Superset export ZIP and extract source connection/schema info.
"""

import io
import zipfile
from typing import Tuple, Dict

import yaml

from models import ParseResult, DatabaseInfo
from sql_schema import extract_query_schemas


def parse_export_zip(zip_bytes: bytes) -> Tuple[ParseResult, Dict[str, bytes]]:
    """
    Parse a Superset dashboard export ZIP.

    Returns:
        result:    ParseResult with detected databases, schemas and file counts.
        raw_files: Dict mapping zip-internal path -> raw bytes (used by transformer).

    Raises:
        ValueError: if the ZIP doesn't look like a valid Superset export.
        zipfile.BadZipFile: if the bytes aren't a valid ZIP.
    """
    raw_files: Dict[str, bytes] = {}
    databases: list[DatabaseInfo] = []
    schemas: set[str] = set()
    dataset_count = 0
    chart_count = 0
    dashboard_count = 0

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for entry in zf.infolist():
            name = entry.filename
            data = zf.read(name)
            raw_files[name] = data

            # Skip directory entries
            if entry.is_dir():
                continue

            # Normalise to forward slashes and split
            parts = name.replace("\\", "/").split("/")
            # Expected layout: <root>/<category>/[<subfolder>/]<file.yaml>
            # parts[0] = root export folder, parts[1] = category
            if len(parts) < 3:
                continue

            category = parts[1]

            if category == "databases" and name.endswith(".yaml"):
                content = yaml.safe_load(data.decode("utf-8"))
                databases.append(
                    DatabaseInfo(
                        name=content.get("database_name", ""),
                        sqlalchemy_uri=content.get("sqlalchemy_uri", ""),
                        uuid=content.get("uuid", ""),
                    )
                )

            elif category == "datasets" and name.endswith(".yaml"):
                content = yaml.safe_load(data.decode("utf-8"))
                schema = content.get("schema") or ""
                schemas.add(schema)

                dataset_sql = content.get("sql")
                if isinstance(dataset_sql, str):
                    schemas.update(extract_query_schemas(dataset_sql))

                dataset_count += 1

            elif category == "charts" and name.endswith(".yaml"):
                chart_count += 1

            elif category == "dashboards" and name.endswith(".yaml"):
                dashboard_count += 1

    if not databases:
        raise ValueError(
            "No database definitions found. Is this a valid Superset dashboard export?"
        )

    return (
        ParseResult(
            databases=databases,
            schemas=sorted(schemas),
            dataset_count=dataset_count,
            chart_count=chart_count,
            dashboard_count=dashboard_count,
        ),
        raw_files,
    )
