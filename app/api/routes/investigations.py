from fastapi import APIRouter, HTTPException, Request, status

from app.graph import load_investigation_response, run_investigation_workflow
from app.graph.nodes import WorkflowExecutionError, WorkflowValidationError
from app.middleware.request_id import REQUEST_ID_STATE_KEY
from app.persistence import InvestigationNotFoundError
from app.schemas.investigations import InvestigationRequest, InvestigationResponse

router = APIRouter(prefix="/api/v1/investigations", tags=["investigations"])


@router.post("", response_model=InvestigationResponse)
def create_investigation(
    payload: InvestigationRequest,
    request: Request,
) -> InvestigationResponse:
    request_id = getattr(request.state, REQUEST_ID_STATE_KEY, None)
    dependencies = getattr(request.app.state, "graph_dependencies", None)
    try:
        return run_investigation_workflow(
            payload,
            request_id=request_id,
            dependencies=dependencies,
        )
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


@router.get("/{investigation_id}", response_model=InvestigationResponse)
def get_investigation(
    investigation_id: str,
    request: Request,
) -> InvestigationResponse:
    dependencies = getattr(request.app.state, "graph_dependencies", None)
    try:
        return load_investigation_response(
            investigation_id,
            dependencies=dependencies,
        )
    except InvestigationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation not found.",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Investigation persistence is not configured.",
        ) from exc
