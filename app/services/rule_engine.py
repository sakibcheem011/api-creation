from typing import List, Optional, Tuple
from app.schemas.ticket import (
    TicketAnalysisRequest, 
    TicketAnalysisResponse, 
    CaseType, 
    Severity, 
    Department, 
    EvidenceVerdict,
    TransactionHistoryItem
)
from app.services.evidence_engine import EvidenceEngine
from app.services.classification_engine import ClassificationEngine
from app.services.routing_engine import RoutingEngine
from app.services.safety_engine import SafetyEngine

class RuleEngine:
    """
    Orchestrator for the deterministic baseline analysis.
    Executes structural, logical, and safety rules without requiring LLM assistance.
    """
    def __init__(self):
        self.evidence_engine = EvidenceEngine()
        self.classification_engine = ClassificationEngine()
        self.routing_engine = RoutingEngine()
        self.safety_engine = SafetyEngine()

    def generate_baseline(self, request: TicketAnalysisRequest) -> TicketAnalysisResponse:
        """
        Executes rule-based flow to generate a fully populated TicketAnalysisResponse object.
        """
        complaint = request.complaint
        history = request.transaction_history

        # 1. Match Evidence Transaction
        matched_tx, confidence, verdict, match_codes = self.evidence_engine.match_transaction(
            complaint, history
        )

        # 2. Case Type Classification
        case_type, classification_codes = self.classification_engine.classify_case(complaint)

        # 3. Determine Severity
        severity = self.classification_engine.determine_severity(complaint, case_type, matched_tx)

        # 4. Routing Department
        department = self.routing_engine.route_ticket(case_type, severity)

        # Combine matching and classification codes to populate initial reason codes
        reason_codes = list(set(match_codes + classification_codes))

        # 5. Determine Human Review Required
        # Trigger human review on critical/high issues, inconsistent evidence, or low confidence.
        human_review_required = False
        if severity in [Severity.CRITICAL, Severity.HIGH]:
            human_review_required = True
            reason_codes.append("high_severity_escalation")
        if verdict != EvidenceVerdict.CONSISTENT:
            human_review_required = True
            reason_codes.append("evidence_mismatch_escalation")
        if confidence < 0.60:
            human_review_required = True
            reason_codes.append("low_confidence_escalation")
        if "multiple_candidates" in reason_codes:
            human_review_required = True

        # 6. Generate Rule-based summary and actions
        agent_summary = self._generate_agent_summary(request, case_type, matched_tx, verdict)
        recommended_next_action = self._generate_next_action(case_type, matched_tx, verdict)
        raw_customer_reply = self._generate_customer_reply(case_type, matched_tx, verdict)

        # 7. Apply Safety Audit Filter to Reply
        customer_reply, sanitized, safety_codes = self.safety_engine.audit_reply(raw_customer_reply)
        if sanitized:
            reason_codes.extend(safety_codes)

        return TicketAnalysisResponse(
            ticket_id=request.ticket_id,
            relevant_transaction_id=matched_tx.transaction_id if matched_tx else None,
            evidence_verdict=verdict,
            case_type=case_type,
            severity=severity,
            department=department,
            agent_summary=agent_summary,
            recommended_next_action=recommended_next_action,
            customer_reply=customer_reply,
            human_review_required=human_review_required,
            confidence=round(confidence, 2),
            reason_codes=sorted(list(set(reason_codes)))
        )

    def _generate_agent_summary(
        self, 
        request: TicketAnalysisRequest, 
        case_type: CaseType, 
        tx: Optional[TransactionHistoryItem], 
        verdict: EvidenceVerdict
    ) -> str:
        """
        Builds a structured baseline summary for agents.
        """
        header = f"Ticket {request.ticket_id} ({request.language}) via {request.channel}. "
        body = f"Classified case: {case_type.value}. "
        
        if tx:
            tx_info = (
                f"Matched Transaction {tx.transaction_id} (Amount: {tx.amount}, "
                f"Type: {tx.type}, Status: {tx.status}, Counterparty: {tx.counterparty}). "
            )
            evidence_info = f"Evidence verdict is {verdict.value}."
            return header + body + tx_info + evidence_info
        else:
            return header + body + "No matching transaction identified from history. Evidence verdict is insufficient_data."

    def _generate_next_action(self, case_type: CaseType, tx: Optional[TransactionHistoryItem], verdict: EvidenceVerdict) -> str:
        """
        Provides action advice based on CaseType and Match.
        """
        if case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
            return "Immediately suspend suspect credentials, freeze suspicious transfers, and escalate to Fraud Risk."
        if case_type == CaseType.WRONG_TRANSFER:
            return "Verify recipient wallet validity. Request dispute consent form from the sender."
        if case_type == CaseType.DUPLICATE_PAYMENT:
            return "Check gateway settlement logs. Confirm double-debit, and request reversing the secondary transaction."
        if case_type == CaseType.MERCHANT_SETTLEMENT_DELAY:
            return "Check settlements batch processing logs. Contact Merchant Ops to manually sync ledger."
        if case_type == CaseType.AGENT_CASH_IN_ISSUE:
            return "Validate Agent point transaction status. Coordinate with Agent Network Operations."
        
        if tx and tx.status.lower() == "failed":
            return "Initiate standard payment failure investigation. Check upstream network provider status."
            
        return "Review customer account details, search logs for error trace, and contact customer for more details."

    def _generate_customer_reply(self, case_type: CaseType, tx: Optional[TransactionHistoryItem], verdict: EvidenceVerdict) -> str:
        """
        Drafts a standard safety-compliant baseline reply for customers.
        """
        base = "Dear Customer, thank you for reaching out to us. "
        
        if case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
            return base + "We take security issues very seriously. We have blocked unauthorized attempts and routed this ticket to our Fraud unit. For your safety, do not share your PIN/OTP with anyone."
        
        if case_type == CaseType.WRONG_TRANSFER:
            return base + "We have recorded your report about funds sent to the wrong account. Our team is investigating the target account and will try to resolve this soon."
            
        if tx and tx.status.lower() == "failed":
            return base + f"We see that your transaction {tx.transaction_id} for {tx.amount} has failed. The system will reverse the balance if deducted. We apologize for the inconvenience."
            
        return base + "We have registered your ticket. Our customer service team is looking into the details of your inquiry. We will contact you once the investigation completes."
