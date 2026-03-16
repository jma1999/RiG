import os
import requests
from dotenv import load_dotenv

load_dotenv()

GRAPHDB_ENDPOINT = os.environ["GRAPHDB_ENDPOINT"]


def run_sparql_query(query: str) -> tuple[list[str], list[dict], dict]:
    headers = {
        "Accept": "application/sparql-results+json",
        "Content-Type": "application/sparql-query",
    }
    resp = requests.post(GRAPHDB_ENDPOINT, data=query.encode("utf-8"), headers=headers, timeout=60)
    resp.raise_for_status()
    payload = resp.json()

    vars_ = payload["head"]["vars"]
    rows = []
    for b in payload["results"]["bindings"]:
        row = {}
        for v in vars_:
            row[v] = b[v]["value"] if v in b else None
        rows.append(row)

    return vars_, rows, {"source": "graphdb"}