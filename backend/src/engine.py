from datetime import date
from dateutil.relativedelta import relativedelta
from typing import List, Dict
from src.schemas import PolicyConfig, ClaimEvent, AdjudicationRow, SettlementStatement

class AdjudicationEngine:
    def __init__(self, policy: PolicyConfig, inception_date: date):
        self.policy = policy
        self.inception_date = inception_date
        self.waiting_period_end = inception_date + relativedelta(months=policy.chronic_waiting_period_months)
        
        # State tracking balances
        self.aggregate_paid_so_far = 0.0
        self.sub_limits_paid_so_far: Dict[str, float] = {b.benefit_name: 0.0 for b in policy.benefits}

    def process_claims(self, claims: List[ClaimEvent], member_name: str) -> SettlementStatement:
        # Sort chronologically to maintain accurate state progression
        sorted_claims = sorted(claims, key=lambda x: x.service_date)
        rows = []
        
        for claim in sorted_claims:
            row = self.adjudicate_single_claim(claim)
            rows.append(row)
            
        return SettlementStatement(
            member_name=member_name,
            policy_year=f"{self.inception_date.year}",
            claims=rows,
            total_billed=round(sum(r.billed_amount for r in rows), 2),
            total_eligible=round(sum(r.eligible_amount for r in rows), 2),
            total_deductible=round(sum(r.deductible_applied for r in rows), 2),
            total_coinsurance=round(sum(r.coinsurance_applied for r in rows), 2),
            total_insurer_paid=round(sum(r.insurer_paid for r in rows), 2),
            total_member_paid=round(sum(r.member_paid for r in rows), 2)
        )

    def adjudicate_single_claim(self, claim: ClaimEvent) -> AdjudicationRow:
        steps = []
        billed = claim.billed_amount
        eligible = billed # Assume R&C based on criteria
        
        # 1. Match Policy Benefit
        rule = next((b for b in self.policy.benefits if b.benefit_name == claim.benefit), None)
        if not rule:
            return self._reject(claim, billed, "Benefit type not covered by policy.")

        # 2. Check Exclusion 4.2 (Chronic Waiting Period)
        if claim.is_chronic_related and claim.service_date < self.waiting_period_end:
            reason = f"Rejected: Claim for chronic condition occurred on {claim.service_date}, within the 6-month waiting period ending {self.waiting_period_end} (Exclusion 4.2)."
            return self._reject(claim, eligible, reason)

        # 3. Check Out-of-Network Coverage
        is_in_network = claim.network == "In-Network"
        if not is_in_network and not rule.is_covered_out_of_network:
            reason = f"Rejected: {claim.benefit} is explicitly not covered Out-of-Network."
            return self._reject(claim, eligible, reason)

        # 4. Apply Deductible (Outpatient Consultation Only)
        deductible = rule.in_network_deductible if is_in_network else rule.out_of_network_deductible
        if deductible > 0 and eligible > 0:
            deductible_applied = round(min(deductible, eligible), 2)
            eligible_after_ded = round(eligible - deductible_applied, 2)
            steps.append(f"Subtracted Deductible of {deductible_applied} AED.")
        else:
            deductible_applied = 0.0
            eligible_after_ded = eligible

        # 5. Calculate Coinsurance Base
        coins_pct = rule.in_network_coinsurance if is_in_network else rule.out_of_network_coinsurance
        coinsurance_applied = round(eligible_after_ded * coins_pct, 2)
        calculated_insurer_share = round(eligible_after_ded - coinsurance_applied, 2)

        # 6. Apply Non-PreAuth Penalty Rule (GC-3: Inpatient Reduction)
        penalty_reduction = 0.0
        if claim.benefit == "Inpatient & Surgery" and not claim.pre_auth_obtained:
            # Insurer reduces amount payable by 20%, member bears reduction
            penalty_reduction = round(calculated_insurer_share * 0.20, 2)
            calculated_insurer_share = round(calculated_insurer_share - penalty_reduction, 2)
            steps.append(f"Applied 20% Non-PreAuth Penalty (GC-3): Reduced insurer portion by {penalty_reduction:.2f} AED.")

        # 7. Apply Sub-limits and Aggregate Constraints (GC-2)
        final_insurer_paid = calculated_insurer_share
        
        if rule.annual_sub_limit > 0:
            remaining_sub_limit = round(rule.annual_sub_limit - self.sub_limits_paid_so_far[claim.benefit], 2)
            if final_insurer_paid > remaining_sub_limit:
                steps.append(f"Cap hit: Insurer payment capped at remaining sub-limit of {remaining_sub_limit:.2f} AED (Original: {final_insurer_paid:.2f} AED).")
                final_insurer_paid = remaining_sub_limit

        remaining_aggregate = round(self.policy.annual_aggregate_limit - self.aggregate_paid_so_far, 2)
            
        if final_insurer_paid > remaining_aggregate:
            steps.append(f"Cap hit: Insurer payment capped at remaining annual aggregate limit of {remaining_aggregate:.2f} AED.")
            final_insurer_paid = remaining_aggregate

        # Update running state metrics
        self.sub_limits_paid_so_far[claim.benefit] = round(self.sub_limits_paid_so_far[claim.benefit] + final_insurer_paid, 2)
        self.aggregate_paid_so_far = round(self.aggregate_paid_so_far + final_insurer_paid, 2)

        # Calculate absolute member total responsibility
        # Member pays: Deductible + Coinsurance + Penalty + Overaged Amount capped by limits
        member_paid = round(billed - final_insurer_paid, 2)

        decision_reason = " | ".join(steps) if steps else "Approved and processed under standard configurations."
        
        return AdjudicationRow(
            claim_id=claim.claim_id,
            billed_amount=billed,
            eligible_amount=eligible,
            deductible_applied=deductible_applied,
            coinsurance_applied=round(coinsurance_applied + penalty_reduction, 2),
            insurer_paid=final_insurer_paid,
            member_paid=member_paid,
            decision_reason=decision_reason
        )

    def _reject(self, claim: ClaimEvent, eligible: float, reason: str) -> AdjudicationRow:
        return AdjudicationRow(
            claim_id=claim.claim_id,
            billed_amount=claim.billed_amount,
            eligible_amount=eligible,
            deductible_applied=0.0,
            coinsurance_applied=0.0,
            insurer_paid=0.0,
            member_paid=claim.billed_amount,
            decision_reason=reason
        )
