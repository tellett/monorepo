# Design: Fix "canceled" spelling in Linear state type filters

## Problem

Issues marked as "Duplicate" (or "Canceled") in Linear were appearing in synced org files. Root cause: the Linear API returns state type `"canceled"` (American spelling), but the codebase filters on `"cancelled"` (British spelling). The mismatch means the `nin` filter never excludes these issues.

Confirmed by inspecting the Engineering team's workflow states via the Linear API — "Duplicate" has `type: "canceled"`, not `"canceled"` with two `l`s.

## Fix

Two files, one change each:

**`py/linear_org_sync/linear_client.py`** — three GraphQL queries (`_ASSIGNED_QUERY`, `_TEAM_QUERY`, `_PROJECT_QUERY`) each have:
```
filter: { state: { type: { nin: ["completed", "cancelled"] } } }
```
Change `"cancelled"` → `"canceled"`.

**`py/linear_org_sync/org_writer.py`** — `_org_todo_keyword` checks:
```python
if issue.state_type in ("completed", "cancelled"):
```
Change `"cancelled"` → `"canceled"`.

## Testing

Update any existing test fixtures or assertions that reference `"cancelled"` to use `"canceled"`.
