from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Any
import logging
from app.anomaly.detector import AnomalyDetector, Anomaly
from app.data.repository import TicketRepository
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()

_detector: AnomalyDetector = None


def get_repository() -> TicketRepository:
    settings = get_settings()
    return TicketRepository(settings.data_file_path)


def get_detector(repo: TicketRepository = Depends(get_repository)) -> AnomalyDetector:
    global _detector
    if _detector is None:
        _detector = AnomalyDetector(repo)
    return _detector


@router.get("/anomalies")
async def get_anomalies(
    detector: AnomalyDetector = Depends(get_detector),
    anomaly_type: str = Query(None, description="Filter by anomaly type"),
    severity: str = Query(None, description="Filter by severity (critical, high, medium, low)"),
    limit: int = Query(100, ge=1, le=1000),
):
    try:
        summary = detector.get_summary()
        anomalies = summary["anomalies"]

        if anomaly_type:
            anomalies = [a for a in anomalies if a["anomaly_type"] == anomaly_type]
        if severity:
            anomalies = [a for a in anomalies if a["severity"] == severity]

        anomalies = anomalies[:limit]

        return {
            "total": summary["total_anomalies"],
            "filtered": len(anomalies),
            "by_type": summary["by_type"],
            "by_severity": summary["by_severity"],
            "anomalies": anomalies,
        }
    except Exception as e:
        logger.error(f"Anomaly detection error: {e}")
        raise HTTPException(status_code=500, detail="Anomaly detection failed")


@router.get("/anomalies/summary")
async def get_anomalies_summary(detector: AnomalyDetector = Depends(get_detector)):
    try:
        summary = detector.get_summary()
        return {
            "total_anomalies": summary["total_anomalies"],
            "by_type": summary["by_type"],
            "by_severity": summary["by_severity"],
        }
    except Exception as e:
        logger.error(f"Anomaly summary error: {e}")
        raise HTTPException(status_code=500, detail="Anomaly detection failed")


@router.get("/anomalies/types")
async def get_anomaly_types(detector: AnomalyDetector = Depends(get_detector)):
    summary = detector.get_summary()
    return {"types": list(summary["by_type"].keys())}