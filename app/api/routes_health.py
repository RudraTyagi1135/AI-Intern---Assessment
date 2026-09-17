from fastapi import APIRouter, Depends
from typing import Dict, Any
import logging
from app.config import get_settings
from app.services.llm_service import LLMService
from app.data.repository import TicketRepository

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def health_check():
    settings = get_settings()

    data_status = "ok"
    data_detail = ""
    try:
        repo = TicketRepository(settings.data_file_path)
        stats = repo.get_stats()
        data_detail = f"{stats['total_tickets']} tickets loaded"
    except Exception as e:
        data_status = "error"
        data_detail = str(e)

    llm_service = LLMService()
    llm_status = llm_service.get_status()

    overall = "healthy" if data_status == "ok" and llm_status["available"] else "degraded"

    return {
        "status": overall,
        "version": settings.app_version,
        "data": {
            "status": data_status,
            "detail": data_detail,
            "file": settings.data_file_path,
        },
        "llm": llm_status,
    }


@router.get("/data")
async def health_data():
    settings = get_settings()
    try:
        repo = TicketRepository(settings.data_file_path)
        return repo.get_stats()
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@router.get("/llm")
async def health_llm():
    llm_service = LLMService()
    return llm_service.get_status()