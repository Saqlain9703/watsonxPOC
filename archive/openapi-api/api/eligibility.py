"""Pure, deterministic eligibility rules. No LLM, network, database, or clock."""

from enum import Enum
import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

POLICY_VERSION = "shipping-rates-v1"


class DestinationMix(str, Enum):
    DOMESTIC_ONLY = "domestic_only"
    MIXED = "mixed"
    INTERNATIONAL_HEAVY = "international_heavy"


class BusinessType(str, Enum):
    ECOMMERCE = "ecommerce"
    RETAIL = "retail"
    MANUFACTURING = "manufacturing"
    LOGISTICS = "logistics"
    OTHER = "other"


class EligibilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    monthly_volume: int = Field(
        ge=0, le=1_000_000,
        description="Confirmed number of shipments per month, not per week or year. Whole number from 0 to 1000000.",
    )
    destination_mix: DestinationMix = Field(description=(
        "domestic_only for no international shipments; mixed for some international "
        "up to 50 percent or an explicitly mixed pattern; international_heavy for "
        "more than 50 percent international or explicitly mostly/all international."
    ))
    business_type: BusinessType = Field(description=(
        "Customer-confirmed business category. Required for audit; does not alter v1 discounts."
    ))


class EligibilityResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    plan_tier: Literal["Platinum", "Gold", "Silver", "Bronze", "Standard"]
    discount_rate: float = Field(ge=0, le=1, description="Fraction, e.g. 0.18 means 18 percent.")
    discount_percent: int = Field(ge=0, le=100)
    eligible_for_discount: bool
    inputs: EligibilityRequest
    rule_id: str
    reason: str
    policy_version: str
    decision_id: str = Field(description="Deterministic reference, not an authentication signature.")
    source: Literal["dummy_shipping_eligibility_api"]
    is_simulated: Literal[True]
    limitations: list[str]


# Highest qualifying threshold for the SAME destination mix wins. Percentages
# are integers; business_type is intentionally audit-only until a rule is agreed.
RATE_TABLE = (
    (1000, DestinationMix.INTERNATIONAL_HEAVY, "Platinum", 18, "INTL_1000"),
    (500, DestinationMix.INTERNATIONAL_HEAVY, "Gold", 12, "INTL_500"),
    (500, DestinationMix.MIXED, "Gold", 10, "MIXED_500"),
    (100, DestinationMix.MIXED, "Silver", 6, "MIXED_100"),
    (1, DestinationMix.DOMESTIC_ONLY, "Bronze", 3, "DOMESTIC_POSITIVE"),
)


def evaluate(request: EligibilityRequest) -> EligibilityResult:
    tier, percent, rule_id = "Standard", 0, "NO_MATCH"
    reason = "No volume threshold matches this destination mix."
    if request.monthly_volume == 0:
        rule_id = "ZERO_VOLUME"
        reason = "Zero monthly shipments do not qualify for a shipping discount."
    else:
        matches = [row for row in RATE_TABLE
                   if request.monthly_volume >= row[0] and request.destination_mix == row[1]]
        if matches:
            minimum, mix, tier, percent, rule_id = max(matches, key=lambda row: row[0])
            reason = f"Monthly volume {request.monthly_volume} meets threshold {minimum} for {mix.value}."
    canonical = json.dumps({"policy_version": POLICY_VERSION, **request.model_dump(mode="json")},
                           sort_keys=True, separators=(",", ":"))
    decision_id = "elig-" + hashlib.sha256(canonical.encode()).hexdigest()[:20]
    return EligibilityResult(
        plan_tier=tier, discount_rate=percent / 100, discount_percent=percent,
        eligible_for_discount=percent > 0, inputs=request.model_copy(deep=True),
        rule_id=rule_id, reason=reason, policy_version=POLICY_VERSION,
        decision_id=decision_id, source="dummy_shipping_eligibility_api", is_simulated=True,
        limitations=[
            "Synthetic POC rules; this is not a binding quote or a booking.",
            "Business type is recorded for audit and does not affect v1 rates.",
            "No base price, payable amount, delivery promise, or live account check is provided.",
        ],
    )
