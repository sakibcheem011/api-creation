import json
import logging
import google.generativeai as genai
from typing import Optional
from app.schemas.ticket import TicketAnalysisRequest, TicketAnalysisResponse
from app.services.safety_engine import SafetyEngine

logger = logging.getLogger(__name__)

class GeminiService:
    """
    Enriches the baseline ticket analysis using Google Gemini.
    Provides complete exception-safe fallbacks if Gemini is offline, misconfigured, or fails.
    """
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client_ready = False
        self.safety_engine = SafetyEngine()
        
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self.client_ready = True
                logger.info("Gemini API configured successfully in GeminiService.")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini SDK: {str(e)}")

    async def enhance_analysis(
        self, 
        baseline: TicketAnalysisResponse, 
        request: TicketAnalysisRequest
    ) -> TicketAnalysisResponse:
        """
        Attempts to enrich the baseline analysis with Gemini LLM.
        If any failure occurs, returns the baseline response unmodified.
        """
        if not self.client_ready:
            logger.info("Gemini API key not configured or client initialization failed. Returning rule-engine baseline.")
            return baseline

        # Format information about matching transactions
        tx_details = "None"
        if baseline.relevant_transaction_id:
            matching_tx = next(
                (tx for tx in request.transaction_history if tx.transaction_id == baseline.relevant_transaction_id), 
                None
            )
            if matching_tx:
                tx_details = json.dumps(matching_tx.model_dump(), indent=2)

        prompt = f"""
You are the core AI agent for "NovaForge Investigator", an automated banking complaint investigator.
Your job is to analyze this ticket and improve the baseline summary, action step, and customer response.

INPUT TICKET:
- ID: {request.ticket_id}
- Complaint Text: {request.complaint}
- Language: {request.language}
- User Type: {request.user_type}
- Channel: {request.channel}
- Relevant matched transaction: {tx_details}
- Calculated Case Type: {baseline.case_type.value}
- Calculated Severity: {baseline.severity.value}
- Evidence Verdict: {baseline.evidence_verdict.value}

CRITICAL CUSTOMER REPLY SAFETY RULES:
The generated `customer_reply` must NEVER:
1. Ask for credentials, credentials change, PIN, OTP, or passwords.
2. Promise refunds, transaction reversals, or account recovery.
3. Direct users to unofficial contacts (emails, phone numbers, external WhatsApp). Only direct them to standard official support channels like support@novaforge.com or hotline 16247.

Generate a JSON response containing exactly these three fields:
1. "agent_summary": A concise audit description for internal support agents, summarising why the complaint matches or doesn't match the transactions.
2. "recommended_next_action": Concrete steps the agent should follow.
3. "customer_reply": A safe, polite response in the same language as the complaint (or English if the language is unknown).

Return ONLY raw JSON, with no markdown code blocks or additional text:
{{
  "agent_summary": "...",
  "recommended_next_action": "...",
  "customer_reply": "..."
}}
"""
        try:
            # Using recommended gemini-1.5-flash for speed and structured instructions
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            # Configure structured JSON output request
            response = model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            content = response.text.strip()
            logger.debug(f"Gemini raw response: {content}")
            
            data = json.loads(content)
            
            # Extract fields with baseline fallbacks in case of partial JSON
            enhanced_summary = data.get("agent_summary", baseline.agent_summary)
            enhanced_action = data.get("recommended_next_action", baseline.recommended_next_action)
            enhanced_reply = data.get("customer_reply", baseline.customer_reply)
            
            # 8. Post-generate Safety Audit: Always process the Gemini output through our local safety filter
            clean_reply, sanitized, safety_codes = self.safety_engine.audit_reply(enhanced_reply)
            
            # Build new enriched response
            reason_codes = list(baseline.reason_codes)
            if sanitized:
                logger.warning("Gemini generated reply breached safety rules! Sanitization applied.")
                reason_codes.extend(safety_codes)
                reason_codes = sorted(list(set(reason_codes)))

            # Return the updated object
            return TicketAnalysisResponse(
                ticket_id=baseline.ticket_id,
                relevant_transaction_id=baseline.relevant_transaction_id,
                evidence_verdict=baseline.evidence_verdict,
                case_type=baseline.case_type,
                severity=baseline.severity,
                department=baseline.department,
                agent_summary=enhanced_summary,
                recommended_next_action=enhanced_action,
                customer_reply=clean_reply,
                human_review_required=baseline.human_review_required,
                confidence=baseline.confidence,
                reason_codes=reason_codes
            )

        except Exception as e:
            logger.error(f"Gemini API enrichment failed: {str(e)}. Falling back to deterministic rule-engine baseline.", exc_info=True)
            return baseline
