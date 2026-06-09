import pytest
from datetime import date
from src.schemas import PolicyConfig, BenefitRule, ClaimEvent
from src.engine import AdjudicationEngine

@pytest.fixture
def sample_policy():
    return PolicyConfig(
        plan_name="Test Plan",
        annual_aggregate_limit=10000.0,
        chronic_waiting_period_months=6,
        benefits=[
            BenefitRule(
                benefit_name="Consultation",
                annual_sub_limit=1000.0,
                in_network_deductible=50.0,
                in_network_coinsurance=0.1,
                out_of_network_deductible=100.0,
                out_of_network_coinsurance=0.3,
                is_covered_out_of_network=True
            )
        ]
    )

def test_in_network_claim_calculation(sample_policy):
    engine = AdjudicationEngine(sample_policy, date(2025, 1, 1))
    
    claim = ClaimEvent(
        claim_id="T1",
        service_date=date(2025, 2, 1),
        benefit="Consultation",
        network="In-Network",
        billed_amount=250.0,
        pre_auth_obtained=True,
        diagnosis_note="Test",
        is_chronic_related=False
    )
    
    row = engine.adjudicate_single_claim(claim)
    
    assert row.eligible_amount == 250.0
    assert row.deductible_applied == 50.0
    # Remaining eligible: 200. Coinsurance is 10%: 20. Insurer pays: 180.
    assert row.insurer_paid == 180.0
    assert row.member_paid == 70.0  # 50 deductible + 20 coinsurance
