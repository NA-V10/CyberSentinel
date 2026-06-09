"""
FastAPI router for ML threat prediction endpoints.

Endpoints:
  POST /predict-threat         — Predict threat from network features
  GET  /predict-threat/model-info — Return model metadata
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field, field_validator

from backend.app.ml.predictor import get_feature_importance, get_model_info, predict_threat

router = APIRouter(tags=["ML Prediction"])

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

VALID_PROTOCOLS = frozenset(
    ["TCP", "UDP", "ICMP", "HTTP", "HTTPS", "DNS", "SSH", "FTP"]
)


class PredictThreatRequest(BaseModel):
    """Incoming network feature payload for threat classification."""

    source_port: int = Field(..., ge=0, le=65535, description="Source port number (0–65535)")
    dest_port: int = Field(..., ge=0, le=65535, description="Destination port number (0–65535)")
    protocol: str = Field(..., description="Network protocol (TCP, UDP, ICMP, HTTP, …)")
    packet_length: float = Field(..., ge=0, description="Average packet length in bytes")
    flow_duration: float = Field(..., ge=0, description="Total flow duration in milliseconds")
    packet_rate: float = Field(..., ge=0, description="Packets per second")

    @field_validator("protocol")
    @classmethod
    def validate_protocol(cls, v: str) -> str:
        upper = v.upper()
        if upper not in VALID_PROTOCOLS:
            raise ValueError(
                f"Unknown protocol '{v}'.  Valid values: {sorted(VALID_PROTOCOLS)}"
            )
        return upper

    model_config = {"json_schema_extra": {
        "example": {
            "source_port": 54321,
            "dest_port": 22,
            "protocol": "TCP",
            "packet_length": 128.5,
            "flow_duration": 1200.0,
            "packet_rate": 45.3,
        }
    }}


class ProbabilityEntry(BaseModel):
    """Per-class probability."""

    class_name: str = Field(..., alias="class")
    probability: float

    model_config = {"populate_by_name": True}


class FeatureImportanceEntry(BaseModel):
    """Single feature importance value."""

    feature: str
    importance: float


class PredictThreatResponse(BaseModel):
    """Prediction result returned to the client."""

    attack_type: str = Field(..., description="Predicted threat category")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Prediction confidence (0–1)")
    all_probabilities: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Probability for each known threat class",
    )
    feature_importance: List[FeatureImportanceEntry] = Field(
        default_factory=list,
        description="Model feature importance (descending)",
    )
    cached: bool = Field(default=False, description="True if result came from cache")

    model_config = {"json_schema_extra": {
        "example": {
            "attack_type": "Brute Force",
            "confidence": 0.87,
            "all_probabilities": [
                {"class": "Brute Force", "probability": 0.87},
                {"class": "Benign", "probability": 0.05},
            ],
            "feature_importance": [
                {"feature": "packet_rate", "importance": 0.35},
                {"feature": "dest_port", "importance": 0.28},
            ],
            "cached": False,
        }
    }}


class ModelInfoResponse(BaseModel):
    """Static information about the trained model."""

    accuracy: Optional[float] = Field(None, description="Training accuracy (0–1)")
    trained_at: Optional[str] = Field(None, description="ISO-8601 UTC timestamp of training")
    saved_at: Optional[str] = Field(None, description="ISO-8601 UTC timestamp of last save")
    feature_names: List[str] = Field(default_factory=list, description="Feature column names")
    classes: List[str] = Field(default_factory=list, description="All possible threat classes")
    n_samples: Optional[int] = Field(None, description="Number of training samples")
    n_classes: Optional[int] = Field(None, description="Number of classes")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=PredictThreatResponse,
    summary="Classify a network flow as a threat type",
    status_code=status.HTTP_200_OK,
)
async def classify_threat(request: PredictThreatRequest) -> PredictThreatResponse:
    """Accept a network flow description and return a ML-based threat classification.

    The model predicts one of: Brute Force, DDoS, Phishing, Malware, Port Scan,
    SQL Injection, XSS, or Benign.
    """
    features: Dict[str, Any] = {
        "source_port": request.source_port,
        "dest_port": request.dest_port,
        "protocol": request.protocol,
        "packet_length": request.packet_length,
        "flow_duration": request.flow_duration,
        "packet_rate": request.packet_rate,
    }

    try:
        result = await predict_threat(features)
    except FileNotFoundError as exc:
        logger.error("Model not found during prediction", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML model is not available.  Please trigger model training first.",
        ) from exc
    except Exception as exc:
        logger.error("Prediction failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction error: {exc}",
        ) from exc

    return PredictThreatResponse(
        attack_type=result["attack_type"],
        confidence=result["confidence"],
        all_probabilities=result.get("all_probabilities", []),
        feature_importance=[
            FeatureImportanceEntry(**fi) for fi in result.get("feature_importance", [])
        ],
        cached=result.get("cached", False),
    )


@router.get(
    "/model-info",
    response_model=ModelInfoResponse,
    summary="Get information about the current ML model",
    status_code=status.HTTP_200_OK,
)
async def model_info() -> ModelInfoResponse:
    """Return metadata about the trained model: accuracy, training date, feature names."""
    try:
        info = await get_model_info()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML model has not been trained yet.",
        ) from exc
    except Exception as exc:
        logger.error("Failed to retrieve model info", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not retrieve model info: {exc}",
        ) from exc

    return ModelInfoResponse(**info)


@router.get(
    "/feature-importance",
    response_model=List[FeatureImportanceEntry],
    summary="Get global feature importance from the ML model",
    status_code=status.HTTP_200_OK,
)
async def feature_importance() -> List[FeatureImportanceEntry]:
    """Return the global feature importance scores from the trained RandomForest."""
    try:
        fi_list = await get_feature_importance()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML model has not been trained yet.",
        ) from exc
    except Exception as exc:
        logger.error("Failed to retrieve feature importance", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not retrieve feature importance: {exc}",
        ) from exc

    return [FeatureImportanceEntry(**fi) for fi in fi_list]
