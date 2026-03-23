from __future__ import annotations
from fastapi import APIRouter, Response


router = APIRouter(prefix="/common", tags=["Dashboard"])


@router.get("/health-check")
def get_dashboard_alerts():
    return Response(status_code=200)


