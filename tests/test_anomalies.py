import pytest
from app.data.repository import TicketRepository
from app.anomaly.detector import AnomalyDetector, Anomaly


@pytest.fixture
def detector():
    repo = TicketRepository("support_tickets.csv")
    return AnomalyDetector(repo)


def test_detect_long_resolution_times(detector):
    anomalies = detector._detect_long_resolution_times()
    assert isinstance(anomalies, list)
    for a in anomalies:
        assert a.anomaly_type == "long_resolution_time"
        assert a.severity in ["medium", "high"]
        assert a.metric == "resolution_time_hrs"
        assert a.value > a.threshold


def test_detect_unresolved_high_priority(detector):
    anomalies = detector._detect_unresolved_high_priority()
    assert isinstance(anomalies, list)
    for a in anomalies:
        assert a.anomaly_type == "unresolved_high_priority"
        assert a.severity in ["high", "critical"]
        assert a.metric == "age_hours"
        assert a.value > 24
        assert a.threshold == 24.0


def test_detect_low_customer_ratings(detector):
    anomalies = detector._detect_low_customer_ratings()
    assert isinstance(anomalies, list)
    for a in anomalies:
        assert a.anomaly_type == "low_customer_rating"
        assert a.metric == "customer_rating"
        assert a.value < a.threshold


def test_detect_long_response_times(detector):
    anomalies = detector._detect_long_response_times()
    assert isinstance(anomalies, list)
    for a in anomalies:
        assert a.anomaly_type == "long_response_time"
        assert a.metric == "response_time_hrs"
        assert a.value > a.threshold


def test_detect_all(detector):
    anomalies = detector.detect_all()
    assert isinstance(anomalies, list)
    assert len(anomalies) > 0
    for a in anomalies:
        assert isinstance(a, Anomaly)
        assert a.ticket_id
        assert a.anomaly_type
        assert a.severity


def test_get_summary(detector):
    summary = detector.get_summary()
    assert "total_anomalies" in summary
    assert "by_type" in summary
    assert "by_severity" in summary
    assert "anomalies" in summary
    assert summary["total_anomalies"] > 0
    assert isinstance(summary["by_type"], dict)
    assert isinstance(summary["by_severity"], dict)
    assert isinstance(summary["anomalies"], list)


def test_anomaly_to_dict(detector):
    anomalies = detector.detect_all()
    if anomalies:
        d = anomalies[0].to_dict()
        assert isinstance(d, dict)
        assert "ticket_id" in d
        assert "anomaly_type" in d
        assert "severity" in d
        assert "metric" in d
        assert "value" in d
        assert "threshold" in d
        assert "reason" in d
        assert "metadata" in d