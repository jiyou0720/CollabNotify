"""FastAPI exception-to-response mapping."""

import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import PayloadValidationError, UnsupportedEventError
from app.schemas.response import ErrorResponse, WebhookResponse

logger = logging.getLogger(__name__)


def register_exception_handlers(application: FastAPI) -> None:
    """Register all global API exception handlers."""

    @application.exception_handler(HTTPException)
    async def _handle_http_exception(
        _request: Request, exception: HTTPException
    ) -> JSONResponse:
        message = str(exception.detail or "HTTP request failed.")
        return JSONResponse(
            status_code=exception.status_code,
            content=ErrorResponse(error=message).model_dump(),
            headers=exception.headers,
        )

    @application.exception_handler(RequestValidationError)
    async def _handle_request_validation(
        _request: Request, exception: RequestValidationError
    ) -> JSONResponse:
        logger.warning(
            "Request validation failed: error_count=%s",
            len(exception.errors()),
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(error="Invalid request.").model_dump(),
        )

    @application.exception_handler(PayloadValidationError)
    async def _handle_payload_validation(
        _request: Request, exception: PayloadValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(error=str(exception)).model_dump(),
        )

    @application.exception_handler(UnsupportedEventError)
    async def _handle_unsupported_event(
        _request: Request, _exception: UnsupportedEventError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=WebhookResponse(message="Ignored event.").model_dump(),
        )

    @application.exception_handler(Exception)
    async def _handle_unexpected_exception(
        request: Request, exception: Exception
    ) -> JSONResponse:
        logger.exception(
            "Unhandled API error: method=%s path=%s",
            request.method,
            request.url.path,
            exc_info=(type(exception), exception, exception.__traceback__),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(error="Internal server error.").model_dump(),
        )
