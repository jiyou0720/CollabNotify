"""Application-level API router composition."""

from fastapi import APIRouter

from app.api.confluence import router as confluence_router
from app.api.github import router as github_router
from app.api.health import router as health_router
from app.api.jira import router as jira_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(github_router)
api_router.include_router(jira_router)
api_router.include_router(confluence_router)
