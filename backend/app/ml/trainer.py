"""
ML threat classifier trainer for CyberSentinel AI.

Trains a RandomForest classifier on cybersecurity incident data.
Features: protocol_encoded, source_port, dest_port, packet_length,
          flow_duration, packet_rate
Target: attack_type (multi-class classification)

Saves model, label encoder, and feature names to ML_MODEL_PATH.
"""

from __future__ import annotations

import os
import random
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from loguru import logger
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

from backend.app.core.config import settings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FEATURE_COLUMNS: List[str] = [
    "source_port",
    "dest_port",
    "protocol_encoded",
    "packet_length",
    "flow_duration",
    "packet_rate",
]

TARGET_COLUMN = "attack_type"

ATTACK_TYPES = [
    "Brute Force",
    "DDoS",
    "Phishing",
    "Malware",
    "Port Scan",
    "SQL Injection",
    "XSS",
    "Benign",
]

SEVERITY_MAP = {
    "Brute Force": "high",
    "DDoS": "critical",
    "Phishing": "medium",
    "Malware": "critical",
    "Port Scan": "low",
    "SQL Injection": "high",
    "XSS": "medium",
    "Benign": "low",
}

PROTOCOL_MAP = {
    "TCP": 0,
    "UDP": 1,
    "ICMP": 2,
    "HTTP": 3,
    "HTTPS": 4,
    "DNS": 5,
    "SSH": 6,
    "FTP": 7,
}

# Port distributions per attack type for realistic synthesis
_ATTACK_PORT_PROFILES: Dict[str, Dict[str, Any]] = {
    "Brute Force": {
        "dest_ports": [22, 3389, 21, 23, 3306],
        "protocols": ["TCP"],
        "packet_length_range": (40, 300),
        "flow_duration_range": (100, 5000),
        "packet_rate_range": (5, 100),
    },
    "DDoS": {
        "dest_ports": [80, 443, 53],
        "protocols": ["UDP", "TCP", "ICMP"],
        "packet_length_range": (64, 1500),
        "flow_duration_range": (1, 60),
        "packet_rate_range": (500, 10000),
    },
    "Phishing": {
        "dest_ports": [25, 465, 587, 80, 443],
        "protocols": ["TCP", "HTTP", "HTTPS"],
        "packet_length_range": (200, 2000),
        "flow_duration_range": (500, 3000),
        "packet_rate_range": (1, 20),
    },
    "Malware": {
        "dest_ports": [443, 80, 4444, 8080],
        "protocols": ["TCP", "HTTPS"],
        "packet_length_range": (100, 1500),
        "flow_duration_range": (200, 10000),
        "packet_rate_range": (2, 50),
    },
    "Port Scan": {
        "dest_ports": [22, 80, 443, 3306, 5432, 8080, 8443, 21],
        "protocols": ["TCP"],
        "packet_length_range": (40, 100),
        "flow_duration_range": (1, 50),
        "packet_rate_range": (50, 500),
    },
    "SQL Injection": {
        "dest_ports": [80, 443, 3306, 5432, 1433],
        "protocols": ["TCP", "HTTP", "HTTPS"],
        "packet_length_range": (300, 3000),
        "flow_duration_range": (100, 2000),
        "packet_rate_range": (1, 30),
    },
    "XSS": {
        "dest_ports": [80, 443, 8080],
        "protocols": ["TCP", "HTTP", "HTTPS"],
        "packet_length_range": (200, 2500),
        "flow_duration_range": (100, 1500),
        "packet_rate_range": (1, 25),
    },
    "Benign": {
        "dest_ports": [80, 443, 22, 53, 25],
        "protocols": ["TCP", "UDP", "HTTP", "HTTPS", "DNS"],
        "packet_length_range": (64, 1400),
        "flow_duration_range": (10, 5000),
        "packet_rate_range": (1, 100),
    },
}


# ---------------------------------------------------------------------------
# Dataset loading / generation
# ---------------------------------------------------------------------------


def load_or_generate_dataset(csv_path: str | None = None) -> pd.DataFrame:
    """Load a CSV dataset if it exists, otherwise generate 1000 synthetic samples.

    Parameters
    ----------
    csv_path:
        Optional path to an existing CSV file.  If ``None`` the function
        checks ``data/sample/sample_incidents.csv`` relative to the project root.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns: source_port, dest_port, protocol_encoded,
        packet_length, flow_duration, packet_rate, attack_type, severity.
    """
    # Try the supplied path first, then the default sample location
    candidates: List[str] = []
    if csv_path:
        candidates.append(csv_path)
    # Default sample path
    candidates.append(
        str(
            Path(__file__).resolve().parents[4]
            / "data"
            / "sample"
            / "sample_incidents.csv"
        )
    )

    for path in candidates:
        if Path(path).exists():
            logger.info("Loading existing dataset from CSV", path=path)
            df = pd.read_csv(path)
            df = _preprocess_raw_csv(df)
            logger.info("Dataset loaded", rows=len(df), columns=list(df.columns))
            return df

    logger.info("No CSV found — generating 1000 synthetic samples")
    return _generate_synthetic_dataset(n_samples=1000)


def _preprocess_raw_csv(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise a raw incident CSV into the feature-ready format."""
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    # Rename destination columns if needed
    rename_map = {
        "destination_ip": "dest_ip",
        "destination_port": "dest_port",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Encode protocol
    if "protocol" in df.columns:
        df["protocol_encoded"] = (
            df["protocol"]
            .str.upper()
            .map(PROTOCOL_MAP)
            .fillna(0)
            .astype(int)
        )

    # Ensure numeric columns
    for col in ["source_port", "dest_port", "packet_length", "flow_duration", "packet_rate"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Ensure attack_type and severity exist
    if "attack_type" not in df.columns:
        df["attack_type"] = "Benign"
    if "severity" not in df.columns:
        df["severity"] = df["attack_type"].map(SEVERITY_MAP).fillna("low")

    # Keep only required columns that exist
    required = FEATURE_COLUMNS + ["attack_type", "severity"]
    available = [c for c in required if c in df.columns]
    return df[available].dropna(subset=["attack_type"])


def _generate_synthetic_dataset(n_samples: int = 1000) -> pd.DataFrame:
    """Generate a synthetic labelled cybersecurity dataset."""
    random.seed(42)
    np.random.seed(42)

    rows = []
    attack_types_cycle = ATTACK_TYPES * (n_samples // len(ATTACK_TYPES) + 1)
    random.shuffle(attack_types_cycle)

    for i in range(n_samples):
        attack_type = attack_types_cycle[i]
        profile = _ATTACK_PORT_PROFILES[attack_type]

        dest_port = random.choice(profile["dest_ports"])
        protocol = random.choice(profile["protocols"])
        protocol_encoded = PROTOCOL_MAP.get(protocol, 0)

        # Source port: privileged (<1024) for services, ephemeral for clients
        source_port = random.choice(
            [random.randint(1024, 65535), random.randint(1, 1023)]
            if random.random() < 0.1
            else [random.randint(1024, 65535)]
        )

        pkt_min, pkt_max = profile["packet_length_range"]
        packet_length = int(np.random.uniform(pkt_min, pkt_max))

        flow_min, flow_max = profile["flow_duration_range"]
        flow_duration = float(np.random.uniform(flow_min, flow_max))

        rate_min, rate_max = profile["packet_rate_range"]
        packet_rate = float(np.random.uniform(rate_min, rate_max))

        severity = SEVERITY_MAP.get(attack_type, "low")

        rows.append(
            {
                "source_port": source_port,
                "dest_port": dest_port,
                "protocol_encoded": protocol_encoded,
                "packet_length": packet_length,
                "flow_duration": round(flow_duration, 3),
                "packet_rate": round(packet_rate, 3),
                "attack_type": attack_type,
                "severity": severity,
            }
        )

    df = pd.DataFrame(rows)
    logger.info("Synthetic dataset generated", rows=len(df))
    return df


# ---------------------------------------------------------------------------
# Model training
# ---------------------------------------------------------------------------


def train_model(df: pd.DataFrame) -> Tuple[RandomForestClassifier, LabelEncoder, Dict[str, Any]]:
    """Preprocess *df*, train a RandomForest classifier and return artefacts.

    Parameters
    ----------
    df:
        DataFrame with FEATURE_COLUMNS and TARGET_COLUMN present.

    Returns
    -------
    tuple
        ``(model, label_encoder, metrics)`` where metrics contains
        ``accuracy``, ``feature_importance``, ``classification_report``,
        and ``trained_at``.
    """
    logger.info("Starting model training", rows=len(df), features=FEATURE_COLUMNS)

    # Validate required columns
    missing = [c for c in FEATURE_COLUMNS + [TARGET_COLUMN] if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in dataframe: {missing}")

    X = df[FEATURE_COLUMNS].copy()
    y_raw = df[TARGET_COLUMN].copy()

    # Fill any NaNs
    X = X.fillna(0)

    # Encode target labels
    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(y_raw)

    logger.info(
        "Label encoding complete",
        classes=list(label_encoder.classes_),
        n_classes=len(label_encoder.classes_),
    )

    # Train/test split (80/20, stratified)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # RandomForest with sensible defaults
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=15,
        min_samples_leaf=2,
        min_samples_split=5,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    model.fit(X_train, y_train)
    logger.info("RandomForest training complete")

    # Evaluation
    y_pred = model.predict(X_test)
    accuracy = float(accuracy_score(y_test, y_pred))
    report = classification_report(
        y_test,
        y_pred,
        target_names=label_encoder.classes_,
        output_dict=True,
        zero_division=0,
    )

    # Feature importance
    feature_importance = [
        {"feature": feat, "importance": float(imp)}
        for feat, imp in sorted(
            zip(FEATURE_COLUMNS, model.feature_importances_),
            key=lambda x: x[1],
            reverse=True,
        )
    ]

    metrics: Dict[str, Any] = {
        "accuracy": accuracy,
        "feature_importance": feature_importance,
        "classification_report": report,
        "trained_at": datetime.utcnow().isoformat(),
        "n_samples": len(df),
        "n_features": len(FEATURE_COLUMNS),
        "n_classes": len(label_encoder.classes_),
        "classes": list(label_encoder.classes_),
    }

    logger.info(
        "Model evaluation complete",
        accuracy=f"{accuracy:.4f}",
        n_samples=len(df),
    )
    return model, label_encoder, metrics


# ---------------------------------------------------------------------------
# Model persistence
# ---------------------------------------------------------------------------


def save_model(
    model: RandomForestClassifier,
    feature_names: List[str],
    label_encoder: LabelEncoder,
    metrics: Dict[str, Any] | None = None,
    path: str | None = None,
) -> str:
    """Persist model, feature names, and label encoder to disk using joblib.

    Parameters
    ----------
    model:
        Trained sklearn estimator.
    feature_names:
        Ordered list of feature column names used during training.
    label_encoder:
        Fitted :class:`~sklearn.preprocessing.LabelEncoder`.
    metrics:
        Optional training metrics dict to embed in the artefact.
    path:
        Destination path.  Defaults to ``settings.ML_MODEL_PATH``.

    Returns
    -------
    str
        Absolute path where the model was saved.
    """
    save_path = path or settings.ML_MODEL_PATH

    # Ensure directory exists
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)

    artefact = {
        "model": model,
        "feature_names": feature_names,
        "label_encoder": label_encoder,
        "metrics": metrics or {},
        "saved_at": datetime.utcnow().isoformat(),
    }

    joblib.dump(artefact, save_path, compress=3)
    logger.info("Model saved", path=save_path)
    return str(Path(save_path).resolve())


# ---------------------------------------------------------------------------
# Convenience entry point
# ---------------------------------------------------------------------------


def run_training(
    csv_path: str | None = None,
    model_path: str | None = None,
) -> Dict[str, Any]:
    """End-to-end training pipeline: load data → train → save → return metrics.

    Parameters
    ----------
    csv_path:
        Optional path to a CSV dataset.
    model_path:
        Optional output path for the saved model artefact.

    Returns
    -------
    dict
        Training metrics including accuracy and feature importance.
    """
    df = load_or_generate_dataset(csv_path)
    model, label_encoder, metrics = train_model(df)
    save_path = save_model(model, FEATURE_COLUMNS, label_encoder, metrics, model_path)
    metrics["model_path"] = save_path
    logger.info("Training pipeline complete", accuracy=metrics["accuracy"])
    return metrics


if __name__ == "__main__":
    results = run_training()
    print(f"Training complete — accuracy: {results['accuracy']:.4f}")
    print("Feature importance:")
    for fi in results["feature_importance"]:
        print(f"  {fi['feature']}: {fi['importance']:.4f}")
