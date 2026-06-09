import os
import time
import pdfplumber
from typing import Dict, Any
from pydantic import BaseModel
from openai import OpenAI
from src.schemas import PolicyConfig

def extract_text_and_tables_from_pdf(pdf_path: str) -> str:
    """
    Reads a PDF, extracts regular text, locates tables, 
    formats tables as clean Markdown, and combines everything.
    """
    full_content = []
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            full_content.append(f"--- PAGE {page_num} ---")
            
            # 1. Extract regular text
            text = page.extract_text()
            if text:
                full_content.append(text)
                
            # 2. Extract tables and format them as Markdown so the LLM retains column layout
            tables = page.extract_tables()
            for table in tables:
                full_content.append("\nExtracted Table Structural Layout:")
                for row in table:
                    # Clean None values and join as markdown row
                    cleaned_row = [str(cell) if cell is not None else "" for cell in row]
                    full_content.append("| " + " | ".join(cleaned_row) + " |")
                full_content.append("\n")
                
    return "\n".join(full_content)

def parse_policy_document(file_content: str) -> Dict[str, Any]:
    """
    Takes raw text from the ingested policy document, sends it to an LLM
    with a strict JsonSchema constraint, and outputs the exact PolicyConfig structure.
    """
    # Initialize client (uses OPENAI_API_KEY environment variable)
    client = OpenAI()
    
    prompt = f"""
    You are an expert insurance document engineering system. Your job is to analyze the following 
    Policy Wording document and extract all operational rules into a strict structured format.
    
    CRITICAL INSTRUCTIONS:
    1. Look carefully for overlapping sections, Endorsements, or General Conditions that override the main table.
    2. Read the whole document to check if sub-limits are altered by text at the back (e.g., Endorsement E1).
    3. Coinsurance values must be extracted as decimals (e.g., 10% = 0.10, 20% = 0.20, 0% = 0.00).
    4. If a benefit is explicitly stated as 'Not covered' in a specific network, set 'is_covered_out_of_network' to false.
    
    Policy Wording Text:
    \"\"\"{file_content}\"\"\"
    """

    # Enforce strict structured generation using the PolicyConfig Pydantic schema
    start_time = time.time()
    completion = client.beta.chat.completions.parse(
        model="gpt-4o",  # Or your chosen model variant
        messages=[
            {"role": "system", "content": "You extract perfect, auditable business rule configurations from raw policy texts."},
            {"role": "user", "content": prompt}
        ],
        response_format=PolicyConfig, # This forces the LLM to return data matching our exact Pydantic schema
    )
    end_time = time.time()
    
    # Calculate Observability Metrics
    usage = completion.usage
    input_rate = float(os.getenv("GPT_4O_INPUT_COST_PER_1M", "5.00"))
    output_rate = float(os.getenv("GPT_4O_OUTPUT_COST_PER_1M", "15.00"))
    
    input_cost = (usage.prompt_tokens / 1_000_000) * input_rate if usage else 0
    output_cost = (usage.completion_tokens / 1_000_000) * output_rate if usage else 0
    
    metrics = {
        "latency_ms": round((end_time - start_time) * 1000, 2),
        "total_tokens": usage.total_tokens if usage else 0,
        "estimated_cost_usd": round(input_cost + output_cost, 5)
    }
    
    # The output is natively validated against our backend schema contract
    structured_rules = completion.choices[0].message.parsed
    return {
        "rules": structured_rules.model_dump(),
        "metrics": metrics
    }
