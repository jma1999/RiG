from case_graphrag.graph.workflow import graph

questions = [
    "How many rooms are in this project?",
    "What is the average temperature in the office?",
    "Is the temperature in the office comfortable?"
]

for q in questions:
    out = graph.invoke({"question": q})
    print("=" * 100)
    print("Q:", q)
    print("ROUTER:", out.get("router"))
    print("ENTITY RESOLUTION:", out.get("entity_resolution"))
    print("PLAN:", out.get("plan"))
    print("ANSWER:", out.get("final_answer"))
    print("EVIDENCE:", out.get("evidence"))
    print("ERRORS:", out.get("errors"))
    if out.get("sql_query"):
        print("SQL:", out["sql_query"].query_text)
    if out.get("sparql_query"):
        print("SPARQL:", out["sparql_query"].query_text)
    if out.get("derived_reasoning"):
        print("DERIVED REASONING:", out["derived_reasoning"])