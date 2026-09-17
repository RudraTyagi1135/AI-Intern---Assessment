import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = [
    "ticket_id",
    "created_at",
    "category",
    "priority",
    "status",
    "response_time_hrs",
    "resolution_time_hrs",
    "agent_id",
    "customer_rating",
    "issue_summary",
]

VALID_CATEGORIES = {"General", "Billing", "Technical"}
VALID_PRIORITIES = {"Low", "Medium", "High", "Critical"}
VALID_STATUSES = {"Open", "Resolved", "Escalated"}


class DataValidationError(Exception):
    pass


def validate_schema(df: pd.DataFrame) -> None:
    missing_cols = set(REQUIRED_COLUMNS) - set(df.columns)
    if missing_cols:
        raise DataValidationError(f"Missing required columns: {missing_cols}")

    extra_cols = set(df.columns) - set(REQUIRED_COLUMNS)
    if extra_cols:
        logger.warning(f"Extra columns found (will be ignored): {extra_cols}")


def validate_data(df: pd.DataFrame) -> pd.DataFrame:
    errors = []

    invalid_categories = set(df["category"].unique()) - VALID_CATEGORIES
    if invalid_categories:
        errors.append(f"Invalid categories: {invalid_categories}")

    invalid_priorities = set(df["priority"].unique()) - VALID_PRIORITIES
    if invalid_priorities:
        errors.append(f"Invalid priorities: {invalid_priorities}")

    invalid_statuses = set(df["status"].unique()) - VALID_STATUSES
    if invalid_statuses:
        errors.append(f"Invalid statuses: {invalid_statuses}")

    if errors:
        raise DataValidationError("; ".join(errors))

    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    if df["created_at"].isna().any():
        raise DataValidationError("Invalid datetime values in created_at column")

    df["response_time_hrs"] = pd.to_numeric(df["response_time_hrs"], errors="coerce")
    df["resolution_time_hrs"] = pd.to_numeric(df["resolution_time_hrs"], errors="coerce")
    df["customer_rating"] = pd.to_numeric(df["customer_rating"], errors="coerce")

    df["ticket_id"] = df["ticket_id"].astype(str).str.strip()
    df["category"] = df["category"].astype(str).str.strip()
    df["priority"] = df["priority"].astype(str).str.strip()
    df["status"] = df["status"].astype(str).str.strip()
    df["agent_id"] = df["agent_id"].astype(str).str.strip()
    df["issue_summary"] = df["issue_summary"].astype(str).str.strip()

    return df


def load_and_validate(file_path: str) -> pd.DataFrame:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Data file not found: {file_path}")

    logger.info(f"Loading data from {file_path}")
    df = pd.read_csv(file_path, encoding="utf-8")

    validate_schema(df)
    df = clean_data(df)
    validate_data(df)

    logger.info(f"Loaded {len(df)} tickets successfully")
    logger.info(f"Date range: {df['created_at'].min()} to {df['created_at'].max()}")
    logger.info(f"Missing resolution_time_hrs: {df['resolution_time_hrs'].isna().sum()}")
    logger.info(f"Missing customer_rating: {df['customer_rating'].isna().sum()}")

    return df


def get_reference_timestamp(df: pd.DataFrame, env_override: Optional[str] = None) -> pd.Timestamp:
    if env_override:
        try:
            return pd.Timestamp(env_override)
        except Exception as e:
            logger.warning(f"Invalid REFERENCE_TIMESTAMP env var: {e}, using max created_at")

    return df["created_at"].max()