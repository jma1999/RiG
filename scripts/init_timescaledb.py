"""
Initialize TimescaleDB schema for telemetry storage.
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os

TIMESCALEDB_HOST = os.getenv("TIMESCALEDB_HOST", "localhost")
TIMESCALEDB_PORT = os.getenv("TIMESCALEDB_PORT", "5432")
TIMESCALEDB_DB = os.getenv("TIMESCALEDB_DB", "rig_timeseries")
TIMESCALEDB_USER = os.getenv("TIMESCALEDB_USER", "rig_user")
TIMESCALEDB_PASSWORD = os.getenv("TIMESCALEDB_PASSWORD", "rig_password")

def init_timescaledb():
    """Initialize TimescaleDB schema."""
    try:
        conn = psycopg2.connect(
            host=TIMESCALEDB_HOST,
            port=TIMESCALEDB_PORT,
            dbname=TIMESCALEDB_DB,
            user=TIMESCALEDB_USER,
            password=TIMESCALEDB_PASSWORD
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # 1) Create base table if it doesn't exist
        cur.execute("""
            CREATE TABLE IF NOT EXISTS telemetry_sample (
                time TIMESTAMPTZ NOT NULL,
                point_id TEXT NOT NULL,
                value DOUBLE PRECISION,
                quality TEXT
            );
        """)
        
        # 2) Check if it's already a hypertable
        cur.execute("""
            SELECT EXISTS (
                SELECT 1
                FROM timescaledb_information.hypertables
                WHERE hypertable_schema = 'public'
                  AND hypertable_name   = 'telemetry_sample'
            );
        """)
        is_hypertable = cur.fetchone()[0]
        
        if not is_hypertable:
            # 3) Convert to hypertable
            cur.execute(
                "SELECT create_hypertable('telemetry_sample', 'time', chunk_time_interval => INTERVAL '1 day');"
            )
            print("✅ Created hypertable 'telemetry_sample'")
            
            # 4) Add primary key on (time, point_id)
            try:
                cur.execute("""
                    ALTER TABLE telemetry_sample 
                    ADD CONSTRAINT telemetry_sample_pkey PRIMARY KEY (time, point_id);
                """)
                print("✅ Added primary key constraint")
            except Exception as e:
                print(f"ℹ️  Primary key constraint may already exist: {e}")
        else:
            print("ℹ️  Hypertable 'telemetry_sample' already exists")
        
        # 5) Create index if it doesn't exist
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_telemetry_sample_point_id 
            ON telemetry_sample (point_id);
        """)
        
        print("✅ TimescaleDB schema initialized successfully")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Failed to initialize TimescaleDB: {e}")
        raise

if __name__ == "__main__":
    init_timescaledb()
