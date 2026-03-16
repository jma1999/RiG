import re

FORBIDDEN_SPARQL = re.compile(
    r"\b(INSERT|DELETE|CLEAR|LOAD|CREATE|DROP|MOVE|COPY|ADD)\b",
    re.IGNORECASE,
)

ALLOWED_GRAPHS = {
    "https://example.com/case-office/g/overlay",
    "https://example.com/case-office/g/223p",
}


def validate_sparql(query: str):
    upper_q = query.upper()

    if FORBIDDEN_SPARQL.search(query):
        return {"ok": False, "reason": "forbidden_operation"}

    if "SELECT" not in upper_q:
        return {"ok": False, "reason": "must_be_select"}

    used_graphs = [g for g in ALLOWED_GRAPHS if g in query]
    if not used_graphs:
        return {"ok": False, "reason": "no_allowed_named_graphs"}

    if "S223:" in upper_q and "PREFIX S223:" not in upper_q:
        return {"ok": False, "reason": "missing_s223_prefix"}

    if "RDFS:" in upper_q and "PREFIX RDFS:" not in upper_q:
        return {"ok": False, "reason": "missing_rdfs_prefix"}

    return {
        "ok": True,
        "used_graphs": used_graphs,
    }