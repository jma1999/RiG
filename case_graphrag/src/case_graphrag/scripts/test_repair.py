from case_graphrag.graph.workflow import graph

questions = [
    "Which room has the most humidity sensors?",
    "Which spaces have telemetry available?",
    "Which sensors in Office1 have humidity?"
]

for q in questions:
    out = graph.invoke({"question": q})
    print("=" * 100)
    print("Q:", q)
    print("ANSWER:", out.get("final_answer"))
    print("ERRORS:", out.get("errors"))
    print("SQL REPAIR COUNT:", out.get("sql_repair_count"))
    print("SPARQL REPAIR COUNT:", out.get("sparql_repair_count"))
    if out.get("sql_query"):
        print("SQL:", out["sql_query"].query_text)
    if out.get("sparql_query"):
        print("SPARQL:", out["sparql_query"].query_text)