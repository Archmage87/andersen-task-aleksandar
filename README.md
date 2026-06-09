# SecureHealth Claims Adjudication Engine

## Approach Overview
This system implements a fully decoupled **Deterministic Logic Engine** separate from data ingestion. The logic is entirely driven by rules extracted from the policy text (represented as a strictly validated JSON structure). LLM is used for anlysing semntic and non structured data, also for statement checking true/false to check if declarations match criteria.

I wasn't sure if claims will come as csv or pdf so i made it able to ingest pdf (task description said claims are in sheets which idnciate structured data, but they come as pdf. Having this in mind I put some work into claims parsing.)

**Workflow:**
1. **Extraction (LLM + PDFPlumber)**: The policy text is converted to Markdown (preserving structural tables via `pdfplumber`), and then sent to an LLM using strict **Structured Outputs** (Pydantic schemas) to extract limits, coinsurance rates, and overriding endorsements cleanly.
2. **Standardization (CSV)**: Raw claims are processed deterministically, cleaning dates, handling strings, and parsing chronic diagnosis flags into standard types. PDFs are first pre-processed. Also fuzzy comaprison for certain terms are implemented.
3. **Computation (Logic Engine)**: Declaration analysis (llm) and claim analysis (Deterministic logic engine). Claims are sorted chronologically. Running state balances for limits are maintained. Rules are evaluated hierarchically (Sub-limits vs. Aggregate vs. Endorsements), ensuring mathematical correctness and absolute auditability.

---

## Task Questions Answers

### Q1: Extraction (Physiotherapy Rates)
**Answer:** The member coinsurance is **10%** and the annual sub-limit is **AED 4,000**.
**Derivation:** While Section 2 (Table of Benefits) lists a 20% coinsurance and an AED 2,500 limit for Physiotherapy, **Endorsement E1** overrides this base table, reducing the In-Network coinsurance to 10% and increasing the sub-limit to AED 4,000.

### Q2: Extraction (Aggregate Limit)
**Answer:** The Annual Aggregate Limit is **AED 250,000**.
**Derivation:** Defined at the top of Section 2 (Table of Benefits).

### Q3: Single Rule (Claim C1 Calculation)
**Answer:** The Insurer pays **AED 225.00** and the Member pays **AED 75.00**.
**Steps:**
1. Billed Amount: AED 300.00
2. Apply Section 2 Deductible (Outpatient Consultation): AED 50.00
3. Remaining Eligible Amount: AED 250.00
4. Apply Section 2 Coinsurance (In-Network Outpatient): 10% of AED 250.00 = AED 25.00
5. Insurer pays: AED 250.00 - 25.00 = **AED 225.00**
6. Member pays: Deductible (50) + Coinsurance (25) = **AED 75.00**

### Q4: Exclusions
**Answer:** The following claims are not payable in full or in part:
- **C2 (Not payable in full):** Excluded under **Section 4.2 (Chronic waiting period)**. The service date (10 Mar) is within the 6-month waiting period from the Inception Date (1 Jan) for the declared Asthma condition.
- **C5 (Not payable in part):** Penalized under **General Condition 3 (GC-3: Pre-authorisation)**. Elective Inpatient treatment occurred without pre-authorisation, meaning the insurer reduces the amount payable by 20%, shifting an extra AED 3,600 liability to the member.
- **C6 (Not payable in full):** Excluded under **Section 2 Table of Benefits**. The Out-of-Network Prescribed Medication benefit is explicitly marked as "Not covered".

### Q5: Full Calculation Totals
**Answer:** 
Total Insurer Paid: **AED 17,640.00**
Total Member Paid: **AED 4,960.00**

**Derivations (Chronological State Traverse):**
- **C1:** Insurer pays 225, Member pays 75.
- **C2:** Insurer pays 0, Member pays 400 (Excluded: 4.2).
- **C3:** Insurer pays 315, Member pays 85 (AED 400 - 50 ded = 350; 10% coinsurance = 35. Chronic condition is now > 6 months old and payable).
- **C4:** Insurer pays 2,700, Member pays 300 (AED 3,000 billed. Endorsement E1 applies: no deductible, 10% coinsurance = 300).
- **C5:** Insurer pays 14,400, Member pays 3,600 (AED 18,000 billed. GC-3 applies: 20% penalty reduces insurer share from 18k to 14.4k).
- **C6:** Insurer pays 0, Member pays 500 (Out-of-Network pharmacy not covered).
*(Sum checks out: 17640 + 4960 = 22600 Total Billed).*

---

### Q6: Structured Settlement Generation

#### Human-Readable Table

| Claim | Service Date | Benefit | Billed (AED) | Deductible | Coinsurance / Penalty | Insurer Paid | Member Paid | Decision / Reason |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **C1** | 15 Feb 2025 | Outpatient | 300.00 | 50.00 | 25.00 | **225.00** | **75.00** | Subtracted Deductible of 50.0 AED. |
| **C2** | 10 Mar 2025 | Outpatient | 400.00 | 0.00 | 0.00 | **0.00** | **400.00** | Rejected: Claim for chronic condition within 6-month waiting period (Exclusion 4.2). |
| **C3** | 05 Aug 2025 | Outpatient | 400.00 | 50.00 | 35.00 | **315.00** | **85.00** | Subtracted Deductible of 50.0 AED. |
| **C4** | 12 Sep 2025 | Physiotherapy | 3000.00 | 0.00 | 300.00 | **2700.00** | **300.00** | Approved and processed under standard configurations. |
| **C5** | 03 Oct 2025 | Inpatient | 18000.00 | 0.00 | 3600.00 | **14400.00** | **3600.00** | Applied 20% Non-PreAuth Penalty (GC-3). |
| **C6** | 20 Nov 2025 | Pharmacy | 500.00 | 0.00 | 0.00 | **0.00** | **500.00** | Rejected: Explicitly not covered Out-of-Network. |
| **TOTALS**| | | **22600.00** | **100.00** | **3960.00** | **17640.00**| **4960.00** | |

#### Machine-Readable JSON
```json
{
  "member_name": "Mr. A. Karim",
  "policy_year": "2025",
  "total_billed": 22600.0,
  "total_eligible": 22600.0,
  "total_deductible": 100.0,
  "total_coinsurance": 3960.0,
  "total_insurer_paid": 17640.0,
  "total_member_paid": 4960.0,
  "claims": [
    {
      "claim_id": "C1",
      "billed_amount": 300.0,
      "eligible_amount": 300.0,
      "deductible_applied": 50.0,
      "coinsurance_applied": 25.0,
      "insurer_paid": 225.0,
      "member_paid": 75.0,
      "decision_reason": "Subtracted Deductible of 50.0 AED."
    },
    {
      "claim_id": "C2",
      "billed_amount": 400.0,
      "eligible_amount": 400.0,
      "deductible_applied": 0.0,
      "coinsurance_applied": 0.0,
      "insurer_paid": 0.0,
      "member_paid": 400.0,
      "decision_reason": "Rejected: Claim for chronic condition occurred on 2025-03-10, within the 6-month waiting period ending 2025-07-01 (Exclusion 4.2)."
    },
    {
      "claim_id": "C3",
      "billed_amount": 400.0,
      "eligible_amount": 400.0,
      "deductible_applied": 50.0,
      "coinsurance_applied": 35.0,
      "insurer_paid": 315.0,
      "member_paid": 85.0,
      "decision_reason": "Subtracted Deductible of 50.0 AED."
    },
    {
      "claim_id": "C4",
      "billed_amount": 3000.0,
      "eligible_amount": 3000.0,
      "deductible_applied": 0.0,
      "coinsurance_applied": 300.0,
      "insurer_paid": 2700.0,
      "member_paid": 300.0,
      "decision_reason": "Approved and processed under standard configurations."
    },
    {
      "claim_id": "C5",
      "billed_amount": 18000.0,
      "eligible_amount": 18000.0,
      "deductible_applied": 0.0,
      "coinsurance_applied": 3600.0,
      "insurer_paid": 14400.0,
      "member_paid": 3600.0,
      "decision_reason": "Applied 20% Non-PreAuth Penalty (GC-3): Reduced insurer portion by 3600.00 AED."
    },
    {
      "claim_id": "C6",
      "billed_amount": 500.0,
      "eligible_amount": 500.0,
      "deductible_applied": 0.0,
      "coinsurance_applied": 0.0,
      "insurer_paid": 0.0,
      "member_paid": 500.0,
      "decision_reason": "Rejected: Prescribed Medication (Pharmacy) is explicitly not covered Out-of-Network."
    }
  ]
}
```

---

## Why Naive Vector-Search/RAG Breaks Here
1. **Mathematical Inability & Running State Traversal**: A naive RAG system evaluates chunks sequentially without cross-referencing global operational states. An LLM cannot accurately count and carry over exactly how much of a dynamic sub-limit was drained by C1 before processing C3.
2. **Footnote and Endorsement Cross-contamination**: Rules override each other across distinct sections. The baseline table states 20% coinsurance for Physiotherapy, while Endorsement E1 completely alters this to 10% in the back of the document. Standard semantic vector search often grabs the densely populated main table and totally misses the disparate endorsement chunk.
3. **Auditability Faults**: Financial compliance requires strict execution paths that can be debugged block by block. A standard conversational LLM produces text representations of math; if it hallucinates a calculation or forgets a GC-3 penalty logic step, the execution failure is trapped inside the "black box" output rather than a verifiable code branch. Separating extraction (LLM structured outputs) from calculation (Python) guarantees 100% deterministic validity.



## App Usage
project-README.md have short instructions how to strt the app.
