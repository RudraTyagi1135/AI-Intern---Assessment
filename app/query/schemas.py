from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Literal
from enum import Enum


class OperationType(str, Enum):
    COUNT = "count"
    GROUP_BY = "group_by"
    AVERAGE = "average"
    LIST = "list"
    STATS = "stats"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class FilterOperator(str, Enum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    LT = "lt"
    GTE = "gte"
    LTE = "lte"
    IN = "in"
    NOT_IN = "not_in"


class FilterCondition(BaseModel):
    field: str
    operator: FilterOperator = FilterOperator.EQ
    value: Any


class StructuredQuery(BaseModel):
    operation: OperationType
    filters: List[FilterCondition] = Field(default_factory=list)
    group_by: Optional[str] = None
    metric: Optional[str] = None
    sort: SortOrder = SortOrder.DESC
    limit: Optional[int] = None
    columns: Optional[List[str]] = None

    @field_validator("operation")
    @classmethod
    def validate_operation(cls, v: OperationType) -> OperationType:
        return v

    @field_validator("group_by")
    @classmethod
    def validate_group_by(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            allowed = {"category", "priority", "status", "agent_id"}
            if v not in allowed:
                raise ValueError(f"group_by must be one of {allowed}")
        return v

    @field_validator("metric")
    @classmethod
    def validate_metric(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            allowed = {"count", "response_time_hrs", "resolution_time_hrs", "customer_rating"}
            if v not in allowed:
                raise ValueError(f"metric must be one of {allowed}")
        return v

    @field_validator("columns")
    @classmethod
    def validate_columns(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            allowed = {
                "ticket_id", "created_at", "category", "priority", "status",
                "response_time_hrs", "resolution_time_hrs", "agent_id",
                "customer_rating", "issue_summary"
            }
            for col in v:
                if col not in allowed:
                    raise ValueError(f"Column '{col}' not allowed. Allowed: {allowed}")
        return v


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)


class QueryResponse(BaseModel):
    question: str
    interpreted_query: StructuredQuery
    answer: str
    data: Dict[str, Any]
    execution_time_ms: float


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None