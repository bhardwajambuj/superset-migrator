from pydantic import BaseModel
from typing import List


class DatabaseInfo(BaseModel):
    name: str
    sqlalchemy_uri: str
    uuid: str


class ParseResult(BaseModel):
    databases: List[DatabaseInfo]
    schemas: List[str]
    dataset_count: int
    chart_count: int
    dashboard_count: int


class DatabaseMapping(BaseModel):
    source_name: str
    target_name: str
    target_sqlalchemy_uri: str


class SchemaMapping(BaseModel):
    source: str
    target: str


class TransformConfig(BaseModel):
    database_mappings: List[DatabaseMapping]
    schema_mappings: List[SchemaMapping]


class TransformSummary(BaseModel):
    databases_patched: int
    schemas_patched: int
    datasets_patched: int
    chart_uuids_backfilled: int
    files_unchanged: int
