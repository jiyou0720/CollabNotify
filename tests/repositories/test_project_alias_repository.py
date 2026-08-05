"""Project alias repository tests."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.repositories.project_alias_repository import ProjectAliasRepository
from app.repositories.project_repository import ProjectRepository


def _project(session: Session, name: str = "Internal") -> int:
    project = ProjectRepository(session).create(
        name,
        "discord",
        f"discord:1:{name.casefold()}",
        discord_guild_id="1",
    )
    return project.id


def test_project_alias_crud(db_session: Session) -> None:
    """Repository supports create, lookup, update, list, and delete."""
    repository = ProjectAliasRepository(db_session)
    project_id = _project(db_session)

    alias = repository.create_alias(project_id, "jira", "COLLAB")
    assert repository.find_by_provider("jira", "COLLAB") is alias
    assert repository.find_all(project_id) == [alias]
    assert repository.find_for_projects({project_id}) == [alias]
    assert repository.find_for_projects(set()) == []

    repository.update_alias(alias, external_name="COLLAB-NEW")
    assert repository.find_by_provider("jira", "COLLAB-NEW") is alias

    repository.delete_alias(alias)
    assert repository.find_all() == []


def test_duplicate_provider_identifier_is_rejected(db_session: Session) -> None:
    """The database enforces provider and external-name uniqueness."""
    repository = ProjectAliasRepository(db_session)
    project_id = _project(db_session)
    repository.create_alias(project_id, "github", "org/repo")

    with pytest.raises(IntegrityError):
        repository.create_alias(project_id, "github", "org/repo")
