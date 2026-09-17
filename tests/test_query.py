import pytest
from app.data.repository import TicketRepository
from app.query.executor import QueryExecutor
from app.query.schemas import (
    StructuredQuery, OperationType, FilterCondition, FilterOperator, SortOrder
)


@pytest.fixture
def executor():
    repo = TicketRepository("support_tickets.csv")
    return QueryExecutor(repo)


def test_execute_count(executor):
    query = StructuredQuery(
        operation=OperationType.COUNT,
        filters=[FilterCondition(field="status", operator=FilterOperator.EQ, value="Open")]
    )
    result = executor.execute(query)
    assert result["count"] == 111
    assert "execution_time_ms" in result


def test_execute_count_multiple_filters(executor):
    query = StructuredQuery(
        operation=OperationType.COUNT,
        filters=[
            FilterCondition(field="priority", operator=FilterOperator.EQ, value="Critical"),
            FilterCondition(field="status", operator=FilterOperator.NE, value="Resolved"),
        ]
    )
    result = executor.execute(query)
    assert result["count"] == 31


def test_execute_group_by(executor):
    query = StructuredQuery(
        operation=OperationType.GROUP_BY,
        group_by="agent_id",
        metric="count",
        filters=[FilterCondition(field="status", operator=FilterOperator.EQ, value="Resolved")],
        sort=SortOrder.DESC,
        limit=3
    )
    result = executor.execute(query)
    assert len(result["results"]) == 3
    assert result["results"][0]["count"] >= result["results"][1]["count"]


def test_execute_average(executor):
    query = StructuredQuery(
        operation=OperationType.AVERAGE,
        metric="customer_rating",
        filters=[FilterCondition(field="category", operator=FilterOperator.EQ, value="Technical")]
    )
    result = executor.execute(query)
    assert result["average"] is not None
    assert 1 <= result["average"] <= 5
    assert result["count"] > 0


def test_execute_list(executor):
    query = StructuredQuery(
        operation=OperationType.LIST,
        filters=[
            FilterCondition(field="priority", operator=FilterOperator.EQ, value="Critical"),
            FilterCondition(field="status", operator=FilterOperator.NE, value="Resolved"),
        ],
        limit=5
    )
    result = executor.execute(query)
    assert result["count"] <= 5
    assert isinstance(result["results"], list)


def test_execute_stats(executor):
    query = StructuredQuery(operation=OperationType.STATS)
    result = executor.execute(query)
    assert "stats" in result
    assert result["stats"]["total_tickets"] == 500


def test_invalid_filter_field(executor):
    query = StructuredQuery(
        operation=OperationType.COUNT,
        filters=[FilterCondition(field="invalid_field", operator=FilterOperator.EQ, value="test")]
    )
    with pytest.raises(ValueError, match="not allowed"):
        executor.execute(query)


def test_invalid_operator():
    from app.query.schemas import FilterOperator
    with pytest.raises(ValueError, match="is not a valid FilterOperator"):
        FilterOperator("invalid")


def test_group_by_invalid_field():
    from pydantic_core import ValidationError
    with pytest.raises(ValidationError, match="group_by must be one of"):
        StructuredQuery(
            operation=OperationType.GROUP_BY,
            group_by="invalid_field",
            metric="count"
        )


def test_average_invalid_metric():
    from pydantic_core import ValidationError
    with pytest.raises(ValidationError, match="metric must be one of"):
        StructuredQuery(
            operation=OperationType.AVERAGE,
            metric="invalid_metric"
        )