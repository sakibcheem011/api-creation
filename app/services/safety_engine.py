import re
from typing import Tuple, List

class SafetyEngine:
    """
    Scans generated customer replies for policy violations.
    Sanitizes or rewrites the text if any forbidden terms or patterns are found.
    """

    # PIN/OTP/Password checks
    PATTERN_SECRETS = re.compile(
        r'\b(pin|otp|password|passcode|one-time password|verification code)\b|'
        r'(পিন|ওটিপি|পাসওয়ার্ড|পাসকোড)', 
        re.IGNORECASE
    )

    # Reversal/Refund promises checks
    PATTERN_PROMISES = re.compile(
        r'\b(promise\b.*\b(refund|reverse|reversal|recover)|'
        r'will refund|guarantee.*refund|refund you|reversal guaranteed|'
        r'recover your account|account recovery guaranteed)\b|'
        r'(ফেরত দিব|ফেরত দেব|রিফান্ড করব|রিকভার করে দেব|ফেরত দিয়ে দেব)', 
        re.IGNORECASE
    )

    # Unofficial contacts checks (detects external phone numbers or URLs)
    # Allows official: 16247, support@novaforge.com, https://novaforge.com
    PATTERN_CONTACTS = re.compile(
        r'\b(?:\+?88)?01[3-9]\d{8}\b|'                      # Mobile numbers
        r'\bhttps?://(?!novaforge\.com)[a-zA-Z0-9./-]+\b|' # Untrusted URLs
        r'\b[a-zA-Z0-9._%+-]+@(?!novaforge\.com)[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b' # Untrusted emails
    )

    def audit_reply(self, reply: str) -> Tuple[str, bool, List[str]]:
        """
        Audits and sanitizes the customer reply.
        Returns:
            - The sanitized/original reply text
            - A boolean flag indicating if sanitization was applied
            - List of safety violation tags
        """
        sanitized = reply
        violation_applied = False
        violations = []

        # Check for password/PIN/OTP requests
        if self.PATTERN_SECRETS.search(reply):
            violations.append("safety_secret_request_attempt")
            violation_applied = True
            # Sanitize: Remove or replace the sentence requesting secret
            sanitized = re.sub(
                r'([^.!?]*\b(pin|otp|password|passcode|পিন|ওটিপি|পাসওয়ার্ড)\b[^.!?]*[.!?]?)',
                ' Please note that our team will NEVER ask for your PIN, OTP, or password. Keep this secret.',
                sanitized,
                flags=re.IGNORECASE
            )

        # Check for financial promises (Refunds, Reversals, Account recovery)
        if self.PATTERN_PROMISES.search(reply):
            violations.append("safety_unauthorized_promise_attempt")
            violation_applied = True
            # Sanitize: Replace refund promises with a neutral dispute check message
            sanitized = re.sub(
                r'([^.!?]*(will refund|promise|guarantee|ফেরত দিব|রিফান্ড|রিকভার)[^.!?]*[.!?]?)',
                ' Your dispute has been registered and is under review. The final resolution will be communicated once the investigation completes.',
                sanitized,
                flags=re.IGNORECASE
            )

        # Check for external unofficial contact details
        if self.PATTERN_CONTACTS.search(reply):
            violations.append("safety_unofficial_contact_attempt")
            violation_applied = True
            # Sanitize: Replace external links/phones with official contact info
            sanitized = self.PATTERN_CONTACTS.sub("our official channel support@novaforge.com (or dial 16247)", sanitized)

        # Double check if sanitization made the text messy or still contains violations.
        # If it still contains violations, completely replace it with a fail-safe fallback reply template.
        if violation_applied and (
            self.PATTERN_SECRETS.search(sanitized) or 
            self.PATTERN_PROMISES.search(sanitized) or 
            self.PATTERN_CONTACTS.search(sanitized)
        ):
            sanitized = (
                "Thank you for reaching out. We have logged your complaint and matching transactions. "
                "Our dispute team is investigating this issue. For safety, please do not share your PIN/OTP "
                "with anyone. You can trace this status directly in the app or contact support at support@novaforge.com."
            )
            violations.append("safety_hard_fallback_triggered")

        return sanitized.strip(), violation_applied, violations
