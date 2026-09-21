"""Read-only synthetic account snapshots; no network, clock, or real customer data."""

from copy import deepcopy
import re

from ibm_watsonx_orchestrate.agent_builder.tools import ToolPermission, tool

AS_OF = "2026-09-16T00:00:00Z"
ACCOUNTS = {
    "ACC-0001": {
        "status": "active", "plan": "starter", "billing_frequency": "monthly",
        "next_billing_date": "2026-10-01",
    },
    "ACC-0002": {
        "status": "active", "plan": "growth", "billing_frequency": "monthly",
        "next_billing_date": "2026-10-15",
    },
    "ACC-0003": {
        "status": "past_due", "plan": "growth", "billing_frequency": "monthly",
        "next_billing_date": "2026-10-05",
    },
    "ACC-0004": {
        "status": "pending_activation", "plan": "starter", "billing_frequency": "monthly",
        "next_billing_date": None,
    },
}


@tool(
    name="get_account_status",
    description=(
        "Look up one synthetic Northstar Workspace account by its exact ID "
        "(ACC- followed by four digits). Returns a fixed snapshot of status, plan, "
        "billing frequency, and next billing date. This is demo data, not a live "
        "customer system. Use for account-specific facts; use knowledge for general policies."
    ),
    permission=ToolPermission.READ_ONLY,
)
def get_account_status(account_id: str) -> dict:
    """Return a deterministic account snapshot without modifying any account.

    Args:
        account_id: Exact synthetic account ID supplied by the user, such as ACC-0001.

    Returns:
        dict: found, error, source, as_of, and account. The account is null for
        invalid or unknown IDs. A null next_billing_date means no date is available.
    """
    result = {
        "found": False,
        "error": None,
        "source": "synthetic_account_fixture_v1",
        "as_of": AS_OF,
        "account": None,
    }
    if not isinstance(account_id, str) or re.fullmatch(r"ACC-[0-9]{4}", account_id) is None:
        result["error"] = "INVALID_ACCOUNT_ID"
        return result
    if account_id not in ACCOUNTS:
        result["error"] = "ACCOUNT_NOT_FOUND"
        return result
    result["found"] = True
    result["account"] = {"account_id": account_id, **deepcopy(ACCOUNTS[account_id])}
    return result
