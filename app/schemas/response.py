"""Common API response schemas."""

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Health-check response body."""

    model_config = ConfigDict(extra="forbid")

    status: str


class WebhookResponse(BaseModel):
    """Successful webhook receipt response."""

    model_config = ConfigDict(extra="forbid")

    success: bool = True
    message: str


class ErrorResponse(BaseModel):
    """Consistent API error response."""

    model_config = ConfigDict(extra="forbid")

    success: bool = False
    error: str
