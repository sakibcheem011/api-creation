import re
from typing import Tuple, List, Optional
from app.schemas.ticket import CaseType, Severity, TransactionHistoryItem

class ClassificationEngine:
    """
    Classifies complaint case types and evaluates severity using linguistic signals
    and financial thresholds, supporting English, Bangla, and Banglish.
    """

    # Keyword maps supporting multiple languages/phrasing
    KEYWORDS_WRONG_TRANSFER = [
        "wrong transfer", "wrong number", "vul number", "vul transfer", 
        "mistake transfer", "ভুল নাম্বার", "ভুল নম্বর", "ভুল করে", "ভুল পাঠান",
        "vul kore", "bhul kore", "vul send"
    ]
    
    KEYWORDS_PHISHING = [
        "scam", "phishing", "fraud", "hacked", "stole", "lured", "prize", "lottery",
        "pin change", "otp change", "code send", "win lottery", "প্রতারণা", "হ্যাক",
        "লটারি", "fraudster", "scammer", "threaten", "threatening"
    ]

    KEYWORDS_SETTLEMENT = [
        "settlement", "merchant wallet", "settle", "settled", "merchant delay",
        "সেটেলমেন্ট", "মার্চেন্ট সেটেল", "settlement delay"
    ]

    KEYWORDS_CASH_IN = [
        "agent cash", "cash in", "cashin", "এজেন্ট", "ক্যাশ ইন", "ক্যাশইন"
    ]

    KEYWORDS_DUPLICATE = [
        "duplicate", "twice", "double debit", "double charge", "double payment",
        "দুইবার", "২ বার", "২বার", "দুই বার"
    ]

    KEYWORDS_REFUND = [
        "refund", "return money", "reversal", "টাকা ফেরত", "ফেরত চাই", "ফেরত দিন"
    ]

    KEYWORDS_FAILED = [
        "failed", "fail", "declined", "error", "stuck", "not received", "didn't receive",
        "cut but not", "ব্যর্থ", "টাকা কেটেছে", "টাকা কেটে", "টাকা কাটে"
    ]

    def classify_case(self, complaint: str) -> Tuple[CaseType, List[str]]:
        """
        Scans complaint text and returns the classified CaseType and associated reason codes.
        """
        complaint_lower = complaint.lower()
        reasons = []

        if any(kw in complaint_lower for kw in self.KEYWORDS_PHISHING):
            reasons.append("phishing_detected")
            return CaseType.PHISHING_OR_SOCIAL_ENGINEERING, reasons
            
        if any(kw in complaint_lower for kw in self.KEYWORDS_WRONG_TRANSFER):
            reasons.append("wrong_transfer")
            return CaseType.WRONG_TRANSFER, reasons

        if any(kw in complaint_lower for kw in self.KEYWORDS_DUPLICATE):
            reasons.append("duplicate_payment")
            return CaseType.DUPLICATE_PAYMENT, reasons

        if any(kw in complaint_lower for kw in self.KEYWORDS_SETTLEMENT):
            reasons.append("merchant_delay")
            return CaseType.MERCHANT_SETTLEMENT_DELAY, reasons

        if any(kw in complaint_lower for kw in self.KEYWORDS_CASH_IN):
            reasons.append("agent_cash_in_issue")
            return CaseType.AGENT_CASH_IN_ISSUE, reasons

        if any(kw in complaint_lower for kw in self.KEYWORDS_REFUND):
            reasons.append("refund_request")
            return CaseType.REFUND_REQUEST, reasons

        if any(kw in complaint_lower for kw in self.KEYWORDS_FAILED):
            reasons.append("payment_failed")
            return CaseType.PAYMENT_FAILED, reasons

        return CaseType.OTHER, ["other_case"]

    def determine_severity(
        self, 
        complaint: str, 
        case_type: CaseType, 
        matched_tx: Optional[TransactionHistoryItem]
    ) -> Severity:
        """
        Determines complaint severity.
        Critical: Phishing, or very high transactions (> 10000), or legal/police threats.
        High: Wrong transfer, duplicate payments, or amounts > 2000, or urgent keywords.
        Medium: Failed payments, refunds, settlements, agent cash ins.
        Low: Small amounts (< 100) or default unspecified queries.
        """
        complaint_lower = complaint.lower()
        amount = matched_tx.amount if matched_tx else 0.0

        # Critical triggers
        if case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
            return Severity.CRITICAL
            
        if amount >= 10000:
            return Severity.CRITICAL
            
        if any(kw in complaint_lower for kw in ["police", "court", "legal", "lawyer", "case file"]):
            return Severity.CRITICAL

        # High triggers
        if case_type in [CaseType.WRONG_TRANSFER, CaseType.DUPLICATE_PAYMENT]:
            return Severity.HIGH
            
        if amount >= 2000:
            return Severity.HIGH
            
        if any(kw in complaint_lower for kw in ["urgent", "immediately", "right now", "emergency", "তাড়াতাড়ি", "জরুরী"]):
            return Severity.HIGH

        # Medium defaults
        if case_type in [CaseType.PAYMENT_FAILED, CaseType.REFUND_REQUEST, CaseType.MERCHANT_SETTLEMENT_DELAY, CaseType.AGENT_CASH_IN_ISSUE]:
            if amount < 100 and amount > 0:
                return Severity.LOW
            return Severity.MEDIUM

        # Low default
        return Severity.LOW
