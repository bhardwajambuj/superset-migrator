"""
main.py — FastAPI application entry point.

Endpoints:
  GET  /health         — Liveness probe
  GET  /api/health     — Same probe under the API prefix
  POST /api/parse      — Upload ZIP, return detected databases + schemas
  POST /api/transform  — Upload ZIP + config JSON, return transformed ZIP
"""

import io
import json
import os
import zipfile

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from models import ParseResult, TransformConfig
from parser import parse_export_zip
from transformer import transform_export_zip

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Superset Dashboard Migrator",
    description="Transform Superset dashboard exports between environments.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Tighten in production if needed
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_zip(file: UploadFile) -> None:
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a .zip export.")


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------

@app.get("/health", summary="Liveness probe")
@app.get("/api/health", summary="Liveness probe")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/parse", response_model=ParseResult, summary="Parse a Superset export ZIP")
async def parse_endpoint(file: UploadFile = File(...)):
    """
    Upload a Superset dashboard export ZIP.
    Returns the detected database connections, unique schemas, and file counts.
    """
    _require_zip(file)
    zip_bytes = await file.read()

    try:
        result, _ = parse_export_zip(zip_bytes)
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="File is not a valid ZIP archive.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unexpected parse error: {exc}")

    return result


@app.post("/api/transform", summary="Transform and download a patched ZIP")
async def transform_endpoint(
    file: UploadFile = File(...),
    config: str = Form(...),
):
    """
    Upload a Superset dashboard export ZIP alongside a JSON mapping config.
    Returns the transformed ZIP as a file download.

    The `config` form field must be a JSON string matching TransformConfig:
    {
      "database_mappings": [
        { "source_name": "read_only",
          "target_name": "read_only",
          "target_sqlalchemy_uri": "mysql+pymysql://user:pass@qa-host:9030" }
      ],
      "schema_mappings": [
        { "source": "dev_analytics", "target": "qa_analytics" }
      ]
    }
    """
    _require_zip(file)

    try:
        transform_config = TransformConfig.model_validate(json.loads(config))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid config JSON: {exc}")

    zip_bytes = await file.read()

    try:
        output_zip, summary = transform_export_zip(zip_bytes, transform_config)
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="File is not a valid ZIP archive.")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Transform failed: {exc}")

    base = file.filename.removesuffix(".zip")
    out_filename = f"{base}_migrated.zip"

    return StreamingResponse(
        io.BytesIO(output_zip),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{out_filename}"',
            # Expose summary counts as response headers so the frontend can read them
            "X-Databases-Patched": str(summary.databases_patched),
            "X-Schemas-Patched": str(summary.schemas_patched),
            "X-Datasets-Patched": str(summary.datasets_patched),
            "X-Chart-Uuids-Backfilled": str(summary.chart_uuids_backfilled),
            "X-Files-Unchanged": str(summary.files_unchanged),
            "Access-Control-Expose-Headers": (
                "X-Databases-Patched, X-Schemas-Patched, "
                "X-Datasets-Patched, X-Chart-Uuids-Backfilled, "
                "X-Files-Unchanged"
            ),
        },
    )


# ---------------------------------------------------------------------------
# Serve built React frontend (production only)
# ---------------------------------------------------------------------------

_frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(_frontend_dist):
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="static")


# ---------------------------------------------------------------------------
# Dev entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
