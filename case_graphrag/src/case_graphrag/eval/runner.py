from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime

from case_graphrag.graph.workflow import graph


def load_eval_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_model_dump(obj):
    if obj is None:
        return None
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    return obj


def run_eval(eval_path: str, output_path: str):
    items = load_eval_json(eval_path)
    results = []

    for item in items:
        question_id = item.get("question_id")
        question_text = item.get("question_text")

        out = graph.invoke({"question": question_text})

        results.append({
            "question_id": question_id,
            "question_text": question_text,
            "gold": item,
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

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"Wrote {len(results)} evaluation results to {output_path}")