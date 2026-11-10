"""Internal API endpoints for serverless function webhooks and administrative tasks."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_lambda_secret
from app.db.session import get_db
from app.models.document import Document
from app.models.project import Project
from app.schemas.internal import LambdaQuotaCallbackRequest, LambdaQuotaCallbackResponse

logger = logging.getLogger("app.api.internal")

router = APIRouter(prefix="/internal", tags=["Internal"])


@router.post(
    "/lambda/quota-alert",
    response_model=LambdaQuotaCallbackResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_lambda_secret)],
)
def handle_lambda_quota_callback(
    payload: LambdaQuotaCallbackRequest,
    db: Annotated[Session, Depends(get_db)],
) -> LambdaQuotaCallbackResponse:
    """Internal webhook called by AWS Lambda size limit checker.

    - If status == 'rejected': purges the rejected Document record from DB (S3 object was
      already deleted by Lambda) and synchronizes project.total_size_bytes.
    - If status == 'accepted': synchronizes project.total_size_bytes.
    """
    project = db.get(Project, payload.project_id)
    if not project:
        logger.warning("Callback received for non-existent project id=%d", payload.project_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {payload.project_id} not found",
        )

    if payload.status == "rejected":
        # Document was purged from S3 by Lambda; remove the corresponding DB row
        doc = (
            db.query(Document)
            .filter(
                Document.id == payload.document_id,
                Document.project_id == payload.project_id,
            )
            .first()
        )
        if doc:
            logger.info(
                "Purging rejected document id=%d for project id=%d from database",
                payload.document_id,
                payload.project_id,
            )
            db.delete(doc)

        project.total_size_bytes = payload.total_size_bytes
        db.commit()

        return LambdaQuotaCallbackResponse(
            status="rejected",
            message=f"Document {payload.document_id} rejected due to quota limit and purged",
            project_id=payload.project_id,
            document_id=payload.document_id,
            total_size_bytes=project.total_size_bytes,
        )

    # Status == 'accepted'
    project.total_size_bytes = payload.total_size_bytes
    db.commit()

    return LambdaQuotaCallbackResponse(
        status="accepted",
        message=f"Document {payload.document_id} accepted and project total size synchronized",
        project_id=payload.project_id,
        document_id=payload.document_id,
        total_size_bytes=project.total_size_bytes,
    )
