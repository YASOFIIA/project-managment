# Internal endpoints for Lambda webhooks
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import get_uow, require_lambda_secret
from app.application.ports.unit_of_work import UnitOfWork
from app.schemas.internal import LambdaQuotaCallbackRequest, LambdaQuotaCallbackResponse
from app.services.quota_alerts import process_quota_alert

router = APIRouter(prefix="/internal", tags=["Internal"])

UowDep = Annotated[UnitOfWork, Depends(get_uow)]


# Handle Lambda size limit webhook callback
@router.post(
    "/lambda/quota-alert",
    response_model=LambdaQuotaCallbackResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_lambda_secret)],
)
def handle_lambda_quota_callback(
    payload: LambdaQuotaCallbackRequest,
    uow: UowDep,
) -> LambdaQuotaCallbackResponse:
    result = process_quota_alert(
        uow=uow,
        project_id=payload.project_id,
        document_id=payload.document_id,
        status=payload.status,
        total_size_bytes=payload.total_size_bytes,
    )
    return LambdaQuotaCallbackResponse(
        status=result.status,
        message=result.message,
        project_id=result.project_id,
        document_id=result.document_id,
        total_size_bytes=result.total_size_bytes,
    )
