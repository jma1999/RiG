from __future__ import annotations

import math
import re
from typing import Any


def normalize_uri_tail(uri: str) -> str:
    if not uri:
        return uri
    return uri.rstrip("/").split("/")[-1]


def row_values(rows, key):
    vals = []
    for r in rows or []:
        if key in r and r[key] is not None:
            vals.append(str(r[key]))
    return vals


def extract_number(text: str) -> float | None:
    if not text:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    if not m:
        return None
    return float(m.group(0))


def nearly_equal(a: float | None, b: float | None, tol: float = 1e-2) -> bool:
    if a is None or b is None:
        return False
    return math.isclose(a, b, abs_tol=tol, rel_tol=0.0)


def predicted_sets(pred: dict[str, Any]):
    sql_result = pred.get("sql_result") or {}
    sparql_result = pred.get("sparql_result") or {}

    sql_rows = sql_result.get("rows") or []
    sparql_rows = sparql_result.get("rows") or []

    predicted_sensor_labels = set(row_values(sql_rows, "sensor_label")) | set(row_values(sparql_rows, "sensor_label"))
    predicted_metric_names = set(row_values(sql_rows, "metric_name")) | set(row_values(sparql_rows, "metric_name"))
    predicted_space_labels = set(row_values(sql_rows, "space_label")) | set(row_values(sparql_rows, "space_label")) | set(row_values(sparql_rows, "room_label"))

    predicted_device_ids = set(row_values(sql_rows, "device_id")) | set(row_values(sparql_rows, "device_id"))

    predicted_uris = set()
    for key in ["canonical_uri", "canonicalURI"]:
        predicted_uris |= {normalize_uri_tail(x) for x in row_values(sql_rows, key)}
        predicted_uris |= {normalize_uri_tail(x) for x in row_values(sparql_rows, key)}

    return {
        "sql_rows": sql_rows,
        "sparql_rows": sparql_rows,
        "sensor_labels": predicted_sensor_labels,
        "metric_names": predicted_metric_names,
        "space_labels": predicted_space_labels,
        "device_ids": predicted_device_ids,
        "uris": predicted_uris,
    }


def classify_status(score: float) -> str:
    if score >= 0.999:
        return "pass"
    if score >= 0.5:
        return "partial"
    return "fail"


def score_identity_lookup(gold: dict[str, Any], pred: dict[str, Any]) -> dict[str, Any]:
    sets = predicted_sets(pred)
    gold_space = gold.get("expected_space")
    gold_uris = {normalize_uri_tail(x) for x in (gold.get("expected_canonical_uris") or []) if x}
    gold_sensors = set(gold.get("expected_sensor_labels") or [])

    uri_recall = (len(sets["uris"] & gold_uris) / len(gold_uris)) if gold_uris else None
    sensor_recall = (len(sets["sensor_labels"] & gold_sensors) / len(gold_sensors)) if gold_sensors else None
    space_match = gold_space in sets["space_labels"] if gold_space else None

    if uri_recall is not None:
        score = uri_recall
    elif space_match is not None:
        score = 1.0 if space_match else 0.0
    else:
        score = sensor_recall or 0.0

    return {
        "space_match": space_match,
        "sensor_recall": sensor_recall,
        "metric_recall": None,
        "uri_recall": uri_recall,
        "numeric_match": None,
        "score": score,
        "status": classify_status(score),
        "root_cause_guess": None if score >= 0.999 else "identity_retrieval_mismatch",
    }


def score_set_membership(gold: dict[str, Any], pred: dict[str, Any]) -> dict[str, Any]:
    sets = predicted_sets(pred)

    gold_space = gold.get("expected_space")
    gold_sensors = set(gold.get("expected_sensor_labels") or [])

    sensor_recall = (len(sets["sensor_labels"] & gold_sensors) / len(gold_sensors)) if gold_sensors else None
    space_match = gold_space in sets["space_labels"] if gold_space else None

    score = sensor_recall if sensor_recall is not None else 0.0

    return {
        "space_match": space_match,
        "sensor_recall": sensor_recall,
        "metric_recall": None,
        "uri_recall": None,
        "numeric_match": None,
        "score": score,
        "status": classify_status(score),
        "root_cause_guess": None if score >= 0.999 else "set_membership_retrieval_incomplete",
    }


def score_latest_reading(gold: dict[str, Any], pred: dict[str, Any]) -> dict[str, Any]:
    sets = predicted_sets(pred)
    gold_space = gold.get("expected_space")
    gold_sensors = set(gold.get("expected_sensor_labels") or [])
    gold_metrics = set(gold.get("expected_metric_names") or [])
    gold_uris = {normalize_uri_tail(x) for x in (gold.get("expected_canonical_uris") or []) if x}

    sensor_recall = (len(sets["sensor_labels"] & gold_sensors) / len(gold_sensors)) if gold_sensors else None
    metric_recall = (len(sets["metric_names"] & gold_metrics) / len(gold_metrics)) if gold_metrics else None
    uri_recall = (len(sets["uris"] & gold_uris) / len(gold_uris)) if gold_uris else None
    space_match = gold_space in sets["space_labels"] if gold_space else None

    parts = []
    if sensor_recall is not None:
        parts.append(sensor_recall)
    if metric_recall is not None:
        parts.append(metric_recall)
    if uri_recall is not None:
        parts.append(uri_recall)
    if space_match is not None:
        parts.append(1.0 if space_match else 0.0)

    score = sum(parts) / len(parts) if parts else 0.0

    return {
        "space_match": space_match,
        "sensor_recall": sensor_recall,
        "metric_recall": metric_recall,
        "uri_recall": uri_recall,
        "numeric_match": None,
        "score": score,
        "status": classify_status(score),
        "root_cause_guess": None if score >= 0.999 else "latest_reading_retrieval_partial",
    }


def score_aggregation(gold: dict[str, Any], pred: dict[str, Any]) -> dict[str, Any]:
    answer = pred.get("final_answer") or ""
    sql_result = pred.get("sql_result") or {}
    sql_rows = sql_result.get("rows") or []

    gold_answer_number = extract_number(gold.get("expected_answer") or "")
    predicted_number = None

    if sql_rows:
        first_row = sql_rows[0]
        for key in ["avg_temperature", "avg_temperature_f", "average_temperature", "value_double"]:
            if key in first_row and first_row[key] is not None:
                predicted_number = float(first_row[key])
                break

    if predicted_number is None:
        predicted_number = extract_number(answer)

    numeric_match = nearly_equal(predicted_number, gold_answer_number, tol=1e-2)
    score = 1.0 if numeric_match else 0.0

    return {
        "space_match": None,
        "sensor_recall": None,
        "metric_recall": None,
        "uri_recall": None,
        "numeric_match": numeric_match,
        "score": score,
        "status": classify_status(score),
        "root_cause_guess": None if numeric_match else "aggregation_value_mismatch",
    }


def score_metric_availability(gold: dict[str, Any], pred: dict[str, Any]) -> dict[str, Any]:
    sets = predicted_sets(pred)
    gold_metrics = set(gold.get("expected_metric_names") or [])
    gold_space = gold.get("expected_space")

    metric_recall = (len(sets["metric_names"] & gold_metrics) / len(gold_metrics)) if gold_metrics else None
    space_match = gold_space in sets["space_labels"] if gold_space else None

    parts = []
    if metric_recall is not None:
        parts.append(metric_recall)
    # don't over-penalize if the aggregate/result rows don't explicitly repeat the space
    if space_match is not None:
        parts.append(1.0 if space_match else 0.0)

    score = sum(parts) / len(parts) if parts else 0.0

    return {
        "space_match": space_match,
        "sensor_recall": None,
        "metric_recall": metric_recall,
        "uri_recall": None,
        "numeric_match": None,
        "score": score,
        "status": classify_status(score),
        "root_cause_guess": None if score >= 0.999 else "metric_availability_retrieval_partial",
    }


def score_ranking_count(gold: dict[str, Any], pred: dict[str, Any]) -> dict[str, Any]:
    sets = predicted_sets(pred)
    answer = pred.get("final_answer") or ""
    sql_rows = sets["sql_rows"]
    sparql_rows = sets["sparql_rows"]

    gold_space = gold.get("expected_space")
    predicted_space = None

    if sql_rows:
        row = sql_rows[0]
        predicted_space = row.get("space_label") or row.get("room_label")
    elif sparql_rows:
        row = sparql_rows[0]
        predicted_space = row.get("space_label") or row.get("room_label")
    else:
        # fallback to answer text
        for candidate in [gold_space]:
            if candidate and candidate.lower() in answer.lower():
                predicted_space = candidate
                break

    space_match = (predicted_space == gold_space) if gold_space else None
    score = 1.0 if space_match else 0.0

    return {
        "space_match": space_match,
        "sensor_recall": None,
        "metric_recall": None,
        "uri_recall": None,
        "numeric_match": None,
        "score": score,
        "status": classify_status(score),
        "root_cause_guess": None if score >= 0.999 else "ranking_or_count_wrong_top_space",
    }


def score_coverage(gold: dict[str, Any], pred: dict[str, Any]) -> dict[str, Any]:
    sets = predicted_sets(pred)
    gold_space = gold.get("expected_space")

    # For this dataset, expected_space is a list? If not, we evaluate set overlap from answer text/evidence.
    # We'll use spaces returned in rows and compare against expected answer text if needed.
    expected_answer = gold.get("expected_answer") or ""

    predicted_spaces = sets["space_labels"]

    # pull expected spaces from answer text heuristically
    expected_spaces = set()
    for candidate in ["Kitchen5", "Office1", "Reception6", "Work Area & Storage2", "Work Area & Storage4", "Meeting Room3"]:
        if candidate in expected_answer:
            expected_spaces.add(candidate)

    if expected_spaces:
        overlap = len(predicted_spaces & expected_spaces) / len(expected_spaces)
    elif gold_space:
        overlap = 1.0 if gold_space in predicted_spaces else 0.0
    else:
        overlap = 0.0

    return {
        "space_match": None,
        "sensor_recall": None,
        "metric_recall": None,
        "uri_recall": None,
        "numeric_match": None,
        "score": overlap,
        "status": classify_status(overlap),
        "root_cause_guess": None if overlap >= 0.999 else "coverage_set_mismatch",
    }


def score_device_to_room(gold: dict[str, Any], pred: dict[str, Any]) -> dict[str, Any]:
    sets = predicted_sets(pred)
    answer = pred.get("final_answer") or ""
    gold_space = gold.get("expected_space")

    space_match = False
    if gold_space:
        if gold_space in sets["space_labels"]:
            space_match = True
        elif gold_space.lower() in answer.lower():
            space_match = True

    score = 1.0 if space_match else 0.0

    return {
        "space_match": space_match,
        "sensor_recall": None,
        "metric_recall": None,
        "uri_recall": None,
        "numeric_match": None,
        "score": score,
        "status": classify_status(score),
        "root_cause_guess": None if score >= 0.999 else "device_to_room_mapping_wrong",
    }


def score_result(item: dict) -> dict:
    gold = item["gold"]
    pred = item["predicted"]

    router = pred.get("router") or {}
    sql_result = pred.get("sql_result") or {}
    sparql_result = pred.get("sparql_result") or {}

    answer_type = gold.get("answer_type", "")

    if answer_type == "identity-lookup":
        core = score_identity_lookup(gold, pred)
    elif answer_type == "set-membership":
        core = score_set_membership(gold, pred)
    elif answer_type in ("latest-reading", "latest-readings-set"):
        core = score_latest_reading(gold, pred)
    elif answer_type == "aggregation":
        core = score_aggregation(gold, pred)
    elif answer_type == "metric-availability":
        core = score_metric_availability(gold, pred)
    elif answer_type == "ranking / count":
        core = score_ranking_count(gold, pred)
    elif answer_type == "set-membership / coverage":
        core = score_coverage(gold, pred)
    elif answer_type == "device-to-room mapping":
        core = score_device_to_room(gold, pred)
    else:
        core = {
            "space_match": None,
            "sensor_recall": None,
            "metric_recall": None,
            "uri_recall": None,
            "numeric_match": None,
            "score": 0.0,
            "status": "fail",
            "root_cause_guess": "unknown_answer_type",
        }

    return {
        "question_id": item["question_id"],
        "answer_type": answer_type,
        "router_intent": router.get("intent"),
        "sql_ok": sql_result.get("ok"),
        "sparql_ok": sparql_result.get("ok"),
        "space_match": core["space_match"],
        "sensor_recall": core["sensor_recall"],
        "metric_recall": core["metric_recall"],
        "uri_recall": core["uri_recall"],
        "numeric_match": core["numeric_match"],
        "score": core["score"],
        "status": core["status"],
        "root_cause_guess": core["root_cause_guess"],
        "errors": pred.get("errors"),
    }
