from case_graphrag.graph.workflow import graph

QUESTION = "Which spaces have telemetry available?"

if __name__ == "__main__":
    out = graph.invoke({"question": QUESTION})

    print("=" * 100)
    print("QUESTION:", QUESTION)
    print("ROUTER:", out.get("router"))
    print("PLAN:", out.get("plan"))

    if out.get("sparql_query"):
        print("\nSPARQL QUERY:\n", out["sparql_query"].query_text)
    if out.get("sparql_validation"):
        print("\nSPARQL VALIDATION:\n", out["sparql_validation"])
    if out.get("sparql_result"):
        print("\nSPARQL RESULT ROWS:", out["sparql_result"].row_count)

    if out.get("sql_query"):
        print("\nSQL QUERY:\n", out["sql_query"].query_text)
    if out.get("sql_validation"):
        print("\nSQL VALIDATION:\n", out["sql_validation"])
    if out.get("sql_result"):
        print("\nSQL RESULT ROWS:", out["sql_result"].row_count)

    print("\nFINAL ANSWER:\n", out.get("final_answer"))
    print("\nEVIDENCE:\n", out.get("evidence"))
    print("\nERRORS:\n", out.get("errors"))