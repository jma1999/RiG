import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

engine = create_engine(os.environ["POSTGRES_URL"])


def run_sql_query(query: str) -> tuple[list[str], list[dict], dict]:
    with engine.connect() as conn:
        result = conn.execute(text(query))
        rows = [dict(r._mapping) for r in result]
        cols = list(result.keys())
    return cols, rows, {"source": "postgres"}