from ..db.graphdb import run_sparql_query
from ..models import ExecutionResult

def sparql_executor_node(state):
    query = state["sparql_query"].query_text

    try:
        cols, rows, meta = run_sparql_query(query)

        return {
            "sparql_result": ExecutionResult(
                ok=True,
                columns=cols,
                rows=rows,
                row_count=len(rows),
                metadata=meta,
            )
        }

    except Exception as e:
        return {
            "sparql_result": ExecutionResult(
                ok=False,
                error=str(e),
            ),
            "errors": state.get("errors", []) + [
                f"sparql_execution_failed:{e}"
            ],
        }