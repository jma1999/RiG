import re
import sqlglot

ALLOWED_TABLES = {
    "telemetry_observations",
    "telemetry_latest",
    "sensor_space_enriched_clean",
    "dt_sensor_map",
}

FORBIDDEN_SQL = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE)\b",
    re.IGNORECASE,
)


def validate_sql(query: str) -> dict:
    if FORBIDDEN_SQL.search(query):
        return {"ok": False, "reason": "forbidden_sql_keyword"}

    try:
        parsed = sqlglot.parse_one(query, read="postgres")
    except Exception as e:
        return {"ok": False, "reason": f"parse_error: {e}"}

    if parsed.key.upper() not in {"SELECT", "WITH"}:
        return {"ok": False, "reason": "only_select_or_with_allowed"}

    query_upper = query.upper()
    used_tables = {t.lower() for t in ALLOWED_TABLES if t.upper() in query_upper}
    if not used_tables:
        return {"ok": False, "reason": "no_allowed_tables_found"}

    return {"ok": True, "used_tables": sorted(used_tables)}