from ..validators.sparql_validator import validate_sparql


def sparql_validator_node(state):
    sparql_query = state.get("sparql_query")

    if sparql_query is None:
        return {
            "sparql_validation": {
                "ok": False,
                "reason": "missing_sparql_query",
            },
            "errors": state.get("errors", []) + [
                "sparql_validation_failed:missing_sparql_query"
            ],
        }

    query = sparql_query.query_text
    result = validate_sparql(query)

    if not result["ok"]:
        return {
            "sparql_validation": result,
            "errors": state.get("errors", []) + [
                f"sparql_validation_failed:{result['reason']}"
            ],
        }

    return {
        "sparql_validation": result
    }
