"""
ML threat predictor for CyberSentinel AI.

Loads a trained RandomForest model from disk and exposes a prediction API.
Predictions are cached in Redis for 30 minutes.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import numpy as np
from loguru import logger

from backend.app.core.config import settings
from backend.app.core.redis_client import cache_get, cache_set

# ---------------------------------------------------------------------------
# Cache TTL (30 minutes)
# ---------------------------------------------------------------------------

_PREDICTION_CACHE_TTL = 1800  # seconds

# ---------------------------------------------------------------------------
# Module-level model artefact cache (in-process)
# ---------------------------------------------------------------------------

_artefact: Optional[Dict[str, Any]] = None


def _load_artefact(path: str | None = None) -> Dict[str, Any]:
    """Load (or return the cached) model artefact from disk.

    Parameters
    ----------
    path:
        Path to the joblib artefact.  Defaults to ``settings.ML_MODEL_PATH``.

    Returns
    -------
    dict
        Keys: ``model``, ``feature_names``, ``label_encoder``, ``metrics``,
        ``saved_at``.

    Raises
    ------
    FileNotFoundError
        If the model file does not exist.  Call ``trainer.run_training()``
        to generate it first.
    """
    global _artefact
    if _artefact is not None:
        return _artefact

    model_path = path or settings.ML_MODEL_PATH
    resolved = Path(model_path).resolve()

    if not resolved.exists():
        logger.warning(
            "Model file not found — attempting to train a new one",
            path=str(resolved),
        )
        from backend.app.ml.trainer import run_training

        run_training(model_path=model_path)

    if not resolved.exists():
        raise FileNotFoundError(
            f"ML model not found at '{resolved}'.  "
            "Run trainer.run_training() to generate it."
        )

    _artefact = joblib.load(str(resolved))
    logger.info(
        "ML model loaded",
        path=str(resolved),
        saved_at=_artefact.get("saved_at"),
        classes=_artefact["label_encoder"].classes_.tolist(),
    )
    return _artefact


def reload_model(path: str | None = None) -> None:
    """Force-reload the model artefact from disk (discards the in-process cache)."""
    global _artefact
    _artefact = None
    _load_artefact(path)
    logger.info("Model reloaded from disk")


# ---------------------------------------------------------------------------
# Feature helpers
# ---------------------------------------------------------------------------

_PROTOCOL_MAP: Dict[str, int] = {
    "tcp": 0,
    "udp": 1,
    "icmp": 2,
    "http": 3,
    "https": 4,
    "dns": 5,
    "ssh": 6,
    "ftp": 7,
}


def _build_feature_vector(features: Dict[str, Any], feature_names: List[str]) -> np.ndarray:
    """Convert a raw features dict into a numpy array aligned to *feature_names*.

    Handles protocol string → integer encoding.

    Parameters
    ----------
    features:
        Dict with keys matching FEATURE_COLUMNS (source_port, dest_port,
        protocol / protocol_encoded, packet_length, flow_duration, packet_rate).
    feature_names:
        Ordered list of feature columns expected by the model.

    Returns
    -------
    np.ndarray
        Shape ``(1, n_features)``.
    """
    resolved: Dict[str, float] = {}

    # Encode protocol
    if "protocol_encoded" in feature_names:
        raw_proto = features.get("protocol_encoded") or features.get("protocol", "tcp")
        if isinstance(raw_proto, str):
            resolved["protocol_encoded"] = float(
                _PROTOCOL_MAP.get(raw_proto.lower(), 0)
            )
        else:
            resolved["protocol_encoded"] = float(raw_proto)

    for fname in feature_names:
        if fname == "protocol_encoded":
            continue
        val = features.get(fname, 0)
        try:
            resolved[fname] = float(val)
        except (TypeError, ValueError):
            resolved[fname] = 0.0

    vector = np.array([[resolved.get(f, 0.0) for f in feature_names]], dtype=np.float64)
    return vector


def _cache_key(features: Dict[str, Any]) -> str:
    """Derive a stable Redis cache key from the feature dict."""
    serialised = json.dumps(features, sort_keys=True, default=str)
    digest = hashlib.sha256(serialised.encode()).hexdigest()[:24]
    return f"cybersentinel:predict:{digest}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def predict_threat(features: Dict[str, Any]) -> Dict[str, Any]:
    """Predict the threat type for a given set of network features.

    Checks Redis for a cached result first (TTL 30 min).

    Parameters
    ----------
    features:
        Dict with keys: source_port, dest_port, protocol (or protocol_encoded),
        packet_length, flow_duration, packet_rate.

    Returns
    -------
    dict
        Keys:
        - ``attack_type`` (str): Predicted threat label.
        - ``confidence`` (float): Probability of the top class (0–1).
        - ``all_probabilities`` (list[dict]): ``{class, probability}`` for each class.
        - ``feature_importance`` (list[dict]): ``{feature, importance}`` sorted descending.
        - ``cached`` (bool): Whether the result came from cache.
    """
    key = _cache_key(features)
    cached = await cache_get(key)
    if cached is not None:
        cached["cached"] = True
        return cached

    artefact = _load_artefact()
    model = artefact["model"]
    label_encoder = artefact["label_encoder"]
    feature_names: List[str] = artefact["feature_names"]

    vector = _build_feature_vector(features, feature_names)

    # Predict class probabilities
    proba = model.predict_proba(vector)[0]  # shape (n_classes,)
    predicted_index = int(np.argmax(proba))
    predicted_class: str = label_encoder.inverse_transform([predicted_index])[0]
    confidence = float(proba[predicted_index])

    all_probs = [
        {"class": label_encoder.inverse_transform([i])[0], "probability": float(p)}
        for i, p in enumerate(proba)
    ]
    all_probs.sort(key=lambda x: x["probability"], reverse=True)

    # Feature importance from the trained forest
    fi_list = [
        {"feature": fname, "importance": float(imp)}
        for fname, imp in sorted(
            zip(feature_names, model.feature_importances_),
            key=lambda x: x[1],
            reverse=True,
        )
    ]

    result: Dict[str, Any] = {
        "attack_type": predicted_class,
        "confidence": confidence,
        "all_probabilities": all_probs,
        "feature_importance": fi_list,
        "cached": False,
    }

    await cache_set(key, result, ttl=_PREDICTION_CACHE_TTL)
    logger.info(
        "Threat prediction complete",
        attack_type=predicted_class,
        confidence=f"{confidence:.4f}",
    )
    return result


async def get_feature_importance() -> List[Dict[str, Any]]:
    """Return the global feature importance from the trained model.

    Returns
    -------
    list[dict]
        Each element: ``{feature: str, importance: float}`` sorted descending.
    """
    artefact = _load_artefact()
    model = artefact["model"]
    feature_names: List[str] = artefact["feature_names"]

    return [
        {"feature": fname, "importance": float(imp)}
        for fname, imp in sorted(
            zip(feature_names, model.feature_importances_),
            key=lambda x: x[1],
            reverse=True,
        )
    ]


async def get_model_info() -> Dict[str, Any]:
    """Return metadata about the currently loaded model.

    Returns
    -------
    dict
        Keys: accuracy, trained_at, saved_at, feature_names, classes,
        n_samples, n_classes.
    """
    artefact = _load_artefact()
    metrics: Dict[str, Any] = artefact.get("metrics", {})

    return {
        "accuracy": metrics.get("accuracy"),
        "trained_at": metrics.get("trained_at"),
        "saved_at": artefact.get("saved_at"),
        "feature_names": artefact["feature_names"],
        "classes": artefact["label_encoder"].classes_.tolist(),
        "n_samples": metrics.get("n_samples"),
        "n_classes": metrics.get("n_classes"),
    }
