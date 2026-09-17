import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import timedelta
import logging
from app.data.repository import TicketRepository

logger = logging.getLogger(__name__)


@dataclass
class Anomaly:
    ticket_id: str
    anomaly_type: str
    severity: str
    metric: str
    value: float
    threshold: float
    reason: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AnomalyDetector:
    def __init__(self, repository: TicketRepository):
        self.repository = repository

    def detect_all(self) -> List[Anomaly]:
        anomalies = []
        anomalies.extend(self._detect_long_resolution_times())
        anomalies.extend(self._detect_unresolved_high_priority())
        anomalies.extend(self._detect_low_customer_ratings())
        anomalies.extend(self._detect_long_response_times())
        return anomalies

    def _detect_long_resolution_times(self) -> List[Anomaly]:
        anomalies = []
        df = self.repository.get_all()
        resolved = df[df["status"] == "Resolved"].copy()
        resolved = resolved.dropna(subset=["resolution_time_hrs"])

        if len(resolved) < 4:
            logger.warning("Not enough resolved tickets for IQR calculation")
            return anomalies

        Q1 = resolved["resolution_time_hrs"].quantile(0.25)
        Q3 = resolved["resolution_time_hrs"].quantile(0.75)
        IQR = Q3 - Q1
        upper_bound = Q3 + 1.5 * IQR

        outliers = resolved[resolved["resolution_time_hrs"] > upper_bound]

        for _, row in outliers.iterrows():
            anomalies.append(Anomaly(
                ticket_id=row["ticket_id"],
                anomaly_type="long_resolution_time",
                severity="high" if row["resolution_time_hrs"] > upper_bound * 2 else "medium",
                metric="resolution_time_hrs",
                value=float(row["resolution_time_hrs"]),
                threshold=float(upper_bound),
                reason=f"Resolution time exceeds 1.5*IQR upper bound ({upper_bound:.1f} hrs)",
                metadata={
                    "category": row["category"],
                    "priority": row["priority"],
                    "agent_id": row["agent_id"],
                    "created_at": row["created_at"].isoformat() if pd.notna(row["created_at"]) else None,
                    "customer_rating": float(row["customer_rating"]) if pd.notna(row["customer_rating"]) else None,
                    "q1": float(Q1),
                    "q3": float(Q3),
                    "iqr": float(IQR),
                }
            ))

        logger.info(f"Detected {len(anomalies)} long resolution time anomalies (threshold: {upper_bound:.1f} hrs)")
        return anomalies

    def _detect_unresolved_high_priority(self) -> List[Anomaly]:
        anomalies = []
        df = self.repository.get_all()
        ref_ts = self.repository.reference_timestamp

        high_priority_unresolved = df[
            (df["priority"].isin(["High", "Critical"])) &
            (df["status"] != "Resolved")
        ].copy()

        for _, row in high_priority_unresolved.iterrows():
            age_hours = (ref_ts - row["created_at"]).total_seconds() / 3600

            if age_hours > 24:
                severity = "critical" if row["priority"] == "Critical" else "high"
                anomalies.append(Anomaly(
                    ticket_id=row["ticket_id"],
                    anomaly_type="unresolved_high_priority",
                    severity=severity,
                    metric="age_hours",
                    value=float(age_hours),
                    threshold=24.0,
                    reason=f"{row['priority']} priority ticket unresolved for {age_hours:.1f} hours (>24h threshold)",
                    metadata={
                        "category": row["category"],
                        "priority": row["priority"],
                        "status": row["status"],
                        "agent_id": row["agent_id"],
                        "created_at": row["created_at"].isoformat() if pd.notna(row["created_at"]) else None,
                        "age_hours": float(age_hours),
                    }
                ))

        logger.info(f"Detected {len(anomalies)} unresolved high-priority tickets (>24h)")
        return anomalies

    def _detect_low_customer_ratings(self) -> List[Anomaly]:
        anomalies = []
        df = self.repository.get_all()
        rated = df.dropna(subset=["customer_rating"])

        if len(rated) < 4:
            return anomalies

        Q1 = rated["customer_rating"].quantile(0.25)
        Q3 = rated["customer_rating"].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR

        outliers = rated[rated["customer_rating"] < lower_bound]

        for _, row in outliers.iterrows():
            anomalies.append(Anomaly(
                ticket_id=row["ticket_id"],
                anomaly_type="low_customer_rating",
                severity="medium",
                metric="customer_rating",
                value=float(row["customer_rating"]),
                threshold=float(lower_bound),
                reason=f"Customer rating below 1.5*IQR lower bound ({lower_bound:.2f})",
                metadata={
                    "category": row["category"],
                    "priority": row["priority"],
                    "status": row["status"],
                    "agent_id": row["agent_id"],
                    "created_at": row["created_at"].isoformat() if pd.notna(row["created_at"]) else None,
                    "resolution_time_hrs": float(row["resolution_time_hrs"]) if pd.notna(row["resolution_time_hrs"]) else None,
                    "q1": float(Q1),
                    "q3": float(Q3),
                    "iqr": float(IQR),
                }
            ))

        logger.info(f"Detected {len(anomalies)} low customer rating anomalies (threshold: {lower_bound:.2f})")
        return anomalies

    def _detect_long_response_times(self) -> List[Anomaly]:
        anomalies = []
        df = self.repository.get_all()

        Q1 = df["response_time_hrs"].quantile(0.25)
        Q3 = df["response_time_hrs"].quantile(0.75)
        IQR = Q3 - Q1
        upper_bound = Q3 + 1.5 * IQR

        outliers = df[df["response_time_hrs"] > upper_bound]

        for _, row in outliers.iterrows():
            anomalies.append(Anomaly(
                ticket_id=row["ticket_id"],
                anomaly_type="long_response_time",
                severity="medium",
                metric="response_time_hrs",
                value=float(row["response_time_hrs"]),
                threshold=float(upper_bound),
                reason=f"Response time exceeds 1.5*IQR upper bound ({upper_bound:.1f} hrs)",
                metadata={
                    "category": row["category"],
                    "priority": row["priority"],
                    "status": row["status"],
                    "agent_id": row["agent_id"],
                    "created_at": row["created_at"].isoformat() if pd.notna(row["created_at"]) else None,
                    "q1": float(Q1),
                    "q3": float(Q3),
                    "iqr": float(IQR),
                }
            ))

        logger.info(f"Detected {len(anomalies)} long response time anomalies (threshold: {upper_bound:.1f} hrs)")
        return anomalies

    def get_summary(self) -> Dict[str, Any]:
        anomalies = self.detect_all()
        by_type = {}
        by_severity = {}

        for a in anomalies:
            by_type[a.anomaly_type] = by_type.get(a.anomaly_type, 0) + 1
            by_severity[a.severity] = by_severity.get(a.severity, 0) + 1

        return {
            "total_anomalies": len(anomalies),
            "by_type": by_type,
            "by_severity": by_severity,
            "anomalies": [a.to_dict() for a in anomalies],
        }