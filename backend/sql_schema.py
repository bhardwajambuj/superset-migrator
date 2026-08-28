import re
from typing import Mapping


_IDENTIFIER = r'`[^`]+`|"[^"]+"|\[[^\]]+\]|[A-Za-z_][\w$]*'

_WITH_HEAD = re.compile(r"\bWITH(?:\s+RECURSIVE)?\s+", re.IGNORECASE)

_CTE_NAME_AT_START = re.compile(
    rf"\s*(?P<name>{_IDENTIFIER})"
    rf"(?:\s*\([^)]*\))?"
    rf"\s+AS\s*\(",
    re.IGNORECASE,
)

# Keyword-prefixed two-part refs (FROM/JOIN/...) plus optional third part
# (schema.table.column) so SELECT lists inside CTEs are covered.
_QUALIFIED_REF = re.compile(
    rf"(?P<prefix>\b(?:from|join|update|into|table)\s+)?"
    rf"(?P<schema>{_IDENTIFIER})"
    rf"(?P<separator>\s*\.\s*)"
    rf"(?P<table>{_IDENTIFIER})"
    rf"(?:(?P<colsep>\s*\.\s*)(?P<column>{_IDENTIFIER}))?",
    re.IGNORECASE,
)


def _unquote_identifier(identifier: str) -> str:
    if len(identifier) >= 2:
        quote_pairs = {"`": "`", '"': '"', "[": "]"}
        closing = quote_pairs.get(identifier[0])
        if closing and identifier.endswith(closing):
            return identifier[1:-1]
    return identifier


def _quote_like(source_identifier: str, target_identifier: str) -> str:
    if source_identifier.startswith("`") and source_identifier.endswith("`"):
        return f"`{target_identifier}`"
    if source_identifier.startswith('"') and source_identifier.endswith('"'):
        return f'"{target_identifier}"'
    if source_identifier.startswith("[") and source_identifier.endswith("]"):
        return f"[{target_identifier}]"
    return target_identifier


def _skip_balanced_paren(sql: str, start: int) -> int:
    """Advance past a `(...)` group that began just before `start`."""
    depth = 1
    i = start
    while i < len(sql) and depth:
        ch = sql[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        i += 1
    return i


def extract_cte_names(sql: str) -> set[str]:
    """Return CTE names declared in WITH / WITH RECURSIVE clauses."""
    names: set[str] = set()
    for head in _WITH_HEAD.finditer(sql):
        pos = head.end()
        while pos < len(sql):
            match = _CTE_NAME_AT_START.match(sql, pos)
            if not match:
                break
            names.add(_unquote_identifier(match.group("name")))
            pos = _skip_balanced_paren(sql, match.end())
            while pos < len(sql) and sql[pos].isspace():
                pos += 1
            if pos < len(sql) and sql[pos] == ",":
                pos += 1
                continue
            break
    return names


def _should_rewrite(match: re.Match, cte_names: set[str]) -> bool:
    schema = _unquote_identifier(match.group("schema"))
    if schema in cte_names:
        return False
    # Keyword-prefixed two-part (FROM schema.table) or three-part
    # (schema.table.column), including inside CTE bodies.
    return bool(match.group("prefix") or match.group("column"))


def extract_query_schemas(sql: str) -> set[str]:
    """Return schema identifiers from qualified table references in SQL text."""
    cte_names = extract_cte_names(sql)
    schemas: set[str] = set()
    for match in _QUALIFIED_REF.finditer(sql):
        if not _should_rewrite(match, cte_names):
            continue
        schemas.add(_unquote_identifier(match.group("schema")))
    return schemas


def replace_query_schemas(sql: str, schema_map: Mapping[str, str]) -> tuple[str, int]:
    """Replace mapped schema identifiers in qualified table references."""
    cte_names = extract_cte_names(sql)
    replacements = 0

    def replace_match(match: re.Match) -> str:
        nonlocal replacements

        if not _should_rewrite(match, cte_names):
            return match.group(0)

        source_identifier = match.group("schema")
        source_schema = _unquote_identifier(source_identifier)
        target_schema = schema_map.get(source_schema)

        if target_schema is None or target_schema == source_schema:
            return match.group(0)

        replacements += 1
        rewritten = (
            f"{match.group('prefix') or ''}"
            f"{_quote_like(source_identifier, target_schema)}"
            f"{match.group('separator')}"
            f"{match.group('table')}"
        )
        if match.group("column"):
            rewritten += f"{match.group('colsep')}{match.group('column')}"
        return rewritten

    return _QUALIFIED_REF.sub(replace_match, sql), replacements
