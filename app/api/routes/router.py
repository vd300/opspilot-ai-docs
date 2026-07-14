from fastapi import APIRouter, Request

from app.middleware.request_id import REQUEST_ID_STATE_KEY
from app.router import RequestRouter, RouteDecision, RouterInput

router = APIRouter(prefix="/api/v1/router", tags=["router"])


@router.post("/classify", response_model=RouteDecision)
def classify_route(payload: RouterInput, request: Request) -> RouteDecision:
    request_id = getattr(request.state, REQUEST_ID_STATE_KEY, None)
    return RequestRouter().route(payload, request_id=request_id)
