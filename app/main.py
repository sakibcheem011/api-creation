import logging
import time
import uuid
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.config import settings
from app.routers import health, tickets
from app.utils.logging import setup_logging, request_id_ctx, ticket_id_ctx

# Initialize logging configuration using settings
setup_logging(log_level=settings.ENVIRONMENT, app_env=settings.ENVIRONMENT)
logger = logging.getLogger("app.main")

# Initialize FastAPI App with automatic Swagger configurations
app = FastAPI(
    title="NovaForge Investigator API",
    description=(
        "Production-ready backend for the NovaForge Investigator hackathon. "
        "Automates banking complaint analysis by running rules and Gemini API analysis. "
        "Verifies complaints against transaction records, routes to appropriate queues, "
        "and checks drafted responses against safety rules."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware integration using settings list
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware to intercept request lifecycle, inject tracking identifiers, and log trace timing
@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):
    # Set request ID context
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request_id_ctx.set(request_id)
    # Clear ticket context for new request
    ticket_id_ctx.set("")
    
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Inject request id into headers
    response.headers["X-Request-ID"] = request_id
    
    duration = (time.time() - start_time) * 1000
    logger.debug(f"Request {request.method} {request.url.path} finished in {duration:.2f}ms")
    
    return response

# Global Exception Handler for Request Validation Errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(
        f"Validation error on {request.method} {request.url.path}: {exc.errors()}",
        extra={"extra_fields": {"validation_errors": exc.errors()}}
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Unprocessable Entity",
            "message": "The request payload failed structural validation checks.",
            "details": exc.errors()
        }
    )

# Global Exception Handler for generic internal server exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error encountered on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please contact system support."
        }
    )

# Register endpoints
app.include_router(health.router, tags=["System Health"])
app.include_router(tickets.router, tags=["Ticket Analysis"])

@app.get("/")
async def root():
    """
    Landing endpoint directing clients to Swagger docs.
    """
    return {
        "message": "Welcome to NovaForge Investigator API. Access API docs at /docs",
        "docs_url": "/docs"
    }
