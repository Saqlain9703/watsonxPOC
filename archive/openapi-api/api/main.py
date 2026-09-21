"""Run with: python -m uvicorn api.main:app --host 127.0.0.1 --port 8000."""

from typing import Annotated

from fastapi import FastAPI, Query

from api.eligibility import EligibilityRequest, EligibilityResult, POLICY_VERSION, evaluate

app = FastAPI(title="Shipping Eligibility POC", version="1.0.0", description=(
    "Deterministic dummy shipping eligibility. No real rates, bookings, or customer data."
))


@app.get("/health", include_in_schema=False)
def health() -> dict:
    return {"status": "ok", "policy_version": POLICY_VERSION}


@app.get(
    "/eligibility", operation_id="evaluate_rate_eligibility", response_model=EligibilityResult,
    summary="Evaluate simulated shipping rate eligibility",
    description=(
        "Return a simulated plan tier and discount from confirmed monthly shipment volume, "
        "destination mix, and business type. All three inputs are required. Never invent "
        "missing values or use this tool for general shipping questions. HTTP 422 means "
        "invalid input, not a Standard-tier decision. Does not calculate a full shipping quote."
    ),
)
def evaluate_rate_eligibility(request: Annotated[EligibilityRequest, Query()]) -> EligibilityResult:
    return evaluate(request)
