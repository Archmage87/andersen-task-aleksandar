import os
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import json
from datetime import datetime
from pydantic import BaseModel
from openai import OpenAI
import pdfplumber

# Load environment variables
load_dotenv()

from ingestion.policy_parser import parse_policy_document, extract_text_and_tables_from_pdf
from ingestion.claim_parser import parse_claims_csv
from src.engine import AdjudicationEngine
from src.schemas import PolicyConfig, ClaimEvent

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global runtime context cache states
CURRENT_POLICY_RULES = None
CURRENT_CLAIM_SCENARIO = None
E2E_METRICS = {
    "total_policies_ingested": 0,
    "total_claims_processed": 0,
    "total_llm_latency_ms": 0.0,
    "total_llm_tokens": 0,
    "total_llm_cost_usd": 0.0
}

@app.post("/api/ingest-policy")
async def ingest_policy(file: UploadFile = File(...)):
    try:
        # Read the raw bytes out of the uploaded file
        file_bytes = await file.read()
        
        # If PDF, use pdfplumber, else decode string
        if file.filename.lower().endswith(".pdf"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
                
            try:
                text_content = extract_text_and_tables_from_pdf(tmp_path)
            finally:
                os.remove(tmp_path)
        else:
            text_content = file_bytes.decode("utf-8")
        
        # Process Flow 1: Dynamic structural analysis extraction via LLM
        extracted_data = parse_policy_document(text_content)
        
        global CURRENT_POLICY_RULES
        global E2E_METRICS
        
        CURRENT_POLICY_RULES = extracted_data["rules"]
        
        # Update Telemetry Stats
        E2E_METRICS["total_policies_ingested"] += 1
        E2E_METRICS["total_llm_latency_ms"] += extracted_data["metrics"]["latency_ms"]
        E2E_METRICS["total_llm_tokens"] += extracted_data["metrics"]["total_tokens"]
        E2E_METRICS["total_llm_cost_usd"] += extracted_data["metrics"]["estimated_cost_usd"]
        
        return {"status": "success", "rules": CURRENT_POLICY_RULES}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Policy ingestion failed: {str(e)}")

@app.post("/api/ingest-claims")
async def ingest_claims(file: UploadFile = File(...)):
    try:
        # Read the raw binary content of the uploaded file
        file_bytes = await file.read()
        
        # Check if the user uploaded the raw PDF directly
        if file.filename.lower().endswith(".pdf"):
            print("Processing Flow 2: Natively extracting text from raw Claims PDF with pdfplumber...")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name
            text_content = ""
            try:
                with pdfplumber.open(tmp_path) as pdf:
                    for page in pdf.pages:
                        extracted_text = page.extract_text()
                        if extracted_text:
                            text_content += extracted_text + "\n"
                        
                        # Use deterministic table extraction to get real comma-separated grids!
                        table = page.extract_table()
                        if table:
                            import csv, io
                            f = io.StringIO()
                            writer = csv.writer(f)
                            # Strip newlines from all cells to ensure DictReader keys match perfectly
                            clean_table = [
                                [str(cell).replace('\n', ' ').strip() if cell is not None else "" for cell in row]
                                for row in table
                            ]
                            writer.writerows(clean_table)
                            text_content += "\n" + f.getvalue() + "\n"
            finally:
                import os
                os.remove(tmp_path)
        else:
            # Fallback for plain text/CSV streams
            text_content = file_bytes.decode("utf-8")
        
        # Process Flow 2: Parse raw transactional tables deterministically
        parsed_claims_payload = parse_claims_csv(text_content)
        
        global CURRENT_CLAIM_SCENARIO
        CURRENT_CLAIM_SCENARIO = parsed_claims_payload
        
        # Update Telemetry Stats
        global E2E_METRICS
        E2E_METRICS["total_claims_processed"] += len(parsed_claims_payload["claims"])
        
        if "metrics" in parsed_claims_payload:
            E2E_METRICS["total_llm_latency_ms"] += parsed_claims_payload["metrics"].get("latency_ms", 0.0)
            E2E_METRICS["total_llm_tokens"] += parsed_claims_payload["metrics"].get("total_tokens", 0)
            E2E_METRICS["total_llm_cost_usd"] += parsed_claims_payload["metrics"].get("estimated_cost_usd", 0.0)
        
        return {"status": "success", "message": "Claims cached successfully."}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Claims ingestion failed: {str(e)}")

@app.post("/api/clear-data")
async def clear_data(type: str):
    global CURRENT_POLICY_RULES
    global CURRENT_CLAIM_SCENARIO
    
    if type == "policy":
        CURRENT_POLICY_RULES = None
        return {"status": "success", "message": "Policy data cleared."}
    elif type == "claims":
        CURRENT_CLAIM_SCENARIO = None
        return {"status": "success", "message": "Claims data cleared."}
    else:
        raise HTTPException(status_code=400, detail="Invalid data type to clear.")

@app.post("/api/adjudicate")
async def run_adjudication():
    if not CURRENT_POLICY_RULES or not CURRENT_CLAIM_SCENARIO:
        raise HTTPException(status_code=400, detail="State Error: Both policy and claims must be ingested first.")
    
    try:
        # Hydrate schemas directly from the active runtime storage cache
        policy_schema = PolicyConfig(**CURRENT_POLICY_RULES)
        claims_schema = [ClaimEvent(**c) for c in CURRENT_CLAIM_SCENARIO["claims"]]
        
        inception_date_str = CURRENT_CLAIM_SCENARIO.get("inception_date", "2025-01-01")
        inception_date = datetime.strptime(inception_date_str, "%Y-%m-%d").date()
        
        # Initialize engine with the dynamic policy rule values
        engine = AdjudicationEngine(policy=policy_schema, inception_date=inception_date)
        
        # Process and return the final mathematical results structure
        settlement_statement = engine.process_claims(claims=claims_schema, member_name=CURRENT_CLAIM_SCENARIO.get("member_name", "Unknown Member"))
        
        # Map the AdjudicationRow format to the frontend's LineItem format
        line_items = []
        id_to_service = {c["claim_id"]: c["benefit"] for c in CURRENT_CLAIM_SCENARIO["claims"]}
        
        for row in settlement_statement.claims:
            line_items.append({
                "service": id_to_service.get(row.claim_id, "Unknown Service"),
                "claimed_amount": row.billed_amount,
                "approved_amount": row.insurer_paid,
                "reason": row.decision_reason
            })
            
        return {
            "settlement_id": "ST-99884",
            "status": "APPROVED",
            "total_claimed": settlement_statement.total_billed,
            "total_approved": settlement_statement.total_insurer_paid,
            "total_patient_responsibility": settlement_statement.total_member_paid,
            "line_items": line_items
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Adjudication calculation failed: {str(e)}")

@app.get("/api/admin/metrics")
async def get_metrics():
    return E2E_METRICS

@app.post("/api/admin/metrics/reset")
async def reset_metrics():
    global E2E_METRICS
    E2E_METRICS = {
        "total_policies_ingested": 0,
        "total_claims_processed": 0,
        "total_llm_latency_ms": 0.0,
        "total_llm_tokens": 0,
        "total_llm_cost_usd": 0.0
    }
    return {"status": "success", "metrics": E2E_METRICS}
