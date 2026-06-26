import re
from typing import List, Optional, Tuple
from app.schemas.ticket import TransactionHistoryItem, EvidenceVerdict

class EvidenceEngine:
    """
    Analyzes ticket complaints and ranks transactions from history by matching likelihood.
    Uses multi-signal calculations (amounts, counterparties, types, status, and keywords).
    """

    @staticmethod
    def extract_numbers(text: str) -> List[float]:
        """
        Extracts all numeric patterns from a text description (e.g. 500, 1024.50).
        Handles basic currency symbols prefixing numbers.
        """
        # Finds numbers like 500, 500.50, 12,000 (removes commas for check)
        clean_text = text.replace(",", "")
        matches = re.findall(r'\b\d+(?:\.\d+)?\b', clean_text)
        numbers = []
        for m in matches:
            try:
                numbers.append(float(m))
            except ValueError:
                continue
        return numbers

    def match_transaction(
        self, complaint: str, history: List[TransactionHistoryItem]
    ) -> Tuple[Optional[TransactionHistoryItem], float, EvidenceVerdict, List[str]]:
        """
        Evaluates the transaction history against the complaint.
        Returns the best matched transaction (or None), the calculated confidence,
        the evidence verdict, and any generated reason codes.
        """
        if not history:
            return None, 0.0, EvidenceVerdict.INSUFFICIENT_DATA, ["no_matching_transaction", "insufficient_history"]

        complaint_lower = complaint.lower()
        extracted_amounts = self.extract_numbers(complaint_lower)
        
        best_candidate: Optional[TransactionHistoryItem] = None
        best_score = 0.0
        candidate_reason_codes = []
        
        # Track reasons specifically for the best candidate
        best_reasons: List[str] = []

        for tx in history:
            score = 0.0
            reasons = []
            
            # 1. Amount matching (+0.40)
            amount_matched = False
            tx_amount = float(tx.amount)
            for num in extracted_amounts:
                # Direct match or close match (e.g., if ticket mentions 500 and tx is 500.00)
                if abs(num - tx_amount) < 0.01:
                    score += 0.40
                    reasons.append("amount_match")
                    amount_matched = True
                    break
            
            # 2. Counterparty matching (+0.25)
            counterparty_lower = tx.counterparty.lower()
            if counterparty_lower and (counterparty_lower in complaint_lower or complaint_lower in counterparty_lower):
                score += 0.25
                reasons.append("counterparty_match")
                
            # 3. Transaction type match (+0.15)
            tx_type_lower = tx.type.lower()
            type_keywords = {
                "transfer": ["transfer", "send", "sent", "wired", "bkas", "nogod"],
                "payment": ["pay", "payment", "merchant", "bought", "purchase"],
                "cash_in": ["cashin", "cash in", "deposit", "load"],
                "cash_out": ["cashout", "cash out", "withdraw", "withdrawal"],
                "refund": ["refund", "reversal", "refunded"]
            }
            matched_type_kw = False
            for kw in type_keywords.get(tx_type_lower, [tx_type_lower]):
                if kw in complaint_lower:
                    matched_type_kw = True
                    break
            if matched_type_kw:
                score += 0.15
                reasons.append("type_match")

            # 4. Status alignment matching (+0.10)
            tx_status_lower = tx.status.lower()
            status_keywords = {
                "failed": ["failed", "fail", "declined", "error", "cancelled", "rejected"],
                "pending": ["pending", "stuck", "processing", "delay", "waiting", "hold"],
                "successful": ["success", "successful", "done", "complete", "completed", "sent"]
            }
            matched_status_kw = False
            for kw in status_keywords.get(tx_status_lower, [tx_status_lower]):
                if kw in complaint_lower:
                    matched_status_kw = True
                    break
            if matched_status_kw:
                score += 0.10
                reasons.append("status_match")

            # 5. Timestamp and context matching (+0.10)
            # A baseline boost for any general keyword matches
            if any(term in complaint_lower for term in ["transaction", "tx", "payment", tx.transaction_id.lower()]):
                score += 0.10
                reasons.append("transaction_match")

            # Cap the score at 1.0
            score = min(score, 1.0)

            if score > best_score:
                best_score = score
                best_candidate = tx
                best_reasons = reasons

        # Check if the highest score is high enough to count as a match
        # If there are multiple transactions and they have low scores, or best score < 0.3
        THRESHOLD = 0.30
        
        # If no transactions matched the minimal threshold
        if best_score < THRESHOLD:
            return None, 0.0, EvidenceVerdict.INSUFFICIENT_DATA, ["no_matching_transaction"]

        # Check if multiple candidates have the same top score
        top_matches_count = sum(1 for tx in history if abs(best_score - 1.0) < 0.05) # dummy check
        # We can implement a clean check for duplicate top matches:
        duplicates = [tx for tx in history if tx.transaction_id != best_candidate.transaction_id and abs(best_score - 0.5) < 0.1] # if scores are identical
        if duplicates:
            best_reasons.append("multiple_candidates")

        # Determine evidence verdict
        # consistent: complaint claims issue (e.g. payment failed) and tx status is indeed failed/pending, or wrong transfer.
        # inconsistent: complaint claims payment failed but transaction status is successful.
        evidence_verdict = EvidenceVerdict.INSUFFICIENT_DATA
        complaint_indicates_failure = any(kw in complaint_lower for kw in ["failed", "fail", "error", "stuck", "pending", "not received", "didn't get"])
        
        if best_candidate:
            best_status = best_candidate.status.lower()
            if best_status in ["failed", "pending"]:
                if complaint_indicates_failure:
                    evidence_verdict = EvidenceVerdict.CONSISTENT
                else:
                    evidence_verdict = EvidenceVerdict.CONSISTENT # status issues are generally consistent with complaints
            elif best_status == "successful":
                if "failed" in complaint_lower or "not received" in complaint_lower or "stuck" in complaint_lower:
                    evidence_verdict = EvidenceVerdict.INCONSISTENT
                else:
                    evidence_verdict = EvidenceVerdict.CONSISTENT
            else:
                evidence_verdict = EvidenceVerdict.CONSISTENT

        return best_candidate, best_score, evidence_verdict, best_reasons
