from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
import os
import pickle
import random

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def resolve_model_path() -> Path:
    configured_path = Path(os.getenv("MODEL_PATH", "ml/model.pkl"))
    if configured_path.is_absolute():
        return configured_path
    return ROOT / configured_path


MODEL_PATH = resolve_model_path()
LSTM_MODEL_PATH = ROOT / "ml" / "lstm_model.keras"
DEFAULT_ORIGINS = ["http://localhost:8501", "http://127.0.0.1:8501", "http://localhost:5678"]


def resolve_allowed_origins() -> list[str]:
    configured = os.getenv("ALLOWED_ORIGINS", "")
    if not configured.strip():
        return DEFAULT_ORIGINS
    origins = [origin.strip() for origin in configured.split(",") if origin.strip()]
    return origins or DEFAULT_ORIGINS

app = FastAPI(title="Factory Copilot API", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=resolve_allowed_origins(),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SensorPayload(BaseModel):
    engine_id: int = Field(..., ge=1)
    s2: float
    s3: float
    s4: float
    s7: float
    s8: float
    s9: float
    s11: float
    s12: float
    s13: float
    s14: float
    s15: float
    s17: float
    s20: float
    s21: float


class FleetResponse(BaseModel):
    fleet_summary: dict[str, Any]
    machines: list[dict[str, Any]]


class VoiceStatusResponse(BaseModel):
    machine_id: int
    risk_level: str
    rul_hours: int
    failure_probability: float
    recommendation: str


class VoiceBriefingResponse(BaseModel):
    timestamp: str
    critical_machine_id: int | None
    fleet_health_percent: float
    critical_count: int
    warning_count: int
    briefing_text: str


class VoiceWorkOrderResponse(BaseModel):
    work_order_id: str
    machine_id: int
    priority: str
    issue: str
    failure_probability: str
    estimated_downtime_cost: str
    actions: list[str]
    created_at: str
    created_by: str


class VoiceMachineRequest(BaseModel):
    machine_id: int = Field(..., ge=1)


FEATURE_ORDER = ["s2", "s3", "s4", "s7", "s8", "s9", "s11", "s12", "s13", "s14", "s15", "s17", "s20", "s21"]


@lru_cache(maxsize=1)
def load_artifacts() -> dict[str, Any]:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Missing trained model at {MODEL_PATH}. Run ml/train_model.py after placing the CMAPSS data in data/."
        )

    with MODEL_PATH.open("rb") as handle:
        return pickle.load(handle)


def get_risk_level(rul: float, anomaly: int) -> str:
    if anomaly == -1 or rul < 30:
        return "critical"
    if rul < 80:
        return "warning"
    return "healthy"


def get_recommendation(risk: str, rul: float, anomaly: int) -> str:
    if risk == "critical":
        return "IMMEDIATE ACTION: Schedule maintenance within 24 hours. High failure probability detected."
    if risk == "warning":
        return "PLAN MAINTENANCE: Schedule inspection within 3 days. Monitor sensors closely."
    if anomaly == -1:
        return "Monitor closely. Anomaly detected, but remaining life is still acceptable."
    return "NORMAL OPERATION: Continue monitoring. Next scheduled check in 7 days."


def simulate_sensor_data(engine_id: int) -> dict[str, float]:
    base = {
        1: dict(s2=642, s3=1589, s4=1400, s7=554, s8=2388, s9=9065, s11=47, s12=521, s13=2388, s14=8138, s15=8.4195, s17=393, s20=39, s21=23),
        2: dict(s2=639, s3=1591, s4=1410, s7=551, s8=2390, s9=9050, s11=48, s12=518, s13=2384, s14=8125, s15=8.3612, s17=390, s20=38, s21=22),
        3: dict(s2=655, s3=1600, s4=1430, s7=560, s8=2400, s9=9100, s11=52, s12=530, s13=2400, s14=8200, s15=8.6000, s17=400, s20=42, s21=25),
        4: dict(s2=641, s3=1590, s4=1402, s7=553, s8=2389, s9=9060, s11=47, s12=520, s13=2385, s14=8130, s15=8.4000, s17=392, s20=39, s21=23),
        5: dict(s2=648, s3=1595, s4=1420, s7=556, s8=2393, s9=9075, s11=50, s12=524, s13=2392, s14=8155, s15=8.4800, s17=396, s20=40, s21=24),
        6: dict(s2=640, s3=1588, s4=1398, s7=552, s8=2387, s9=9055, s11=46, s12=519, s13=2382, s14=8120, s15=8.3900, s17=391, s20=38, s21=22),
    }
    rng = random.Random(engine_id)
    selected = base.get(engine_id, base[1])
    return {name: round(value + rng.uniform(-2, 2), 4) for name, value in selected.items()}


def predict_from_payload(payload: SensorPayload) -> dict[str, Any]:
    try:
        models = load_artifacts()
        xgb_model = models["xgb_model"]
        iso_forest = models["iso_forest"]
        scaler = models["scaler"]
        features = models["features"]

        sensor_frame = pd.DataFrame(
            [{feature: getattr(payload, feature) for feature in features}],
            columns=features,
        )
        scaled = scaler.transform(sensor_frame)
        rul = float(xgb_model.predict(scaled)[0])
        rul = max(0.0, round(rul, 1))
        anomaly = int(iso_forest.predict(scaled)[0])
    except (FileNotFoundError, OSError, pickle.UnpicklingError, EOFError, KeyError, TypeError, ValueError):
        sensor_values = np.array([getattr(payload, feature) for feature in FEATURE_ORDER], dtype=float)
        spread = float(np.ptp(sensor_values))
        normalized = (sensor_values - sensor_values.min()) / max(spread, 1.0)
        rul = round(float(max(0.0, 125.0 - normalized.mean() * 125.0)), 1)
        anomaly = -1 if normalized.std() > 0.22 else 1

    failure_probability = round(max(0.0, min(100.0, (1 - rul / 125.0) * 100.0 + (10 if anomaly == -1 else 0))), 1)
    risk = get_risk_level(rul, anomaly)
    health = round(max(0.0, min(100.0, (rul / 125.0) * 100.0)), 1)

    return {
        "engine_id": payload.engine_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rul_hours": round(rul * 2),
        "health_percent": health,
        "failure_probability": failure_probability,
        "anomaly_detected": anomaly == -1,
        "risk_level": risk,
        "sensors": payload.model_dump(exclude={"engine_id"}),
        "recommendation": get_recommendation(risk, rul, anomaly),
    }


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "Factory Copilot API running", "version": app.version}


@app.get("/health")
def health() -> dict[str, Any]:
    model_ready = MODEL_PATH.exists()
    return {
        "status": "ok",
        "model_ready": model_ready,
        "model_path": str(MODEL_PATH),
        "lstm_model_ready": LSTM_MODEL_PATH.exists(),
        "lstm_model_path": str(LSTM_MODEL_PATH),
        "model_stack": ["XGBoost", "Isolation Forest", "LSTM"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/predict/{engine_id}")
def predict_machine(engine_id: int) -> dict[str, Any]:
    if engine_id < 1:
        raise HTTPException(status_code=400, detail="engine_id must be positive")

    payload = SensorPayload(engine_id=engine_id, **simulate_sensor_data(engine_id))
    return predict_from_payload(payload)


@app.post("/predict")
def predict_from_request(payload: SensorPayload) -> dict[str, Any]:
    return predict_from_payload(payload)


@app.get("/fleet", response_model=FleetResponse)
def fleet_status() -> dict[str, Any]:
    machines = [predict_machine(engine_id) for engine_id in range(1, 7)]
    critical = sum(1 for machine in machines if machine["risk_level"] == "critical")
    warning = sum(1 for machine in machines if machine["risk_level"] == "warning")
    avg_health = round(sum(machine["health_percent"] for machine in machines) / len(machines), 1)

    return {
        "fleet_summary": {
            "total_machines": len(machines),
            "critical": critical,
            "warning": warning,
            "healthy": len(machines) - critical - warning,
            "avg_health": avg_health,
        },
        "machines": machines,
    }


@app.post("/workorder/{engine_id}")
def generate_work_order(engine_id: int) -> dict[str, Any]:
    data = predict_machine(engine_id)
    rul_hours = data["rul_hours"]
    return {
        "work_order_id": f"WO-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{engine_id:03d}",
        "machine_id": engine_id,
        "priority": data["risk_level"].upper(),
        "issue": f"Predicted failure within {rul_hours}h",
        "failure_probability": f"{data['failure_probability']}%",
        "estimated_downtime_cost": f"€{rul_hours * 87:.0f}",
        "actions": [
            "Inspect bearing assembly",
            "Check lubrication system",
            "Measure vibration levels",
            "Replace if wear exceeds tolerance",
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": "Factory Copilot AI Agent",
    }


@app.get("/voice/status/{machine_id}", response_model=VoiceStatusResponse)
def voice_machine_status(machine_id: int) -> dict[str, Any]:
    data = predict_machine(machine_id)
    return {
        "machine_id": machine_id,
        "risk_level": data["risk_level"],
        "rul_hours": data["rul_hours"],
        "failure_probability": data["failure_probability"],
        "recommendation": data["recommendation"],
    }


@app.get("/voice/briefing", response_model=VoiceBriefingResponse)
def voice_briefing() -> dict[str, Any]:
    fleet = fleet_status()
    machines = fleet["machines"]
    summary = fleet["fleet_summary"]

    critical_machines = [machine for machine in machines if machine["risk_level"] == "critical"]
    warning_machines = [machine for machine in machines if machine["risk_level"] == "warning"]
    top_machine = min(machines, key=lambda machine: machine["rul_hours"]) if machines else None

    if top_machine:
        briefing_text = (
            f"Fleet health is {summary['avg_health']} percent. "
            f"Most critical is machine {top_machine['engine_id']} with RUL {top_machine['rul_hours']} hours "
            f"and failure probability {top_machine['failure_probability']} percent. "
            f"Recommendation: {top_machine['recommendation']}"
        )
    else:
        briefing_text = "No machine data is currently available."

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "critical_machine_id": top_machine["engine_id"] if top_machine else None,
        "fleet_health_percent": summary["avg_health"],
        "critical_count": len(critical_machines),
        "warning_count": len(warning_machines),
        "briefing_text": briefing_text,
    }


@app.post("/voice/workorder/{machine_id}", response_model=VoiceWorkOrderResponse)
def voice_create_work_order(machine_id: int) -> dict[str, Any]:
    return generate_work_order(machine_id)


@app.post("/voice/tools/get_machine_status")
def voice_tool_get_machine_status(payload: VoiceMachineRequest) -> dict[str, Any]:
    data = voice_machine_status(payload.machine_id)
    return {
        "status": "success",
        **data,
        "result_text": (
            f"Machine {data['machine_id']} is {data['risk_level']} with failure probability "
            f"{data['failure_probability']} percent and RUL {data['rul_hours']} hours. "
            f"Recommendation: {data['recommendation']}"
        ),
    }


@app.post("/voice/tools/get_fleet_briefing")
def voice_tool_get_fleet_briefing() -> dict[str, Any]:
    data = voice_briefing()
    return {
        "status": "success",
        **data,
        "result_text": data["briefing_text"],
    }


@app.post("/voice/tools/create_work_order")
def voice_tool_create_work_order(payload: VoiceMachineRequest) -> dict[str, Any]:
    data = voice_create_work_order(payload.machine_id)
    return {
        "status": "success",
        **data,
        "result_text": (
            f"Work order {data['work_order_id']} created for machine {data['machine_id']} "
            f"with priority {data['priority']} and issue '{data['issue']}'."
        ),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
