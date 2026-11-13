"""HTTP API that persists ESP32 readings in InfluxDB."""

from __future__ import annotations

import hmac
import os
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

app = FastAPI(title="Lâmpada Lab API", version="1.0.0")


class Reading(BaseModel):
    """One timestamped measurement packet received from an ESP32."""

    model_config = ConfigDict(extra="forbid")

    device_id: str = Field(default="lampada-01", min_length=1, max_length=64)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tank_level: float | None = None
    temperature: float | None = None
    humidity: float | None = Field(default=None, ge=0, le=100)
    luminosity: float | None = Field(default=None, ge=0)
    color: str | None = Field(default=None, max_length=32)
    button: bool | None = None

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_have_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone, preferably UTC")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def require_a_sensor_value(self) -> "Reading":
        values = self.model_dump(exclude={"device_id", "timestamp"}, exclude_none=True)
        if not values:
            raise ValueError("at least one sensor value is required")
        return self


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected = os.getenv("API_KEY", "")
    if not expected:
        raise HTTPException(status_code=503, detail="API_KEY is not configured")
    if x_api_key is None or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="invalid API key")


def influx_settings() -> tuple[str, str, str, str]:
    names = ("INFLUX_URL", "INFLUX_TOKEN", "INFLUX_ORG", "INFLUX_BUCKET")
    values = tuple(os.getenv(name, "").strip() for name in names)
    if not all(values):
        raise HTTPException(status_code=503, detail="InfluxDB settings are incomplete")
    return values  # type: ignore[return-value]


@contextmanager
def influx_client() -> Iterator[tuple[InfluxDBClient, str, str]]:
    url, token, org, bucket = influx_settings()
    client = InfluxDBClient(url=url, token=token, org=org)
    try:
        yield client, org, bucket
    finally:
        client.close()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/v1/readings", status_code=status.HTTP_201_CREATED)
def create_reading(
    reading: Reading, _: None = Depends(require_api_key)
) -> dict[str, Any]:
    with influx_client() as (client, org, bucket):
        point = Point("sensor_reading").tag("device_id", reading.device_id)
        for name, value in reading.model_dump(
            exclude={"device_id", "timestamp"}, exclude_none=True
        ).items():
            point.field(name, value)
        point.time(reading.timestamp, WritePrecision.S)
        try:
            client.write_api(write_options=SYNCHRONOUS).write(
                bucket=bucket, org=org, record=point
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail="could not persist reading") from exc

    return {"status": "stored", "device_id": reading.device_id, "timestamp": reading.timestamp}


@app.get("/api/v1/readings")
def list_readings(
    time_range: str = Query(default="-24h", alias="range"),
    device_id: str | None = Query(default=None, max_length=64),
    _: None = Depends(require_api_key),
) -> dict[str, Any]:
    if not re.fullmatch(r"-[1-9][0-9]*[smhdw]", time_range):
        raise HTTPException(status_code=422, detail="range must look like -24h, -7d, or -30m")

    url, token, org, bucket = influx_settings()
    filter_device = (
        f'|> filter(fn: (r) => r["device_id"] == "{device_id}")'
        if device_id and re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", device_id)
        else ""
    )
    if device_id and not filter_device:
        raise HTTPException(status_code=422, detail="device_id contains unsupported characters")

    flux = (
        f'from(bucket: "{bucket}")\n'
        f'  |> range(start: {time_range})\n'
        '  |> filter(fn: (r) => r["_measurement"] == "sensor_reading")\n'
        f"  {filter_device}\n"
        '  |> pivot(rowKey: ["_time", "device_id"], columnKey: ["_field"], valueColumn: "_value")\n'
        '  |> sort(columns: ["_time"], desc: true)\n'
        '  |> limit(n: 500)'
    )
    try:
        with InfluxDBClient(url=url, token=token, org=org) as client:
            tables = client.query_api().query(flux, org=org)
            items = [
                {
                    "device_id": record.values.get("device_id"),
                    "timestamp": record.get_time(),
                    **{
                        key: value
                        for key, value in record.values.items()
                        if key not in {"result", "table", "_start", "_stop", "_time", "_measurement", "device_id"}
                    },
                }
                for table in tables
                for record in table.records
            ]
    except Exception as exc:
        raise HTTPException(status_code=502, detail="could not query InfluxDB") from exc
    return {"count": len(items), "readings": items}
