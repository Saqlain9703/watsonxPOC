# Product capabilities

Document ID: PP-001
Version: 1.0
Effective date: 2026-09-01
Owner: Product Policy
Classification: Synthetic POC policy for the fictional Northstar Workspace service.

## What the service does

Northstar Workspace is a hosted workspace for managing customer-onboarding
checklists. Teams can create task boards, assign checklist items to members,
record completion, and view an activity history. Workspace administrators manage
membership; members work on the tasks they are permitted to access.

## Exports

Both Starter and Growth support exporting checklist items as a CSV file.
Exported rows contain the task title, assignee display label, state, and due
date when one is present. A CSV export does not include uploaded attachments.

## Scope of the onboarding assistant

The assistant explains documented capabilities and onboarding requirements.
Its account lookup reports a fixed synthetic account snapshot. It cannot
create workspaces, invite members, change plans, process payments, or execute
data exports. Requests for an operation must not be reported as completed by
the assistant.
