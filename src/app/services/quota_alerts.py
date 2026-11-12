from __future__ import annotations

import logging
from dataclasses import dataclass

from app.application.ports.unit_of_work import UnitOfWork
from app.domain.errors import ProjectNotFound

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QuotaAlertResult:
    status: str
    message: str
    project_id: int
    document_id: int
    total_size_bytes: int


def process_quota_alert(
    uow: UnitOfWork,
    *,
    project_id: int,
    document_id: int,
    status: str,
    total_size_bytes: int,
) -> QuotaAlertResult:
    """Process a size limit quota webhook from Lambda and synchronize project size."""
    with uow:
        project = uow.projects.get_by_id_for_update(project_id)
        if project is None:
            logger.warning("Callback received for non-existent project id=%d", project_id)
            raise ProjectNotFound(f"Project {project_id} not found")

        if status == "rejected":
            doc = uow.documents.get_by_id(document_id)
            if doc is not None and doc.project_id == project_id:
                logger.info(
                    "Purging rejected document id=%d for project id=%d from database",
                    document_id,
                    project_id,
                )
                uow.documents.delete(doc)

            project.total_size_bytes = total_size_bytes
            uow.commit()

            return QuotaAlertResult(
                status="rejected",
                message=f"Document {document_id} rejected due to quota limit and purged",
                project_id=project_id,
                document_id=document_id,
                total_size_bytes=project.total_size_bytes,
            )

        # status == "accepted"
        project.total_size_bytes = total_size_bytes
        uow.commit()

        return QuotaAlertResult(
            status="accepted",
            message=f"Document {document_id} accepted and project total size synchronized",
            project_id=project_id,
            document_id=document_id,
            total_size_bytes=project.total_size_bytes,
        )
