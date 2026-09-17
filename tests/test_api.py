import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app
from app.query.schemas import StructuredQuery, OperationType


client = TestClient(app)


def test_health_endpoint():
    with patch("app.api.routes_health.LLMService") as mock_llm:
        mock_instance = MagicMock()
        mock_instance.get_status.return_value = {
            "provider": {"provider": "ollama", "model": "llama3.2:3b", "available": True},
            "available": True
        }
        mock_llm.return_value = mock_instance
        
        response = client.get("/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded"]
        assert data["version"] == "1.0.0"
        assert "data" in data
        assert "llm" in data


def test_health_data_endpoint():
    response = client.get("/health/data")
    assert response.status_code == 200
    data = response.json()
    assert data["total_tickets"] == 500


def test_query_endpoint_llm_unavailable():
    response = client.post("/api/query", json={"question": "How many tickets are open?"})
    assert response.status_code == 503
    assert "LLM provider not available" in response.json()["detail"]


def test_query_endpoint_with_mocked_llm():
    from app.api.routes_query import get_llm_service, get_query_executor
    from app.services.llm_service import LLMService
    from app.query.executor import QueryExecutor
    
    mock_llm = MagicMock()
    mock_llm.parse_question.return_value = StructuredQuery(
        operation=OperationType.COUNT,
        filters=[]
    )
    mock_llm.is_available.return_value = True
    
    mock_executor = MagicMock()
    mock_executor.execute.return_value = {
        "count": 111,
        "data": {"count": 111},
        "execution_time_ms": 1.5
    }
    
    app.dependency_overrides[get_llm_service] = lambda: mock_llm
    app.dependency_overrides[get_query_executor] = lambda: mock_executor
    
    try:
        response = client.post("/api/query", json={"question": "How many tickets are open?"})
        assert response.status_code == 200
        data = response.json()
        assert data["question"] == "How many tickets are open?"
        assert "answer" in data
        assert "data" in data
    finally:
        app.dependency_overrides.clear()


def test_anomalies_endpoint():
    response = client.get("/api/anomalies")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "anomalies" in data
    assert isinstance(data["anomalies"], list)


def test_anomalies_summary_endpoint():
    response = client.get("/api/anomalies/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_anomalies" in data
    assert "by_type" in data
    assert "by_severity" in data


def test_anomalies_types_endpoint():
    response = client.get("/api/anomalies/types")
    assert response.status_code == 200
    data = response.json()
    assert "types" in data
    assert isinstance(data["types"], list)


def test_query_examples_endpoint():
    response = client.get("/api/query/examples")
    assert response.status_code == 200
    data = response.json()
    assert "examples" in data
    assert isinstance(data["examples"], list)
    assert len(data["examples"]) > 0


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data


def test_invalid_query_request():
    response = client.post("/api/query", json={})
    assert response.status_code == 422