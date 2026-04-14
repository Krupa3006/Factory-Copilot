from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import pickle
from typing import Any, Sequence

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import MinMaxScaler
from xgboost import XGBRegressor

try:
    import tensorflow as tf
    from tensorflow import keras
    from tensorflow.keras import callbacks, layers

    TENSORFLOW_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency in local setups
    tf = None
    keras = None
    callbacks = None
    layers = None
    TENSORFLOW_AVAILABLE = False

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
MODEL_PATH = Path(__file__).resolve().with_name("model.pkl")
LSTM_MODEL_PATH = Path(__file__).resolve().with_name("lstm_model.keras")
METRICS_PATH = Path(__file__).resolve().with_name("model_metrics.json")
SEQUENCE_LENGTH = 20

FEATURES: list[str] = ["s2", "s3", "s4", "s7", "s8", "s9", "s11", "s12", "s13", "s14", "s15", "s17", "s20", "s21"]
COLUMNS: list[str] = ["engine_id", "cycle", "op1", "op2", "op3", *[f"s{i}" for i in range(1, 22)]]


def generate_synthetic_cmapss(n_engines: int = 60, max_cycle: int = 280) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    rows: list[list[float]] = []
    for engine_id in range(1, n_engines + 1):
        life = int(rng.integers(180, max_cycle + 1))
        for cycle in range(1, life + 1):
            degradation = cycle / life
            op1 = float(rng.normal(0, 1))
            op2 = float(rng.normal(0, 1))
            op3 = float(rng.normal(0, 1))
            sensors = []
            for sensor_index in range(1, 22):
                baseline = 500 + sensor_index * 30
                trend = (sensor_index % 5 + 1) * degradation * 12
                noise = rng.normal(0, 1.5)
                sensors.append(float(baseline + trend + noise))
            rows.append([float(engine_id), float(cycle), op1, op2, op3, *sensors])
    return pd.DataFrame(rows, columns=COLUMNS)


def load_single_dataset(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=r"\s+", header=None, names=COLUMNS, engine="python")
    df = df.dropna(axis=1, how="all")
    return df


def load_training_data(data_dir: Path) -> tuple[pd.DataFrame, list[str]]:
    train_files = sorted(data_dir.glob("train_FD*.txt"))
    if not train_files:
        print(f"No CMAPSS train_FD*.txt files found in {data_dir}. Using deterministic synthetic dataset for demo training.")
        return generate_synthetic_cmapss(), ["synthetic"]

    frames: list[pd.DataFrame] = []
    loaded_names: list[str] = []
    engine_offset = 0

    for train_file in train_files:
        frame = load_single_dataset(train_file)
        frame["engine_id"] = frame["engine_id"].astype(int) + engine_offset
        frame["dataset"] = train_file.stem.replace("train_", "")

        engine_offset = int(frame["engine_id"].max())
        loaded_names.append(train_file.name)
        frames.append(frame)

    combined = pd.concat(frames, axis=0, ignore_index=True)
    return combined, loaded_names


def build_training_frame(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()
    max_cycles = frame.groupby("engine_id", as_index=False)["cycle"].max().rename(columns={"cycle": "max_cycle"})
    frame = frame.merge(max_cycles, on="engine_id", how="left")
    frame["RUL"] = (frame["max_cycle"] - frame["cycle"]).clip(lower=0, upper=125)
    return frame


@dataclass(slots=True)
class TrainingArtifacts:
    xgb_model: XGBRegressor
    iso_forest: IsolationForest
    scaler: MinMaxScaler
    features: Sequence[str]


def train_models(frame: pd.DataFrame) -> tuple[TrainingArtifacts, dict[str, float]]:
    X = frame[list(FEATURES)]
    y = frame["RUL"]
    groups = frame["engine_id"]

    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(splitter.split(X, y, groups))

    scaler = MinMaxScaler()
    X_train = scaler.fit_transform(X.iloc[train_idx])
    X_test = scaler.transform(X.iloc[test_idx])
    y_train = y.iloc[train_idx]
    y_test = y.iloc[test_idx]

    xgb_model = XGBRegressor(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="reg:squarederror",
        random_state=42,
    )
    xgb_model.fit(X_train, y_train)

    predictions = xgb_model.predict(X_test)
    metrics = {
        "r2_score": float(r2_score(y_test, predictions)),
        "mae": float(mean_absolute_error(y_test, predictions)),
        "num_rows": int(len(frame)),
        "num_engines": int(frame["engine_id"].nunique()),
    }

    iso_forest = IsolationForest(contamination=0.05, random_state=42)
    iso_forest.fit(scaler.transform(X))

    artifacts = TrainingArtifacts(
        xgb_model=xgb_model,
        iso_forest=iso_forest,
        scaler=scaler,
        features=FEATURES,
    )
    return artifacts, metrics


def build_lstm_sequences(
    frame: pd.DataFrame,
    scaler: MinMaxScaler,
    sequence_length: int = SEQUENCE_LENGTH,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    ordered = frame.sort_values(["engine_id", "cycle"]).reset_index(drop=True)
    scaled_features = scaler.transform(ordered[list(FEATURES)])

    sequences: list[np.ndarray] = []
    labels: list[float] = []
    groups: list[int] = []

    start = 0
    engine_ids = ordered["engine_id"].to_numpy(dtype=int)
    rul_values = ordered["RUL"].to_numpy(dtype=np.float32)

    while start < len(ordered):
        engine_id = engine_ids[start]
        end = start
        while end < len(ordered) and engine_ids[end] == engine_id:
            end += 1

        engine_slice = scaled_features[start:end]
        engine_rul = rul_values[start:end]

        for index in range(sequence_length - 1, len(engine_slice)):
            window_start = index - sequence_length + 1
            sequences.append(engine_slice[window_start : index + 1])
            labels.append(float(engine_rul[index]))
            groups.append(int(engine_id))

        start = end

    return (
        np.asarray(sequences, dtype=np.float32),
        np.asarray(labels, dtype=np.float32),
        np.asarray(groups, dtype=np.int32),
    )


def train_lstm_model(frame: pd.DataFrame, scaler: MinMaxScaler) -> dict[str, Any]:
    if not TENSORFLOW_AVAILABLE:
        return {
            "status": "skipped",
            "reason": "tensorflow is not installed; XGBoost and Isolation Forest artifacts were still generated.",
        }

    if tf is not None:
        tf.random.set_seed(42)

    X_sequences, y_sequences, groups = build_lstm_sequences(frame, scaler)
    if len(X_sequences) == 0:
        return {
            "status": "skipped",
            "reason": "Not enough sequential data to create LSTM windows.",
        }

    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_idx, test_idx = next(splitter.split(X_sequences, y_sequences, groups))

    X_train = X_sequences[train_idx]
    X_test = X_sequences[test_idx]
    y_train = y_sequences[train_idx]
    y_test = y_sequences[test_idx]

    model = keras.Sequential(
        [
            layers.Input(shape=(SEQUENCE_LENGTH, len(FEATURES))),
            layers.LSTM(48),
            layers.Dense(24, activation="relu"),
            layers.Dense(1),
        ]
    )
    model.compile(optimizer="adam", loss="mse", metrics=["mae"])
    early_stopping = callbacks.EarlyStopping(monitor="val_loss", patience=2, restore_best_weights=True)
    model.fit(
        X_train,
        y_train,
        validation_split=0.2,
        epochs=8,
        batch_size=64,
        callbacks=[early_stopping],
        verbose=0,
    )

    predictions = model.predict(X_test, verbose=0).reshape(-1)
    model.save(LSTM_MODEL_PATH)

    return {
        "status": "trained",
        "path": str(LSTM_MODEL_PATH),
        "sequence_length": SEQUENCE_LENGTH,
        "r2_score": float(r2_score(y_test, predictions)),
        "mae": float(mean_absolute_error(y_test, predictions)),
        "num_sequences": int(len(X_sequences)),
    }


def build_test_truth(test_frame: pd.DataFrame, rul_file: Path) -> pd.DataFrame:
    rul_values = pd.read_csv(rul_file, sep=r"\s+", header=None, engine="python").dropna(axis=1, how="all")
    rul_values.columns = ["final_rul"]
    rul_values["engine_id"] = np.arange(1, len(rul_values) + 1)

    frame = test_frame.copy()
    max_cycles = frame.groupby("engine_id", as_index=False)["cycle"].max().rename(columns={"cycle": "max_cycle"})
    frame = frame.merge(max_cycles, on="engine_id", how="left")
    frame = frame.merge(rul_values, on="engine_id", how="left")
    frame["RUL"] = (frame["final_rul"] + frame["max_cycle"] - frame["cycle"]).clip(lower=0, upper=125)
    return frame


def evaluate_on_cmapss_tests(artifacts: TrainingArtifacts, data_dir: Path) -> dict[str, Any]:
    results: dict[str, Any] = {}
    test_files = sorted(data_dir.glob("test_FD*.txt"))

    for test_file in test_files:
        suffix = test_file.stem.replace("test_", "")
        rul_file = data_dir / f"RUL_{suffix}.txt"
        if not rul_file.exists():
            continue

        test_raw = load_single_dataset(test_file)
        test_frame = build_test_truth(test_raw, rul_file)

        X_test = test_frame[list(artifacts.features)]
        y_true = test_frame["RUL"].to_numpy(dtype=float)
        y_pred = artifacts.xgb_model.predict(artifacts.scaler.transform(X_test))

        results[suffix] = {
            "r2_score": float(r2_score(y_true, y_pred)),
            "mae": float(mean_absolute_error(y_true, y_pred)),
            "rows": int(len(test_frame)),
            "engines": int(test_frame["engine_id"].nunique()),
        }

    if results:
        aggregate_mae = float(np.mean([result["mae"] for result in results.values()]))
        results["aggregate"] = {
            "mean_mae": aggregate_mae,
            "datasets": len(results),
        }
    return results


def save_artifacts(artifacts: TrainingArtifacts, metrics: dict[str, float]) -> None:
    with MODEL_PATH.open("wb") as handle:
        pickle.dump(
            {
                "xgb_model": artifacts.xgb_model,
                "iso_forest": artifacts.iso_forest,
                "scaler": artifacts.scaler,
                "features": list(artifacts.features),
            },
            handle,
        )

    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")


def main() -> None:
    df, loaded_names = load_training_data(DATA_DIR)
    frame = build_training_frame(df)
    artifacts, metrics = train_models(frame)
    lstm_metrics = train_lstm_model(frame, artifacts.scaler)
    test_metrics = evaluate_on_cmapss_tests(artifacts, DATA_DIR)
    metrics["datasets"] = loaded_names
    metrics["model_stack"] = ["XGBoost", "Isolation Forest", "LSTM"]
    metrics["lstm"] = lstm_metrics
    if test_metrics:
        metrics["test_evaluation"] = test_metrics
    save_artifacts(artifacts, metrics)
    print(f"Loaded datasets: {', '.join(loaded_names)}")
    print(f"Saved model artifacts to {MODEL_PATH}")
    print(f"Metrics: R2={metrics['r2_score']:.3f}, MAE={metrics['mae']:.3f}")
    if lstm_metrics["status"] == "trained":
        print(
            f"LSTM saved to {lstm_metrics['path']} "
            f"(R2={lstm_metrics['r2_score']:.3f}, MAE={lstm_metrics['mae']:.3f})"
        )
    else:
        print(f"LSTM status: {lstm_metrics['status']} - {lstm_metrics['reason']}")
    if test_metrics:
        for dataset_name, dataset_metrics in test_metrics.items():
            if dataset_name == "aggregate":
                print(
                    f"Test aggregate: mean MAE={dataset_metrics['mean_mae']:.3f} over {dataset_metrics['datasets']} datasets"
                )
                continue
            print(
                f"Test {dataset_name}: R2={dataset_metrics['r2_score']:.3f}, "
                f"MAE={dataset_metrics['mae']:.3f}"
            )


if __name__ == "__main__":
    main()
