import json
from case_graphrag.graph.workflow import graph

INPUT_PATH = "case_graphrag/data/CASE_SurpriseQuestions.json"
OUTPUT_PATH = "case_graphrag/data/CASE_SurpriseResults.json"


def safe_model_dump(obj):
    if obj is None:
        return None
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    return obj


def main():
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        items = json.load(f)

    outputs = []

    for item in items:
        qid = item["question_id"]
        qtext = item["question_text"]

        out = graph.invoke({"question": qtext})

        outputs.append({
            "question_id": qid,
            "question_text": qtext,
            "predicted": {
                "router": safe_model_dump(out.get("router")),
                "plan": safe_model_dump(out.get("plan")),
                "final_answer": out.get("final_answer"),
                "evidence": out.get("evidence"),
                "errors": out.get("errors"),
                "sql_query": out["sql_query"].query_text if out.get("sql_query") else None,
                "sparql_query": out["sparql_query"].query_text if out.get("sparql_query") else None,
                "sql_validation": out.get("sql_validation"),
                "sparql_validation": out.get("sparql_validation"),
                "sql_result": safe_model_dump(out.get("sql_result")),
                "sparql_result": safe_model_dump(out.get("sparql_result")),
            }
        })

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(outputs, f, indent=2, default=str)

    print(f"Wrote {len(outputs)} surprise results to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()