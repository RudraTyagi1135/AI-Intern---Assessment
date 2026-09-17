import pytest
import pandas as pd
from app.data.loader import load_and_validate, validate_data, clean_data, DataValidationError
from app.data.repository import TicketRepository


def test_load_csv():
    repo = TicketRepository("support_tickets.csv")
    assert repo is not None
    assert len(repo.df) == 500
    assert list(repo.df.columns) == [
        "ticket_id", "created_at", "category", "priority", "status",
        "response_time_hrs", "resolution_time_hrs", "agent_id",
        "customer_rating", "issue_summary"
    ]


def test_data_types():
    repo = TicketRepository("support_tickets.csv")
    df = repo.df
    assert pd.api.types.is_datetime64_any_dtype(df["created_at"])
    assert pd.api.types.is_float_dtype(df["response_time_hrs"])
    assert pd.api.types.is_float_dtype(df["resolution_time_hrs"])
    assert pd.api.types.is_float_dtype(df["customer_rating"])


def test_missing_values():
    repo = TicketRepository("support_tickets.csv")
    df = repo.df
    assert df["resolution_time_hrs"].isna().sum() == 173
    assert df["customer_rating"].isna().sum() == 173
    assert df["ticket_id"].isna().sum() == 0
    assert df["created_at"].isna().sum() == 0


def test_unique_categories():
    repo = TicketRepository("support_tickets.csv")
    cats = set(repo.df["category"].unique())
    assert cats == {"General", "Billing", "Technical"}


def test_unique_priorities():
    repo = TicketRepository("support_tickets.csv")
    pri = set(repo.df["priority"].unique())
    assert pri == {"Low", "Medium", "High", "Critical"}


def test_unique_statuses():
    repo = TicketRepository("support_tickets.csv")
    stats = set(repo.df["status"].unique())
    assert stats == {"Open", "Resolved", "Escalated"}


def test_agents():
    repo = TicketRepository("support_tickets.csv")
    agents = set(repo.df["agent_id"].unique())
    assert len(agents) == 12
    assert all(a.startswith("AGT-") for a in agents)


def test_date_range():
    repo = TicketRepository("support_tickets.csv")
    min_date = repo.df["created_at"].min()
    max_date = repo.df["created_at"].max()
    assert min_date.year == 2024
    assert max_date.year == 2024
    assert min_date.month == 1
    assert max_date.month == 3


def test_numerical_distributions():
    repo = TicketRepository("support_tickets.csv")
    df = repo.df
    assert df["response_time_hrs"].mean() > 0
    assert df["response_time_hrs"].min() >= 0
    assert df["resolution_time_hrs"].dropna().mean() > 0
    assert df["customer_rating"].dropna().min() >= 1
    assert df["customer_rating"].dropna().max() <= 5


def test_repository_count():
    repo = TicketRepository("support_tickets.csv")
    assert repo.count() == 500
    assert repo.count(status="Open") == 111
    assert repo.count(status="Resolved") == 327
    assert repo.count(priority="Critical") == 55


def test_repository_filter():
    repo = TicketRepository("support_tickets.csv")
    df = repo.filter(category="Technical", priority="High")
    assert len(df) > 0
    assert all(df["category"] == "Technical")
    assert all(df["priority"] == "High")


def test_repository_group_by():
    repo = TicketRepository("support_tickets.csv")
    result = repo.group_by("agent_id", metric="count", filters={"status": "Resolved"}, sort="desc", limit=1)
    assert len(result) == 1
    assert result.iloc[0]["count"] > 0


def test_repository_average():
    repo = TicketRepository("support_tickets.csv")
    avg = repo.average("customer_rating", filters={"category": "Technical"})
    assert avg is not None
    assert 1 <= avg <= 5


def test_repository_stats():
    repo = TicketRepository("support_tickets.csv")
    stats = repo.get_stats()
    assert stats["total_tickets"] == 500
    assert stats["by_status"]["Open"] == 111
    assert "avg_resolution_time_hrs" in stats


def test_invalid_file():
    with pytest.raises(FileNotFoundError):
        TicketRepository("nonexistent.csv")


def test_schema_validation():
    df = pd.DataFrame(columns=["ticket_id", "created_at"])
    with pytest.raises(DataValidationError):
        from app.data.loader import validate_schema
        validate_schema(df)