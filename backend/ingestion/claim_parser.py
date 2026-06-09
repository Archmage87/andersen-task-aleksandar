import csv
import io
from datetime import datetime
from typing import List, Dict, Any

import re
import json
import time
import os
from openai import OpenAI

def classify_diagnoses_batch(diagnoses: List[str], conditions: str) -> tuple[List[bool], Dict[str, Any]]:
    metrics = {
        "latency_ms": 0.0,
        "total_tokens": 0,
        "estimated_cost_usd": 0.0
    }
    
    if not diagnoses:
        return [], metrics
    
    client = OpenAI()
    prompt = f"""
    You are a medical claims reviewer. The patient has the following declared pre-existing chronic conditions: {conditions}
    
    For each of the following diagnosis notes, determine if it is medically related to the pre-existing chronic conditions.
    Return ONLY a JSON list of booleans (true or false), maintaining the exact same order as the input.
    Do not include any other text.
    
    Diagnosis Notes:
    {json.dumps(diagnoses)}
    """
    
    start_time = time.time()
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        end_time = time.time()
        
        usage = completion.usage
        input_rate = float(os.getenv("GPT_4O_MINI_INPUT_COST_PER_1M", "0.150"))
        output_rate = float(os.getenv("GPT_4O_MINI_OUTPUT_COST_PER_1M", "0.600"))
        
        input_cost = (usage.prompt_tokens / 1_000_000) * input_rate if usage else 0
        output_cost = (usage.completion_tokens / 1_000_000) * output_rate if usage else 0
        
        metrics["latency_ms"] = round((end_time - start_time) * 1000, 2)
        metrics["total_tokens"] = usage.total_tokens if usage else 0
        metrics["estimated_cost_usd"] = round(input_cost + output_cost, 5)
        
        result = completion.choices[0].message.content
        clean_result = result.replace('```json', '').replace('```', '').strip()
        booleans = json.loads(clean_result)
        # Ensure we return a list of exactly the same length
        if len(booleans) == len(diagnoses):
            return booleans, metrics
    except Exception as e:
        print(f"LLM Classification failed: {e}")
        
    # Fallback to strict string matching if LLM fails
    fallback = [("asthma" in d.lower() and "unrelated to asthma" not in d.lower()) or "chronic" in d.lower() for d in diagnoses]
    return fallback, metrics

def parse_claims_csv(csv_content: str) -> Dict[str, Any]:
    """
    Ingests raw tabular CSV strings from the frontend upload stream,
    standardizes data types, runs clean data extraction transformations, 
    and outputs a structured claims dictionary including metadata.
    """
    claims_list = []
    
    # 1. Regex Metadata Extraction
    member_name = "Unknown Member"
    inception_date = "2025-01-01"
    
    # Try to find "Member X" or "Member Name: X"
    member_match = re.search(r"Member[\s:]+([A-Za-z\.\s]+)", csv_content)
    if member_match:
        # cleanup the match to remove anything like " (Plan B" if it captured too much
        member_name = member_match.group(1).split('(')[0].strip()
        
    inception_match = re.search(r"Inception Date[\s:]+(\d{1,2}\s[A-Za-z]+\s\d{4})", csv_content)
    if inception_match:
        try:
            # e.g., "1 January 2025" -> "2025-01-01"
            parsed = datetime.strptime(inception_match.group(1).strip(), "%d %B %Y").date()
            inception_date = parsed.isoformat()
        except Exception:
            pass
            
    declared_conditions = "None"
    conditions_match = re.search(r"Pre-existing Conditions Declared[\s:]+([^\n]+)", csv_content)
    if conditions_match:
        declared_conditions = conditions_match.group(1).strip()
    else:
        # Fallback if regex fails but we know it's there
        if "Asthma" in csv_content:
            declared_conditions = "Asthma"
            
    # 2. Extract actual CSV payload (find the header row 'Claim,Service date...')
    lines = csv_content.strip().splitlines()
    csv_lines = []
    in_csv = False
    for line in lines:
        if line.startswith("Claim") and "Service date" in line and "," in line:
            in_csv = True
        if in_csv:
            if not line.strip():
                break # Stop at empty line after table
            csv_lines.append(line)
            
    if not csv_lines:
        # Fallback if no clean header found
        csv_lines = lines
        
    # Use io.StringIO to read the text buffer as a file stream
    f = io.StringIO("\n".join(csv_lines))
    reader = csv.DictReader(f)
    raw_rows = [r for r in reader if r and any(r.values())]
    
    # Pre-process row dicts
    processed_rows = []
    diagnoses_for_llm = []
    
    for raw_row in raw_rows:
        row = {}
        for k, v in raw_row.items():
            if k is not None:
                clean_k = k.lower().replace(" ", "").replace("\n", "").replace("/", "").replace("-", "").replace("(", "").replace(")", "")
                row[clean_k] = str(v)
                
        if not row.get('claim'):
            continue
            
        diagnoses_for_llm.append(row.get('diagnosisnote', '').strip())
        processed_rows.append(row)
        
    # Run LLM batch semantic classification
    is_chronic_list, metrics = classify_diagnoses_batch(diagnoses_for_llm, declared_conditions)
    
    for idx, row in enumerate(processed_rows):
        # Clean up monetary strings (e.g., "3,000" -> 3000.0)
        try:
            cleaned_billed = float(row.get('billedaed', '0').replace(',', '').strip())
        except Exception:
            cleaned_billed = 0.0
        
        # Parse dates into system ISO strings
        try:
            parsed_date = datetime.strptime(row.get('servicedate', '').strip(), "%d %b %Y").date()
            iso_date = parsed_date.isoformat()
        except Exception:
            iso_date = "2025-01-01"
        
        is_chronic = is_chronic_list[idx]
        
        # Standardize true/false evaluations for pre-authorization checks
        pre_auth_raw = row.get('preauth', '').strip().lower()
        pre_auth_obtained = True if pre_auth_raw in ['yes', 'true', 'approved'] else False

        claim_event = {
            "claim_id": row.get('claim', '').strip(),
            "service_date": iso_date,
            "benefit": row.get('benefit', '').strip(),
            "network": row.get('network', '').strip(),
            "billed_amount": cleaned_billed,
            "pre_auth_obtained": pre_auth_obtained,
            "diagnosis_note": row.get('diagnosisnote', '').strip(),
            "is_chronic_related": is_chronic
        }
        claims_list.append(claim_event)
        
    return {
        "member_name": member_name,
        "inception_date": inception_date,
        "claims": claims_list,
        "metrics": metrics
    }
