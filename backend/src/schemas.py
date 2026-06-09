from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date

class BenefitRule(BaseModel):
    benefit_name: str
    annual_sub_limit: float
    is_sub_limit_within_aggregate: bool = False
    in_network_deductible: float = 0.0
    in_network_coinsurance: float  # e.g., 0.10 for 10%
    out_of_network_deductible: float = 0.0
    out_of_network_coinsurance: float
    is_covered_out_of_network: bool = True

class PolicyConfig(BaseModel):
    plan_name: str
    annual_aggregate_limit: float
    chronic_waiting_period_months: int
    benefits: List[BenefitRule]

class ClaimEvent(BaseModel):
    claim_id: str
    service_date: date
    benefit: str
    network: str # "In-Network" or "Out-Of-Network"
    billed_amount: float
    pre_auth_obtained: bool
    diagnosis_note: str
    is_chronic_related: bool

class AdjudicationRow(BaseModel):
    claim_id: str
    billed_amount: float
    eligible_amount: float
    deductible_applied: float
    coinsurance_applied: float
    insurer_paid: float
    member_paid: float
    decision_reason: str

class SettlementStatement(BaseModel):
    member_name: str
    policy_year: str
    claims: List[AdjudicationRow]
    total_billed: float
    total_eligible: float
    total_deductible: float
    total_coinsurance: float
    total_insurer_paid: float
    total_member_paid: float
