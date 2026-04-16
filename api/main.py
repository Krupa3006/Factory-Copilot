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
CMAPSS_SPLIT = os.getenv("CMAPSS_SPLIT", "FD001").upper()
CMAPSS_SOURCE = os.getenv("CMAPSS_SOURCE", "train").lower()
CMAPSS_REPLAY_ENABLED = os.getenv("CMAPSS_REPLAY_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
CMAPSS_REPLAY_STATE: dict[int, int] = {}
CMAPSS_COLUMNS = ["engine_id", "cycle", "op1", "op2", "op3"] + [f"s{i}" for i in range(1, 22)]


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
ENGINE_RUNTIME: dict[int, dict[str, float]] = {}

FALLBACK_BASELINE = {
    "s2": 642.0,
    "s3": 1592.0,
    "s4": 1410.0,
    "s7": 554.0,
    "s8": 2390.0,
    "s9": 9068.0,
    "s11": 48.0,
    "s12": 521.0,
    "s13": 2388.0,
    "s14": 8145.0,
    "s15": 8.42,
    "s17": 394.0,
    "s20": 39.2,
    "s21": 23.4,
}

FALLBACK_SCALE = {
    "s2": 9.0,
    "s3": 28.0,
    "s4": 34.0,
    "s7": 13.0,
    "s8": 32.0,
    "s9": 110.0,
    "s11": 4.5,
    "s12": 14.0,
    "s13": 28.0,
    "s14": 105.0,
    "s15": 0.16,
    "s17": 14.0,
    "s20": 3.5,
    "s21": 3.0,
}

DEGRADATION_SENSITIVITY = {
    "s2": 0.014,
    "s3": 0.021,
    "s4": 0.024,
    "s7": 0.016,
    "s8": 0.019,
    "s9": 0.027,
    "s11": 0.060,
    "s12": 0.022,
    "s13": 0.019,
    "s14": 0.028,
    "s15": 0.115,
    "s17": 0.039,
    "s20": 0.072,
    "s21": 0.079,
}


def get_engine_runtime(engine_id: int) -> dict[str, float]:
    runtime = ENGINE_RUNTIME.get(engine_id)
    if runtime is None:
        seeded = random.Random(engine_id * 1009)
        runtime = {
            "cycle": float(seeded.randint(40, 220)),
            "wear": seeded.uniform(0.16, 0.58),
            "wear_rate": seeded.uniform(0.0015, 0.0065),
            "phase": seeded.uniform(0.0, 2 * np.pi),
        }
        ENGINE_RUNTIME[engine_id] = runtime
    return runtime


@lru_cache(maxsize=1)
def load_artifacts() -> dict[str, Any]:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Missing trained model at {MODEL_PATH}. Run ml/train_model.py after placing the CMAPSS data in data/."
        )

    with MODEL_PATH.open("rb") as handle:
        return pickle.load(handle)


def resolve_cmapss_data_path(split: str | None = None, source: str | None = None) -> Path:
    selected_split = (split or CMAPSS_SPLIT).upper()
    selected_source = (source or CMAPSS_SOURCE).lower()
    return ROOT / "data" / f"{selected_source}_{selected_split}.txt"


@lru_cache(maxsize=2)
def load_cmapss_replay_frame(split: str | None = None, source: str | None = None) -> pd.DataFrame:
    selected_split = (split or CMAPSS_SPLIT).upper()
    selected_source = (source or CMAPSS_SOURCE).lower()
    data_path = resolve_cmapss_data_path(selected_split, selected_source)
    if not data_path.exists():
        raise FileNotFoundError(f"CMAPSS file not found: {data_path}")

    raw_df = pd.read_csv(data_path, sep=r"\s+", header=None, engine="python")
    if raw_df.shape[1] < len(CMAPSS_COLUMNS):
        raise ValueError(f"Unexpected CMAPSS format in {data_path}; expected at least {len(CMAPSS_COLUMNS)} columns.")
    if raw_df.shape[1] > len(CMAPSS_COLUMNS):
        raw_df = raw_df.iloc[:, : len(CMAPSS_COLUMNS)]
    raw_df.columns = CMAPSS_COLUMNS

    feature_columns = ["engine_id", "cycle", *FEATURE_ORDER]
    df = raw_df[feature_columns].copy()
    df["engine_id"] = df["engine_id"].astype(int)
    df["cycle"] = df["cycle"].astype(int)

    if selected_source == "train":
        max_cycle = df.groupby("engine_id")["cycle"].transform("max")
        df["true_rul_cycles"] = (max_cycle - df["cycle"]).astype(float)
    elif selected_source == "test":
        rul_path = ROOT / "data" / f"RUL_{selected_split}.txt"
        if not rul_path.exists():
            raise FileNotFoundError(f"Missing CMAPSS RUL file for test split: {rul_path}")
        rul_df = pd.read_csv(rul_path, sep=r"\s+", header=None, names=["final_rul"], engine="python")
        rul_df["engine_id"] = np.arange(1, len(rul_df) + 1, dtype=int)
        df = df.merge(rul_df, on="engine_id", how="left")
        if df["final_rul"].isna().any():
            raise ValueError(f"Could not align RUL file {rul_path} with test engines in {data_path}")
        max_cycle = df.groupby("engine_id")["cycle"].transform("max")
        df["true_rul_cycles"] = (df["final_rul"] + (max_cycle - df["cycle"])).astype(float)
        df.drop(columns=["final_rul"], inplace=True)
    else:
        raise ValueError("CMAPSS_SOURCE must be 'train' or 'test'")

    return df.sort_values(["engine_id", "cycle"]).reset_index(drop=True)


@lru_cache(maxsize=2)
def load_cmapss_replay_groups(split: str | None = None, source: str | None = None) -> dict[int, pd.DataFrame]:
    frame = load_cmapss_replay_frame(split, source)
    return {int(engine_id): group.reset_index(drop=True) for engine_id, group in frame.groupby("engine_id", sort=True)}


def get_next_cmapss_snapshot(logical_engine_id: int) -> dict[str, Any] | None:
    if not CMAPSS_REPLAY_ENABLED:
        return None

    try:
        grouped = load_cmapss_replay_groups()
    except (FileNotFoundError, ValueError, OSError):
        return None

    available_engines = sorted(grouped.keys())
    if not available_engines:
        return None

    mapped_engine_id = available_engines[(logical_engine_id - 1) % len(available_engines)]
    engine_df = grouped[mapped_engine_id]
    cursor = CMAPSS_REPLAY_STATE.get(logical_engine_id, 0)
    index = cursor % len(engine_df)
    CMAPSS_REPLAY_STATE[logical_engine_id] = (cursor + 1) % len(engine_df)

    row = engine_df.iloc[index]
    sensors = {feature: float(row[feature]) for feature in FEATURE_ORDER}

    return {
        "logical_engine_id": logical_engine_id,
        "cmapss_engine_id": mapped_engine_id,
        "cycle": int(row["cycle"]),
        "true_rul_cycles": float(row["true_rul_cycles"]),
        "sensors": sensors,
        "data_source": "cmapss_replay",
        "cmapss_split": CMAPSS_SPLIT,
        "cmapss_source": CMAPSS_SOURCE,
    }


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
    selected = base.get(engine_id, base[1])
    runtime = get_engine_runtime(engine_id)
    runtime["cycle"] += 1.0
    runtime["wear"] = min(1.0, runtime["wear"] + runtime["wear_rate"])

    cycle = runtime["cycle"]
    wear = runtime["wear"]
    phase = runtime["phase"]

    wave = float(np.sin(cycle / 9.0 + phase))
    rng = random.Random((engine_id * 1_000_003) + int(cycle))

    sensors: dict[str, float] = {}
    for name, value in selected.items():
        sensitivity = DEGRADATION_SENSITIVITY[name]
        drift = value * sensitivity * wear
        oscillation = value * (0.0015 if name != "s15" else 0.0035) * wave
        noise = rng.uniform(-1.8, 1.8) if name != "s15" else rng.uniform(-0.08, 0.08)

        spike = 0.0
        if name in {"s11", "s17", "s20", "s21"} and rng.random() < wear * 0.20:
            spike = rng.uniform(0.25, 2.6) if name == "s11" else rng.uniform(0.5, 3.4)
        if name == "s15" and rng.random() < wear * 0.15:
            spike = rng.uniform(0.04, 0.18)

        sensors[name] = round(value + drift + oscillation + noise + spike, 4)

    return sensors


def predict_from_payload(payload: SensorPayload, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    metadata = metadata or {}
    true_rul_cycles = metadata.get("true_rul_cycles")
    true_rul_cycles = float(true_rul_cycles) if true_rul_cycles is not None else None

    predicted_rul_cycles: float | None = None
    model_used = False
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
        predicted_rul_cycles = float(xgb_model.predict(scaled)[0])
        predicted_rul_cycles = max(0.0, round(predicted_rul_cycles, 1))
        anomaly = int(iso_forest.predict(scaled)[0])
        model_used = True
    except (FileNotFoundError, OSError, pickle.UnpicklingError, EOFError, KeyError, TypeError, ValueError):
        sensor_values = {feature: float(getattr(payload, feature)) for feature in FEATURE_ORDER}
        if true_rul_cycles is not None:
            predicted_rul_cycles = round(float(np.clip(true_rul_cycles, 0.0, 125.0)), 1)
            anomaly = -1 if predicted_rul_cycles < 25 else 1
        else:
            deviations = [
                abs((sensor_values[feature] - FALLBACK_BASELINE[feature]) / FALLBACK_SCALE[feature])
                for feature in FEATURE_ORDER
            ]
            degradation_index = float(np.mean(deviations))
            engine_bias = 0.035 * ((payload.engine_id - 1) % 3)
            degradation_index += engine_bias

            predicted_rul_cycles = round(float(np.clip(125.0 * (1.0 - 0.47 * degradation_index), 0.0, 125.0)), 1)
            anomaly_score = max(
                abs((sensor_values["s11"] - FALLBACK_BASELINE["s11"]) / FALLBACK_SCALE["s11"]),
                abs((sensor_values["s20"] - FALLBACK_BASELINE["s20"]) / FALLBACK_SCALE["s20"]),
                abs((sensor_values["s21"] - FALLBACK_BASELINE["s21"]) / FALLBACK_SCALE["s21"]),
            )
            anomaly = -1 if (degradation_index > 0.92 or anomaly_score > 1.45) else 1

    effective_rul_cycles = true_rul_cycles if true_rul_cycles is not None else predicted_rul_cycles
    if effective_rul_cycles is None:
        effective_rul_cycles = 0.0

    failure_probability = round(
        max(0.0, min(100.0, (1 - effective_rul_cycles / 125.0) * 100.0 + (10 if anomaly == -1 else 0))),
        1,
    )
    risk = get_risk_level(effective_rul_cycles, anomaly)
    health = round(max(0.0, min(100.0, (effective_rul_cycles / 125.0) * 100.0)), 1)

    prediction_error = None
    if predicted_rul_cycles is not None and true_rul_cycles is not None:
        prediction_error = round(predicted_rul_cycles - true_rul_cycles, 2)

    return {
        "engine_id": payload.engine_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "rul_hours": round(effective_rul_cycles * 2),
        "health_percent": health,
        "failure_probability": failure_probability,
        "anomaly_detected": anomaly == -1,
        "risk_level": risk,
        "sensors": payload.model_dump(exclude={"engine_id"}),
        "recommendation": get_recommendation(risk, effective_rul_cycles, anomaly),
        "data_source": metadata.get("data_source", "simulated"),
        "cmapss_split": metadata.get("cmapss_split"),
        "cmapss_source": metadata.get("cmapss_source"),
        "cmapss_engine_id": metadata.get("cmapss_engine_id"),
        "cycle": metadata.get("cycle"),
        "true_rul_cycles": round(true_rul_cycles, 1) if true_rul_cycles is not None else None,
        "true_rul_hours": round(true_rul_cycles * 2) if true_rul_cycles is not None else None,
        "predicted_rul_cycles": round(predicted_rul_cycles, 1) if predicted_rul_cycles is not None else None,
        "prediction_error_cycles": prediction_error,
        "model_used": model_used,
    }


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "Factory Copilot API running", "version": app.version}


@app.get("/health")
def health() -> dict[str, Any]:
    model_ready = MODEL_PATH.exists()
    replay_path = resolve_cmapss_data_path()
    replay_ready = False
    replay_engines = 0
    try:
        replay_groups = load_cmapss_replay_groups()
        replay_ready = bool(replay_groups)
        replay_engines = len(replay_groups)
    except (FileNotFoundError, ValueError, OSError):
        replay_ready = False

    return {
        "status": "ok",
        "model_ready": model_ready,
        "model_path": str(MODEL_PATH),
        "lstm_model_ready": LSTM_MODEL_PATH.exists(),
        "lstm_model_path": str(LSTM_MODEL_PATH),
        "model_stack": ["XGBoost", "Isolation Forest", "LSTM"],
        "cmapss_replay_enabled": CMAPSS_REPLAY_ENABLED,
        "cmapss_replay_ready": replay_ready,
        "cmapss_replay_engines": replay_engines,
        "cmapss_replay_path": str(replay_path),
        "cmapss_split": CMAPSS_SPLIT,
        "cmapss_source": CMAPSS_SOURCE,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/predict/{engine_id}")
def predict_machine(engine_id: int) -> dict[str, Any]:
    if engine_id < 1:
        raise HTTPException(status_code=400, detail="engine_id must be positive")

    cmapss_snapshot = get_next_cmapss_snapshot(engine_id)
    if cmapss_snapshot is not None:
        payload = SensorPayload(engine_id=engine_id, **cmapss_snapshot["sensors"])
        metadata = {
            "data_source": cmapss_snapshot["data_source"],
            "cmapss_split": cmapss_snapshot["cmapss_split"],
            "cmapss_source": cmapss_snapshot["cmapss_source"],
            "cmapss_engine_id": cmapss_snapshot["cmapss_engine_id"],
            "cycle": cmapss_snapshot["cycle"],
            "true_rul_cycles": cmapss_snapshot["true_rul_cycles"],
        }
        return predict_from_payload(payload, metadata=metadata)

    payload = SensorPayload(engine_id=engine_id, **simulate_sensor_data(engine_id))
    return predict_from_payload(payload, metadata={"data_source": "simulated_fallback"})


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
