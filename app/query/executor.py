import time
import logging
from typing import Dict, Any, List, Optional
import pandas as pd
from app.data.repository import TicketRepository
from app.query.schemas import (
    StructuredQuery,
    OperationType,
    FilterCondition,
    FilterOperator,
    SortOrder,
)

logger = logging.getLogger(__name__)

ALLOWED_FILTER_FIELDS = {
    "category", "priority", "status", "agent_id",
    "created_at", "response_time_hrs", "resolution_time_hrs",
    "customer_rating"
}

OPERATOR_MAP = {
    FilterOperator.EQ: lambda series, val: series == val,
    FilterOperator.NE: lambda series, val: series != val,
    FilterOperator.GT: lambda series, val: series > val,
    FilterOperator.LT: lambda series, val: series < val,
    FilterOperator.GTE: lambda series, val: series >= val,
    FilterOperator.LTE: lambda series, val: series <= val,
    FilterOperator.IN: lambda series, val: series.isin(val if isinstance(val, list) else [val]),
    FilterOperator.NOT_IN: lambda series, val: ~series.isin(val if isinstance(val, list) else [val]),
}


class QueryExecutor:
    def __init__(self, repository: TicketRepository):
        self.repository = repository

    def execute(self, query: StructuredQuery) -> Dict[str, Any]:
        start_time = time.perf_counter()

        try:
            if query.operation == OperationType.COUNT:
                result = self._execute_count(query)
            elif query.operation == OperationType.GROUP_BY:
                result = self._execute_group_by(query)
            elif query.operation == OperationType.AVERAGE:
                result = self._execute_average(query)
            elif query.operation == OperationType.LIST:
                result = self._execute_list(query)
            elif query.operation == OperationType.STATS:
                result = self._execute_stats(query)
            else:
                raise ValueError(f"Unsupported operation: {query.operation}")

            execution_time = (time.perf_counter() - start_time) * 1000
            result["execution_time_ms"] = execution_time
            return result

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def _apply_filters(self, df: pd.DataFrame, filters: List[FilterCondition]) -> pd.DataFrame:
        for f in filters:
            if f.field not in ALLOWED_FILTER_FIELDS:
                raise ValueError(f"Filter field '{f.field}' not allowed")

            if f.field not in df.columns:
                raise ValueError(f"Filter field '{f.field}' not found in data")

            op_func = OPERATOR_MAP.get(f.operator)
            if not op_func:
                raise ValueError(f"Unsupported operator: {f.operator}")

            try:
                if f.field == "created_at":
                    val = pd.Timestamp(f.value)
                elif f.field in ["response_time_hrs", "resolution_time_hrs", "customer_rating"]:
                    val = float(f.value)
                else:
                    val = f.value

                mask = op_func(df[f.field], val)
                df = df[mask]
            except Exception as e:
                raise ValueError(f"Failed to apply filter {f.field} {f.operator} {f.value}: {e}")

        return df

    def _execute_count(self, query: StructuredQuery) -> Dict[str, Any]:
        df = self.repository.get_all()
        df = self._apply_filters(df, query.filters)
        count = len(df)
        return {
            "count": count,
            "data": {"count": count},
        }

    def _execute_group_by(self, query: StructuredQuery) -> Dict[str, Any]:
        if not query.group_by:
            raise ValueError("group_by field is required for group_by operation")

        df = self.repository.get_all()
        df = self._apply_filters(df, query.filters)

        metric = query.metric or "count"
        if metric == "count":
            result = df.groupby(query.group_by).size().reset_index(name="count")
        else:
            if metric not in df.columns:
                raise ValueError(f"Metric column '{metric}' not found")
            result = df.groupby(query.group_by)[metric].mean().reset_index(name="average")

        ascending = query.sort == SortOrder.ASC
        result = result.sort_values(result.columns[1], ascending=ascending)

        if query.limit:
            result = result.head(query.limit)

        return {
            "group_by": query.group_by,
            "metric": metric,
            "results": result.to_dict(orient="records"),
            "data": result.to_dict(orient="records"),
        }

    def _execute_average(self, query: StructuredQuery) -> Dict[str, Any]:
        if not query.metric:
            raise ValueError("metric field is required for average operation")

        df = self.repository.get_all()
        df = self._apply_filters(df, query.filters)

        if query.metric not in df.columns:
            raise ValueError(f"Metric column '{query.metric}' not found")

        valid = df[query.metric].dropna()
        if valid.empty:
            avg = None
        else:
            avg = float(valid.mean())

        return {
            "metric": query.metric,
            "average": avg,
            "count": len(valid),
            "data": {"average": avg, "count": len(valid)},
        }

    def _execute_list(self, query: StructuredQuery) -> Dict[str, Any]:
        df = self.repository.get_all()
        df = self._apply_filters(df, query.filters)

        columns = query.columns or [
            "ticket_id", "created_at", "category", "priority", "status",
            "response_time_hrs", "resolution_time_hrs", "agent_id",
            "customer_rating", "issue_summary"
        ]

        df = df[columns]

        if query.sort != SortOrder.DESC and len(df) > 0:
            sort_col = columns[0] if columns else "ticket_id"
            if sort_col in df.columns:
                df = df.sort_values(sort_col, ascending=(query.sort == SortOrder.ASC))

        if query.limit:
            df = df.head(query.limit)

        records = df.to_dict(orient="records")
        for r in records:
            if "created_at" in r and pd.notna(r["created_at"]):
                r["created_at"] = r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"])

        return {
            "count": len(records),
            "results": records,
            "data": records,
        }

    def _execute_stats(self, query: StructuredQuery) -> Dict[str, Any]:
        stats = self.repository.get_stats()
        return {
            "stats": stats,
            "data": stats,
        }