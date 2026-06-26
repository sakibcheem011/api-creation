from fastapi import APIRouter

router = APIRouter()

@router.get(
    "/health", 
    summary="Health Check", 
    description="Validates that the service is running and healthy.",
    response_model=dict
)
async def health_check():
    """
    Standard health check endpoint.
    """
    return {"status": "ok"}
