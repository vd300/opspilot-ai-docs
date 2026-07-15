from fastapi import APIRouter, HTTPException, Request, status

from app.graph import run_investigation_workflow
from app.graph.nodes import WorkflowExecutionError, WorkflowValidationError
from app.middleware.request_id import REQUEST_ID_STATE_KEY
from app.schemas.investigations import InvestigationRequest, InvestigationResponse

router = APIRouter(prefix="/api/v1/investigations", tags=["investigations"])


@router.post("", response_model=InvestigationResponse)
def create_investigation(
    payload: InvestigationRequest,
    request: Request,
) -> InvestigationResponse:
    request_id = getattr(request.state, REQUEST_ID_STATE_KEY, None)
    try:
        return run_investigation_workflow(payload, request_id=request_id)
    except WorkflowValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except WorkflowExecutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Investigation workflow could not route the request.",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Investigation workflow returned malformed output.",
        ) from exc
