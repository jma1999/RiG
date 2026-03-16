from pathlib import Path
from case_graphrag.eval.runner import run_eval

if __name__ == "__main__":
    eval_path = "case_graphrag/data/CASE_EvaluationSet.normalized.json"
    output_path = "case_graphrag/data/CASE_EvaluationResults.json"
    run_eval(eval_path, output_path)