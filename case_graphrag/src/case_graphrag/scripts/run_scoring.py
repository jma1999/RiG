import json
from collections import Counter, defaultdict

from case_graphrag.eval.metrics import score_result

RESULTS_PATH = "case_graphrag/data/CASE_EvaluationResults.json"
OUTPUT_PATH = "case_graphrag/data/CASE_EvaluationScores.json"


def avg(values):
    values = [v for v in values if v is not None]
    return sum(values) / len(values) if values else 0.0


def main():
    with open(RESULTS_PATH, "r", encoding="utf-8") as f:
        results = json.load(f)

    scores = [score_result(item) for item in results]

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(scores, f, indent=2)

    print("Scoring complete.")
    print(f"Wrote scores to {OUTPUT_PATH}")

    total = len(scores)
    status_counts = Counter(s["status"] for s in scores)
    by_type = defaultdict(list)
    for s in scores:
        by_type[s["answer_type"]].append(s)

    print("\n===== EVALUATION SUMMARY =====")
    print("Total questions:", total)
    print("Pass:", status_counts.get("pass", 0))
    print("Partial:", status_counts.get("partial", 0))
    print("Fail:", status_counts.get("fail", 0))
    print("Avg score:", round(avg([s["score"] for s in scores]), 3))

    print("\n===== BY ANSWER TYPE =====")
    for answer_type, items in sorted(by_type.items()):
        print(
            answer_type,
            "| count:", len(items),
            "| avg_score:", round(avg([x["score"] for x in items]), 3),
            "| pass:", sum(1 for x in items if x["status"] == "pass"),
            "| partial:", sum(1 for x in items if x["status"] == "partial"),
            "| fail:", sum(1 for x in items if x["status"] == "fail"),
        )

    print("\n===== PER QUESTION =====")
    for s in scores:
        print(
            s["question_id"],
            "| type:", s["answer_type"],
            "| status:", s["status"],
            "| score:", round(s["score"], 3),
            "| router:", s["router_intent"],
            "| root_cause:", s["root_cause_guess"],
        )

    print("\n===== FAILURES / PARTIALS =====")
    for s in scores:
        if s["status"] != "pass":
            print(
                s["question_id"],
                "| type:", s["answer_type"],
                "| status:", s["status"],
                "| score:", round(s["score"], 3),
                "| errors:", s["errors"],
                "| root_cause:", s["root_cause_guess"],
            )


if __name__ == "__main__":
    main()
