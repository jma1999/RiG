from ..validators.sql_validator import validate_sql

def sql_validator_node(state):
    query = state["sql_query"].query_text
    result = validate_sql(query)
    if not result["ok"]:
        return {
            "sql_validation": result,
            "errors": state.get("errors", []) + [f"sql_validation_failed:{result['reason']}"],
        }
    return {"sql_validation": result}