import os
import random
from datetime import datetime, timedelta, timezone

import psycopg2

conn = psycopg2.connect(
    host=os.getenv("TIMESCALEDB_HOST", "localhost"),
    port=int(os.getenv("TIMESCALEDB_PORT", "5432")),
    dbname=os.getenv("TIMESCALEDB_DB", "rig_timeseries"),
    user=os.getenv("TIMESCALEDB_USER", "rig_user"),
    password=os.getenv("TIMESCALEDB_PASSWORD", "rig_password"),
)
conn.autocommit = True

cur = conn.cursor()

point_id = "ft_136276_sat"

# generate 60 minutes of data at 1-min resolution
now = datetime.now(timezone.utc)
base_temp = 20.0

rows = []
for i in range(60):
    ts = now - timedelta(minutes=(60 - i))
    # small random walk around 20°C
    base_temp += random.uniform(-0.1, 0.1)
    rows.append((ts, point_id, round(base_temp, 2), "good"))

cur.executemany(
    """
    INSERT INTO telemetry_sample (time, point_id, value, quality)
    VALUES (%s, %s, %s, %s)
    """,
    rows,
)

cur.close()
conn.close()
print("Inserted 60 rows for ft_136276_sat")
