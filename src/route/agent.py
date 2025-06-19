from typing import Literal

from fastapi import APIRouter
from fastapi import status

router = APIRouter(
    prefix="/agent",
    tags=["Agent"],
    responses={
        400: {"description": "Invalid parameter(s)."},
        404: {"description": "Entity not found."}
    },
)


@router.post("/status", tags=["Agent"], status_code=status.HTTP_200_OK)
async def set_status(new_status: Literal["ON", "OFF"]):
    from ..main import agent
    agent.status = new_status


@router.get("/health", tags=["Agent"], status_code=status.HTTP_200_OK)
async def health_check():
    """Health check endpoint"""
    from ..main import agent
    return {
        "status": agent.status
    }
