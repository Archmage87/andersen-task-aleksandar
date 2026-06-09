import json
from datetime import datetime
from src.schemas import PolicyConfig, ClaimEvent
from src.engine import AdjudicationEngine

def run_report(policy_path: str, claims_path: str):
    # Load JSON data
    with open(policy_path, 'r') as f:
        policy_data = json.load(f)
    with open(claims_path, 'r') as f:
        claims_data = json.load(f)
    
    # Parse into Pydantic models
    policy = PolicyConfig(**policy_data)
    inception_date = datetime.strptime(claims_data["inception_date"], "%Y-%m-%d").date()
    
    claims = [ClaimEvent(**c) for c in claims_data["claims"]]
    member_name = claims_data["member_name"]
    
    # Execute engine
    engine = AdjudicationEngine(policy, inception_date)
    settlement = engine.process_claims(claims, member_name)
    
    # Generate Output
    print(f"--- Settlement Report for {settlement.member_name} ---")
    print(f"Total Billed: {settlement.total_billed}")
    print(f"Total Eligible: {settlement.total_eligible}")
    print(f"Total Insurer Paid: {settlement.total_insurer_paid}")
    print(f"Total Member Paid: {settlement.total_member_paid}")
    print("\nLine Items:")
    for row in settlement.claims:
        print(f"  [{row.claim_id}] Billed: {row.billed_amount} -> Insurer Paid: {row.insurer_paid} | Reason: {row.decision_reason}")
    
    return settlement

if __name__ == "__main__":
    run_report("data/policy_rules.json", "data/claim_scenario.json")
