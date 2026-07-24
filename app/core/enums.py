"""Shared enumerations for CollabNotify."""

from enum import StrEnum


class ServiceType(StrEnum):
    """Supported collaboration services."""

    GITHUB = "github"
    JIRA = "jira"
    CONFLUENCE = "confluence"
