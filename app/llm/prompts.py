import json
from app.query.schemas import (
    StructuredQuery,
    OperationType,
    FilterCondition,
    FilterOperator,
    SortOrder,
)

SYSTEM_PROMPT = """You are a query planner for a customer support ticket system. 
Your task is to convert natural language questions into structured JSON queries.

The database has the following schema:
- ticket_id: string (e.g., "TKT-001")
- created_at: datetime (range: 2024-01-01 to 2024-03-30)
- category: string (one of: "General", "Billing", "Technical")
- priority: string (one of: "Low", "Medium", "High", "Critical")
- status: string (one of: "Open", "Resolved", "Escalated")
- response_time_hrs: float
- resolution_time_hrs: float (nullable - only for resolved tickets)
- agent_id: string (e.g., "AGT-01" through "AGT-12")
- customer_rating: float 1-5 (nullable - only for resolved tickets)
- issue_summary: string

Supported operations:
1. "count" - count tickets matching filters
2. "group_by" - group by a field and aggregate (count, average of metric)
3. "average" - compute average of a numeric metric
4. "list" - list tickets matching filters
5. "stats" - get overall dataset statistics

Filters use operators: eq, ne, gt, lt, gte, lte, in, not_in
Fields available for filtering: category, priority, status, agent_id, created_at, response_time_hrs, resolution_time_hrs, customer_rating

Output MUST be valid JSON matching this schema:
{
  "operation": "count|group_by|average|list|stats",
  "filters": [{"field": "...", "operator": "...", "value": ...}],
  "group_by": "category|priority|status|agent_id",
  "metric": "count|response_time_hrs|resolution_time_hrs|customer_rating",
  "sort": "asc|desc",
  "limit": integer,
  "columns": ["ticket_id", "created_at", ...]
}

Rules:
- For "how many" questions → use "count"
- For "which agent/category/priority has most/least" → use "group_by" with metric="count", sort="desc"/"asc", limit=1
- For "average rating/time" → use "average" with metric
- For "show me / list" → use "list"
- For date references like "this month" use the data's max date as reference (2024-03-30)
- "unresolved" means status != "Resolved"
- "high priority" means priority in ["High", "Critical"]
- For time comparisons, use hours (e.g., "12 hours" → resolution_time_hrs > 12)
- Always use the exact field names and enum values as defined above
- Return ONLY the JSON, no explanation, no markdown"""


def build_user_prompt(question: str) -> str:
    return f"Question: {question}\n\nJSON Query:"


def parse_llm_response(response: str) -> StructuredQuery:
    try:
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        data = json.loads(response)

        filters = []
        for f in data.get("filters", []):
            filters.append(FilterCondition(**f))

        return StructuredQuery(
            operation=OperationType(data["operation"]),
            filters=filters,
            group_by=data.get("group_by"),
            metric=data.get("metric"),
            sort=SortOrder(data.get("sort", "desc")),
            limit=data.get("limit"),
            columns=data.get("columns"),
        )
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}")
    except Exception as e:
        raise ValueError(f"Failed to parse LLM response: {e}")