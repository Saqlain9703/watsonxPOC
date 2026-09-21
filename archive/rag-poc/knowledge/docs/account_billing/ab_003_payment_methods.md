# Payment methods and failed payments

Document ID: AB-003
Version: 1.0
Effective date: 2026-09-01
Owner: Billing Operations
Classification: Synthetic POC policy for the fictional Northstar Workspace service.

## Supported payments

Northstar Workspace accepts Visa and Mastercard credit or debit cards for the
Starter and Growth subscriptions in this demonstration. Charges are in USD.
Cash, bank transfers, checks, cryptocurrency, and digital wallets are not
supported payment methods in this POC policy.

An administrator updates the payment method in Settings > Billing > Payment
method. A chat agent cannot collect card details or update the payment method.
Updating a payment method does not by itself change the subscription plan.

## Failed charges

After an initial failed renewal charge, automatic retries are scheduled three
and seven calendar days after that failed charge. The account is marked
past_due while the invoice remains unpaid. The existence of a retry schedule
does not establish whether any particular charge succeeded.

Use the account-status lookup to report a specific account's status. The POC
lookup does not contain transaction history, decline reasons, or card details;
those cannot be inferred from the past_due label.
