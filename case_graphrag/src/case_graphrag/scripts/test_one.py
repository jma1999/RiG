from case_graphrag.graph.workflow import graph

questions = [
    "Which canonical URI corresponds to Sensor32?",
    "What is the latest reading for Sensor40?",
    "What is the average temperature in Office1 over the export window?",
]

for q in questions:
    out = graph.invoke({"question": q})
    print("=" * 80)
    print("Q:", q)
    print("ROUTER:", out.get("router"))
    print("PLAN:", out.get("plan"))
    print("ANSWER:", out.get("final_answer"))
    print("EVIDENCE:", out.get("evidence"))
    print("ERRORS:", out.get("errors"))
    if out.get("sparql_query"):
        print("SPARQL:", out["sparql_query"].query_text)
    if out.get("sql_query"):
        print("SQL:", out["sql_query"].query_text)
    if out.get("sparql_validation"):
        print("SPARQL VALIDATION:", out.get("sparql_validation"))
    if out.get("sql_validation"):
        print("SQL VALIDATION:", out.get("sql_validation"))
    if out.get("sparql_result"):
        print("SPARQL ROWS:", out["sparql_result"].row_count)
    if out.get("sql_result"):
        print("SQL ROWS:", out["sql_result"].row_count)