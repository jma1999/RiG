from ..db.postgres import run_sql_query
from ..models import ExecutionResult

def sql_executor_node(state):
    query = state["sql_query"].query_text
    try:
        cols, rows, meta = run_sql_query(query)
        return {
            "sql_result": ExecutionResult(
                ok=True,
                columns=cols,
                rows=rows,
                row_count=len(rows),
                metadata=meta,
            )
        }
    except Exception as e:
        return {
            "sql_result": ExecutionResult(
                ok=False,
                error=str(e),
            ),
            "errors": state.get("errors", []) + [f"sql_execution_failed:{e}"],
        }