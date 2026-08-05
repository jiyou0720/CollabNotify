"""FastAPI dependency providers."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request

from app.config.settings import WebhookConfig
from app.core.enums import ServiceType
from app.dispatcher.dispatcher import EventDispatcher
from app.handlers.confluence.handler import ConfluenceHandler
from app.handlers.github.handler import GithubHandler
from app.handlers.jira.handler import JiraHandler
from app.services.webhook_service import NotificationCoordinator, WebhookService


def get_health_status() -> str:
    """Return the current process health status."""
    return "ok"


def get_webhook_config() -> WebhookConfig:
    """Load webhook authentication settings for an inbound request."""
    return WebhookConfig.from_env()


@lru_cache(maxsize=1)
def get_event_dispatcher() -> EventDispatcher:
    """Return the process-wide Dispatcher with all MVP Handlers registered."""
    dispatcher = EventDispatcher()
    github_events = (
        "issues",
        "issue_comment",
        "pull_request",
        "pull_request_review",
        "pull_request_review_comment",
        "push",
        "release",
        "workflow_run",
        "create",
        "delete",
    )
    jira_events = (
        "jira:issue_created",
        "jira:issue_updated",
        "jira:issue_deleted",
        "comment_created",
        "comment_updated",
        "comment_deleted",
    )
    confluence_events = (
        "page_created",
        "page_updated",
        "page_deleted",
        "comment_created",
        "attachment_created",
    )
    for event_type in github_events:
        dispatcher.register(ServiceType.GITHUB, event_type, GithubHandler(event_type))
    for event_type in jira_events:
        dispatcher.register(ServiceType.JIRA, event_type, JiraHandler(event_type))
    for event_type in confluence_events:
        dispatcher.register(
            ServiceType.CONFLUENCE,
            event_type,
            ConfluenceHandler(event_type),
        )
    return dispatcher


def get_webhook_service(
    request: Request,
    dispatcher: Annotated[EventDispatcher, Depends(get_event_dispatcher)],
) -> WebhookService:
    """Create request orchestration using the application runtime."""
    coordinator: NotificationCoordinator | None = getattr(
        request.app.state, "notification_coordinator", None
    )
    return WebhookService(dispatcher, coordinator)
