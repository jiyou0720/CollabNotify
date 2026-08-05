"""Project alias application service tests."""

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import InvalidConfigurationError
from app.repositories.project_repository import ProjectRepository
from app.services.project_alias_service import ProjectAliasService
from database.session import create_session_factory


def _service_and_project(session: Session) -> ProjectAliasService:
    ProjectRepository(session).create(
        "Internal Project",
        "discord",
        "discord:123:internal-project",
        discord_guild_id="123",
    )
    session.commit()
    return ProjectAliasService(create_session_factory(session.get_bind()))


def test_alias_service_crud_and_github_normalization(db_session: Session) -> None:
    """Service manages guild-scoped aliases and normalizes GitHub names."""
    service = _service_and_project(db_session)
    created = service.create_alias(123, "GitHub", "Org/Repository", "Internal Project")

    assert created.external_name == "org/repository"
    assert service.find_by_provider("github", "ORG/REPOSITORY") == created
    assert service.find_all(123) == [created]
    assert service.delete_alias(999, "github", "org/repository") is False
    assert service.delete_alias(123, "github", "org/repository") is True
    assert service.find_all(123) == []


def test_alias_service_rejects_duplicate_and_unknown_project(
    db_session: Session,
) -> None:
    """Invalid or duplicate administrator input produces safe domain errors."""
    service = _service_and_project(db_session)
    service.create_alias(123, "jira", "COLLAB", "Internal Project")

    with pytest.raises(InvalidConfigurationError):
        service.create_alias(123, "jira", "COLLAB", "Internal Project")
    with pytest.raises(InvalidConfigurationError):
        service.create_alias(123, "confluence", "SPACE", "Missing")


def test_alias_service_update(db_session: Session) -> None:
    """An alias can be updated without exposing repository details."""
    service = _service_and_project(db_session)
    service.create_alias(123, "jira", "OLD", "Internal Project")

    updated = service.update_alias(123, "jira", "OLD", new_external_name="NEW")

    assert updated.external_name == "NEW"
    assert service.find_by_provider("jira", "OLD") is None
    assert service.find_by_provider("jira", "NEW") == updated
