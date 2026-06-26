from app.schemas.ticket import CaseType, Department, Severity

class RoutingEngine:
    """
    Determines target routing department based on CaseType and Severity classifications.
    """

    def route_ticket(self, case_type: CaseType, severity: Severity) -> Department:
        """
        Calculates the appropriate department queue using structured prioritization.
        """
        # Critical severity or scams always go to fraud risk
        if case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING or severity == Severity.CRITICAL:
            return Department.FRAUD_RISK

        # Wrong transfers and double charges go to dispute resolution
        if case_type in [CaseType.WRONG_TRANSFER, CaseType.DUPLICATE_PAYMENT]:
            return Department.DISPUTE_RESOLUTION

        # Merchant settlement issues
        if case_type == CaseType.MERCHANT_SETTLEMENT_DELAY:
            return Department.MERCHANT_OPERATIONS

        # Agent cash-in issues
        if case_type == CaseType.AGENT_CASH_IN_ISSUE:
            return Department.AGENT_OPERATIONS

        # Payment failures and refund requests
        if case_type in [CaseType.PAYMENT_FAILED, CaseType.REFUND_REQUEST]:
            return Department.PAYMENTS_OPS

        # Default fallback
        return Department.CUSTOMER_SUPPORT
