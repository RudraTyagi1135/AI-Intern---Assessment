from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import logging
import time
from app.query.schemas import QueryRequest, QueryResponse, ErrorResponse
from app.services.llm_service import LLMService, LLMError, LLMUnavailableError
from app.query.executor import QueryExecutor
from app.data.repository import TicketRepository
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()

_repository: TicketRepository = None
_llm_service: LLMService = None
_query_executor: QueryExecutor = None


def get_repository() -> TicketRepository:
    global _repository
    if _repository is None:
        settings = get_settings()
        _repository = TicketRepository(settings.data_file_path)
    return _repository


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


def get_query_executor(repo: TicketRepository = Depends(get_repository)) -> QueryExecutor:
    global _query_executor
    if _query_executor is None:
        _query_executor = QueryExecutor(repo)
    return _query_executor


@router.post("/query", response_model=QueryResponse, responses={400: {"model": ErrorResponse}, 503: {"model": ErrorResponse}})
async def query_tickets(
    request: QueryRequest,
    llm: LLMService = Depends(get_llm_service),
    executor: QueryExecutor = Depends(get_query_executor),
):
    start_time = time.perf_counter()

    try:
        structured_query = llm.parse_question(request.question)
    except LLMUnavailableError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except LLMError as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse question: {e}")

    try:
        result = executor.execute(structured_query)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Query execution error: {e}")
        raise HTTPException(status_code=500, detail="Query execution failed")

    execution_time = (time.perf_counter() - start_time) * 1000

    answer = _format_answer(structured_query, result)

    return QueryResponse(
        question=request.question,
        interpreted_query=structured_query,
        answer=answer,
        data=result.get("data", {}),
        execution_time_ms=execution_time,
    )


def _format_answer(query, result: Dict[str, Any]) -> str:
    op = query.operation.value

    if op == "count":
        return f"There are {result.get('count', 0)} tickets matching your criteria."
    elif op == "group_by":
        results = result.get("results", [])
        if not results:
            return "No results found."
        if query.limit == 1 and results:
            top = results[0]
            group_val = top.get(query.group_by, "N/A")
            metric_val = top.get("count") or top.get("average", "N/A")
            return f"The top {query.group_by} is '{group_val}' with {metric_val} tickets."
        return f"Found {len(results)} groups."
    elif op == "average":
        avg = result.get("average")
        count = result.get("count", 0)
        if avg is None:
            return f"No data available for {query.metric}."
        return f"The average {query.metric} is {avg:.2f} (based on {count} tickets)."
    elif op == "list":
        count = result.get("count", 0)
        return f"Found {count} ticket(s) matching your criteria."
    elif op == "stats":
        return "Dataset statistics retrieved."
    return "Query completed."


@router.get("/query/examples")
async def query_examples():
    return {
        "examples": [
            "How many tickets are currently open?",
            "Which agent resolved the most tickets this month?",
            "Show me all Critical tickets not resolved within 12 hours.",
            "What is the average customer rating for Technical category tickets?",
            "Are there any anomalies in resolution times this week?",
            "How many critical tickets are unresolved?",
            "Which agent has the lowest average customer rating?",
            "What percentage of tickets are escalated?",
            "How many Technical tickets are open?",
            "What is the average resolution time for resolved Billing tickets?",
            "List unresolved Critical tickets.",
            "Which category has the highest average resolution time?",
        ]
    }