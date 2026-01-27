"""
Standardized error handling middleware for FastAPI
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from fastapi.middleware.cors import CORSMiddleware
import structlog

logger = structlog.get_logger()


class APIError(Exception):
    """Base exception for API errors"""
    def __init__(self, message: str, status_code: int = 400, details: dict | None = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


def _add_cors_headers(response: JSONResponse, request: Request) -> JSONResponse:
    """Add CORS headers to error responses"""
    from ..core.config import get_cors_origins
    
    origins = get_cors_origins()
    origin = request.headers.get("origin")
    
    # If allowing all origins or origin is in allowed list
    if origins == ["*"] or (origin and origin in origins):
        response.headers["Access-Control-Allow-Origin"] = origin if origin else "*"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Expose-Headers"] = "*"
    
    return response


async def error_handler(request: Request, exc: Exception):
    """
    Global error handler for all exceptions.
    Returns standardized error response format with CORS headers.
    """
    # Log the error
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        error_type=type(exc).__name__,
        exc_info=True
    )
    
    # Handle specific exception types
    if isinstance(exc, APIError):
        response = JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.message,
                "details": exc.details,
                "path": request.url.path
            }
        )
        return _add_cors_headers(response, request)
    
    if isinstance(exc, RequestValidationError):
        response = JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Validation error",
                "details": exc.errors(),
                "path": request.url.path
            }
        )
        return _add_cors_headers(response, request)
    
    if isinstance(exc, SQLAlchemyError):
        logger.error("Database error", error=str(exc), exc_info=True)
        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Database error",
                "details": {"message": "An error occurred while processing your request"},
                "path": request.url.path
            }
        )
        return _add_cors_headers(response, request)
    
    # Generic error handler
    response = JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "details": {"message": "An unexpected error occurred"},
            "path": request.url.path
        }
    )
    return _add_cors_headers(response, request)

