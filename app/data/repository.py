import pandas as pd
from typing import Optional, List, Dict, Any
from datetime import timedelta
import logging
from app.data.loader import load_and_validate, get_reference_timestamp, DataValidationError

logger = logging.getLogger(__name__)


class TicketRepository:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._df: Optional[pd.DataFrame] = None
        self._reference_ts: Optional[pd.Timestamp] = None
        self._load_data()

    def _load_data(self) -> None:
        try:
            self._df = load_and_validate(self.file_path)
            self._reference_ts = get_reference_timestamp(self._df)
            logger.info(f"Reference timestamp set to: {self._reference_ts}")
        except (FileNotFoundError, DataValidationError) as e:
            logger.error(f"Failed to load data: {e}")
            raise

    @property
    def df(self) -> pd.DataFrame:
        if self._df is None:
            self._load_data()
        return self._df

    @property
    def reference_timestamp(self) -> pd.Timestamp:
        if self._reference_ts is None:
            self._reference_ts = get_reference_timestamp(self._df)
        return self._reference_ts

    def reload(self) -> None:
        self._df = None
        self._reference_ts = None
        self._load_data()

    def get_all(self) -> pd.DataFrame:
        return self.df.copy()

    def get_by_id(self, ticket_id: str) -> Optional[pd.Series]:
        matches = self.df[self.df["ticket_id"] == ticket_id]
        if matches.empty:
            return None
        return matches.iloc[0]

    def filter(
        self,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        agent_id: Optional[str] = None,
        created_after: Optional[pd.Timestamp] = None,
        created_before: Optional[pd.Timestamp] = None,
        resolution_time_gt: Optional[float] = None,
        resolution_time_lt: Optional[float] = None,
        customer_rating_gt: Optional[float] = None,
        customer_rating_lt: Optional[float] = None,
        status_not: Optional[str] = None,
        priority_in: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        df = self.df

        if category:
            df = df[df["category"] == category]
        if priority:
            df = df[df["priority"] == priority]
        if priority_in:
            df = df[df["priority"].isin(priority_in)]
        if status:
            df = df[df["status"] == status]
        if status_not:
            df = df[df["status"] != status_not]
        if agent_id:
            df = df[df["agent_id"] == agent_id]
        if created_after:
            df = df[df["created_at"] >= created_after]
        if created_before:
            df = df[df["created_at"] <= created_before]
        if resolution_time_gt is not None:
            df = df[df["resolution_time_hrs"] > resolution_time_gt]
        if resolution_time_lt is not None:
            df = df[df["resolution_time_hrs"] < resolution_time_lt]
        if customer_rating_gt is not None:
            df = df[df["customer_rating"] > customer_rating_gt]
        if customer_rating_lt is not None:
            df = df[df["customer_rating"] < customer_rating_lt]

        return df

    def count(self, **filters) -> int:
        return len(self.filter(**filters))

    def group_by(
        self,
        group_by: str,
        metric: str = "count",
        filters: Optional[Dict[str, Any]] = None,
        sort: str = "desc",
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        df = self.filter(**(filters or {}))

        if metric == "count":
            result = df.groupby(group_by).size().reset_index(name="count")
        elif metric in ["mean", "avg", "average"]:
            if metric not in df.columns:
                raise ValueError(f"Metric column '{metric}' not found")
            result = df.groupby(group_by)[metric].mean().reset_index(name="average")
        elif metric == "sum":
            if metric not in df.columns:
                raise ValueError(f"Metric column '{metric}' not found")
            result = df.groupby(group_by)[metric].sum().reset_index(name="total")
        else:
            raise ValueError(f"Unsupported metric: {metric}")

        ascending = sort.lower() == "asc"
        result = result.sort_values(result.columns[1], ascending=ascending)

        if limit:
            result = result.head(limit)

        return result

    def average(self, metric: str, filters: Optional[Dict[str, Any]] = None) -> Optional[float]:
        df = self.filter(**(filters or {}))
        if metric not in df.columns:
            raise ValueError(f"Metric column '{metric}' not found")
        valid = df[metric].dropna()
        if valid.empty:
            return None
        return float(valid.mean())

    def list_tickets(
        self,
        filters: Optional[Dict[str, Any]] = None,
        columns: Optional[List[str]] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        df = self.filter(**(filters or {}))
        if columns:
            df = df[columns]
        if limit:
            df = df.head(limit)
        return df

    def get_stats(self) -> Dict[str, Any]:
        df = self.df
        return {
            "total_tickets": len(df),
            "by_status": df["status"].value_counts().to_dict(),
            "by_priority": df["priority"].value_counts().to_dict(),
            "by_category": df["category"].value_counts().to_dict(),
            "by_agent": df["agent_id"].value_counts().to_dict(),
            "date_range": {
                "min": df["created_at"].min().isoformat(),
                "max": df["created_at"].max().isoformat(),
            },
            "avg_response_time_hrs": float(df["response_time_hrs"].mean()),
            "avg_resolution_time_hrs": float(df["resolution_time_hrs"].dropna().mean()),
            "avg_customer_rating": float(df["customer_rating"].dropna().mean()),
            "missing_resolution_time": int(df["resolution_time_hrs"].isna().sum()),
            "missing_customer_rating": int(df["customer_rating"].isna().sum()),
        }

    def get_tickets_in_timerange(self, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
        return self.filter(created_after=start, created_before=end)