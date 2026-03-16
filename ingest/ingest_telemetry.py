import re
import pandas as pd
from sqlalchemy import create_engine
from pathlib import Path

# ---------- CONFIG ----------
RAW_CSV = Path("data/sensorReadings/dt_export.csv")   # start with sample first
GRAPH_MAP_CSV = Path("data/sensorReadings/graph_sensor_map.csv")
DB_URL = "postgresql+psycopg2://rig_user:rig_password@localhost:5433/rig_timeseries"

engine = create_engine(DB_URL)

# ---------- LOAD RAW CSV ----------
df = pd.read_csv(RAW_CSV)
df = df.rename(columns={"timestamp": "ts"})
df["ts"] = pd.to_datetime(df["ts"], utc=True)

# ---------- EXTRACT SENSOR NUMBER FROM CSV LABEL ----------
def extract_sensor_number(label: str):
    if pd.isna(label):
        return None
    m = re.search(r"#(\d+)", str(label))
    return int(m.group(1)) if m else None

df["sensor_number"] = df["name_label"].apply(extract_sensor_number)

# ---------- LOAD GRAPH MAPPING ----------
graph_map = pd.read_csv(GRAPH_MAP_CSV)

def extract_graph_sensor_number(label: str):
    if pd.isna(label):
        return None
    m = re.search(r"Sensor(\d+)", str(label))
    return int(m.group(1)) if m else None

graph_map["sensor_number"] = graph_map["label"].apply(extract_graph_sensor_number)

# ---------- CREATE DEVICE/SENSOR MAP ----------
device_map = (
    df[["device_id", "name_label", "sensor_number"]]
    .drop_duplicates()
    .merge(
        graph_map[["sensor_number", "point_uri", "sensor_223p_uri", "canonical_uri", "ifc_guid"]],
        on="sensor_number",
        how="left",
    )
)

device_map.to_csv(Path("data/sensorReadings/dt_sensor_map_generated.csv"), index=False)

# ---------- LOAD RAW TABLE ----------
raw_df = df[[
    "device_id",
    "device_type",
    "event_id",
    "event_type",
    "ts",
    "name_label",
    "relative_humidity_percent",
    "temperature_fahrenheit"
]].copy()

raw_df.to_sql(
    "dt_humidity_raw",
    engine,
    if_exists="append",
    index=False,
    chunksize=5000,
    method="multi",
)

# ---------- NORMALIZE TO LONG FORMAT ----------
rh = df[[
    "ts", "event_id", "device_id", "name_label", "event_type", "sensor_number", "relative_humidity_percent"
]].copy()
rh["metric_name"] = "relative_humidity"
rh["quantity_kind"] = "http://qudt.org/vocab/quantitykind/RelativeHumidity"
rh["unit"] = "percent"
rh["value_double"] = rh["relative_humidity_percent"]
rh = rh.drop(columns=["relative_humidity_percent"])

temp = df[[
    "ts", "event_id", "device_id", "name_label", "event_type", "sensor_number", "temperature_fahrenheit"
]].copy()
temp["metric_name"] = "temperature"
temp["quantity_kind"] = "http://qudt.org/vocab/quantitykind/Temperature"
temp["unit"] = "fahrenheit"
temp["value_double"] = temp["temperature_fahrenheit"]
temp = temp.drop(columns=["temperature_fahrenheit"])

telemetry = pd.concat([rh, temp], ignore_index=True)

# ---------- JOIN TO GRAPH IDENTITIES ----------
telemetry = telemetry.merge(
    device_map[[
        "device_id", "sensor_number", "point_uri", "sensor_223p_uri", "canonical_uri", "ifc_guid"
    ]].drop_duplicates(),
    on=["device_id", "sensor_number"],
    how="left"
)

# ---------- FINAL COLUMN ORDER ----------
telemetry = telemetry[[
    "ts",
    "event_id",
    "device_id",
    "point_uri",
    "sensor_223p_uri",
    "canonical_uri",
    "ifc_guid",
    "metric_name",
    "quantity_kind",
    "value_double",
    "unit",
    "name_label",
    "event_type"
]]

telemetry.to_csv(Path("data/sensorReadings/telemetry_observations_preview.csv"), index=False)

# ---------- LOAD TO TIMESCALEDB ----------
telemetry.to_sql(
    "telemetry_observations",
    engine,
    if_exists="append",
    index=False,
    chunksize=5000,
    method="multi",
)

# ---------- OPTIONAL: SAVE MAP INTO DB ----------
device_map.to_sql(
    "dt_sensor_map",
    engine,
    if_exists="append",
    index=False,
    chunksize=1000,
    method="multi",
)

print("Loaded raw and normalized telemetry successfully.")
print(f"Raw rows: {len(raw_df)}")
print(f"Telemetry rows: {len(telemetry)}")
print(f"Mapped rows: {telemetry['canonical_uri'].notna().sum()} / {len(telemetry)}")