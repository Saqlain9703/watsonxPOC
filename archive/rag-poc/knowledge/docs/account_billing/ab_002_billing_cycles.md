# Billing cycles and effective dates

Document ID: AB-002
Version: 1.0
Effective date: 2026-09-01
Owner: Billing Operations
Classification: Synthetic POC policy for the fictional Northstar Workspace service.

## First cycle

The first billing cycle begins when the account is activated, not when the
registration form is submitted. Subscription charges are billed in advance.
All billing dates and billing boundaries use UTC.

## Renewals

Monthly subscriptions renew on the same day number each month. If a month does
not contain that day number, renewal occurs on its final calendar day. For
example, an account activated on January 31 renews on February's final day and
then on March 31. Annual subscriptions renew on the anniversary of the annual
cycle start; a February 29 anniversary uses February 28 in non-leap years.

## Changing billing frequency

An approved change from monthly to annual billing takes effect on the next
scheduled billing date after the request is confirmed. It does not change the
current cycle or create a mid-cycle prorated charge. Eligibility for annual
billing is defined by Product & Policy.

For a specific account, use the next billing date returned by the account-status
tool. Do not calculate a replacement date when the tool supplies no date, and
do not represent a proposed change as an approved or completed change.
