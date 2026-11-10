from sqlalchemy.orm import Session

from app.models.project import Project, ProjectMember, ProjectRole
from app.models.user import User
from app.schemas.project import ProjectCreateRequest


def create_project(
    db: Session,
    user: User,
    data: ProjectCreateRequest,
) -> Project:
    """Create a new project and assign the creator as OWNER in a single atomic transaction."""
    project = Project(
        name=data.name.strip(),
        description=data.description.strip() if data.description else None,
        total_size_bytes=0,
    )
    db.add(project)
    db.flush()

    # Automatically grant creator owner permissions
    membership = ProjectMember(
        project_id=project.id,
        user_id=user.id,
        role=ProjectRole.OWNER,
    )
    db.add(membership)

    db.commit()
    db.refresh(project)
    return project
