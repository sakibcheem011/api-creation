from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

# --- Enumerations ---

class CaseType(str, Enum):
    WRONG_TRANSFER = "wrong_transfer"
    PAYMENT_FAILED = "payment_failed"
    REFUND_REQUEST = "refund_request"
    DUPLICATE_PAYMENT = "duplicate_payment"
    MERCHANT_SETTLEMENT_DELAY = "merchant_settlement_delay"
    AGENT_CASH_IN_ISSUE = "agent_cash_in_issue"
    PHISHING_OR_SOCIAL_ENGINEERING = "phishing_or_social_engineering"
    OTHER = "other"

class Department(str, Enum):
    CUSTOMER_SUPPORT = "customer_support"
    DISPUTE_RESOLUTION = "dispute_resolution"
    PAYMENTS_OPS = "payments_ops"
    MERCHANT_OPERATIONS = "merchant_operations"
    AGENT_OPERATIONS = "agent_operations"
    FRAUD_RISK = "fraud_risk"

class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class EvidenceVerdict(str, Enum):
    CONSISTENT = "consistent"
    INCONSISTENT = "inconsistent"
    INSUFFICIENT_DATA = "insufficient_data"

# --- Request Models ---

class TransactionHistoryItem(BaseModel):
    transaction_id: str = Field(..., description="Unique transaction reference code")
    timestamp: str = Field(..., description="ISO 8601 formatted transaction timestamp")
    type: str = Field(..., description="Transaction action type (e.g. transfer, cash_in, cash_out, payment)")
    amount: float = Field(..., description="Transaction monetary amount")
    counterparty: str = Field(..., description="Receiver/Sender identifier")
    status: str = Field(..., description="Transaction state (e.g., successful, failed, pending)")

class TicketAnalysisRequest(BaseModel):
    ticket_id: str = Field(..., description="Unique identifier for the incoming ticket")
    complaint: str = Field(..., description="Raw support text/message written by the user")
    language: str = Field(..., description="ISO language code or parsed language name")
    channel: str = Field(..., description="Ingestion channel (e.g. email, in_app, whatsapp, sms)")
    user_type: str = Field(..., description="Segmentation user type (e.g., retail_customer, agent, merchant)")
    campaign_context: str = Field(..., description="Marketing or special status campaign references")
    transaction_history: List[TransactionHistoryItem] = Field(
        default_factory=list, 
        description="List of transaction records linked to the user account history"
    )
    metadata: Optional[dict] = Field(
        default=None, 
        description="Optional unstructured dictionary container for additional metadata context"
    )

# --- Response Models ---

class TicketAnalysisResponse(BaseModel):
    ticket_id: str = Field(..., description="Reference ticket_id matching input")
    relevant_transaction_id: Optional[str] = Field(None, description="Matched transaction_id or null if none identified")
    evidence_verdict: EvidenceVerdict = Field(..., description="Integrity assessment of complaint claim vs transaction facts")
    case_type: CaseType = Field(..., description="Categorized nature of the complaint ticket")
    severity: Severity = Field(..., description="Calculated ticket criticality")
    department: Department = Field(..., description="Target routing queue")
    agent_summary: str = Field(..., description="Structured audit summary of the case and matching evidence")
    recommended_next_action: str = Field(..., description="Step-by-step guidance for the customer service agent")
    customer_reply: str = Field(..., description="Safe drafted reply ready to send directly to the customer")
    human_review_required: bool = Field(..., description="Flag indicating if workflow requires manual validation")
    confidence: float = Field(..., description="Confidence score representing match accuracy (range 0.0 to 1.0)")
    reason_codes: List[str] = Field(..., description="List of generated logical reasons/tags explaining decisions")
