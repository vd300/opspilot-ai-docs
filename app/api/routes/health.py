from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.health import HealthResponse, ReadinessCheck, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )


@router.get("/ready", response_model=ReadinessResponse)
def ready() -> ReadinessResponse:
    settings = get_settings()
    checks = [
        ReadinessCheck(name="application", status="ok", detail="Application is ready"),
        ReadinessCheck(name="configuration", status="ok", detail="Settings loaded"),
    ]
    return ReadinessResponse(
        status="ready",
        service=settings.app_name,
        environment=settings.environment,
        checks=checks,
    )

