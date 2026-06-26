import time
import logging
from fastapi import APIRouter, Depends, status
from app.schemas.ticket import TicketAnalysisRequest, TicketAnalysisResponse
from app.services.rule_engine import RuleEngine
from app.services.gemini_service import GeminiService
from app.config import settings
from app.utils.logging import request_id_ctx, ticket_id_ctx

router = APIRouter()
logger = logging.getLogger("app.routers.tickets")

# Singleton rule engine instance
rule_engine = RuleEngine()

def get_gemini_service() -> GeminiService:
    """
    Dependency injection helper to retrieve configured Gemini service.
    """
    return GeminiService(api_key=settings.GEMINI_API_KEY)

@router.post(
    "/analyze-ticket",
    response_model=TicketAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze Support Ticket Complaint",
    description="Analyzes complaint messages against transaction histories. Operates deterministically with optional Gemini enhancement."
)
async def analyze_ticket(
    request: TicketAnalysisRequest,
    gemini_service: GeminiService = Depends(get_gemini_service)
) -> TicketAnalysisResponse:
    """
    Ingests and processes support complaints. Evaluates evidence, routes the case,
    and returns a structured compliance-checked audit analysis.
    """
    # Track the ticket_id in logging context
    ticket_id_ctx.set(request.ticket_id)
    
    start_time = time.time()
    logger.info(f"Received ticket analysis request for ticket_id={request.ticket_id}")

    try:
        # Step 1: Run deterministic baseline rules
        baseline = rule_engine.generate_baseline(request)
        
        # Step 2: Attempt AI enhancement (will safely fall back to baseline if offline/keyless)
        final_response = await gemini_service.enhance_analysis(baseline, request)
        
        duration_ms = (time.time() - start_time) * 1000
        
        # Step 3: Structured audit logging
        extra_log_data = {
            "extra_fields": {
                "duration_ms": round(duration_ms, 2),
                "case_type": final_response.case_type.value,
                "severity": final_response.severity.value,
                "department": final_response.department.value,
                "verdict": final_response.evidence_verdict.value,
                "confidence": final_response.confidence,
                "relevant_transaction_id": final_response.relevant_transaction_id,
                "human_review_required": final_response.human_review_required
            }
        }
        logger.info(
            f"Ticket {request.ticket_id} processed successfully in {duration_ms:.2f}ms. "
            f"Verdict: {final_response.evidence_verdict.value}",
            extra=extra_log_data
        )
        
        return final_response

    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        logger.error(
            f"Exception occurred while processing ticket {request.ticket_id} after {duration_ms:.2f}ms: {str(e)}",
            exc_info=True
        )
        # Propagate exception to global handler which returns 500 cleanly
        raise e
