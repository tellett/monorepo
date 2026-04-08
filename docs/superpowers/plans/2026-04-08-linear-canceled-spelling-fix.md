# Linear "canceled" Spelling Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the British/American spelling mismatch that causes "canceled" and "duplicate" Linear issues to appear in org files.

**Architecture:** Linear's API returns state type `"canceled"` (American spelling, one `l`). The codebase filters/checks on `"cancelled"` (two `l`s), so the filter never matches. Fix both the GraphQL `nin` filters and the org-writer keyword check to use the correct spelling.

**Tech Stack:** Python, pytest via Bazel (`bazel test //py/linear_org_sync:linear_org_sync_test`)

---

### Task 1: Fix org_writer — update test first, then implementation

**Files:**
- Modify: `py/linear_org_sync/org_writer_test.py:48-51`
- Modify: `py/linear_org_sync/org_writer.py:32`

- [ ] **Step 1: Update the test to use the correct spelling**

In `py/linear_org_sync/org_writer_test.py`, change the test at line 48:

```python
def test_todo_keyword_canceled():
    issue = _make_issue(state_type="canceled", state_name="Canceled")
    text = format_issue(issue)
    assert text.startswith("* DONE ")
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
bazel test //py/linear_org_sync:linear_org_sync_test --test_output=streamed -- //py/linear_org_sync:linear_org_sync_test 2>&1 | grep -A5 "test_todo_keyword_canceled"
```

Expected: FAIL — `format_issue` returns `"* TODO ..."` because `"canceled"` doesn't match `"cancelled"` in the check.

- [ ] **Step 3: Fix the implementation**

In `py/linear_org_sync/org_writer.py`, change line 32:

```python
    if issue.state_type in ("completed", "canceled"):
```

- [ ] **Step 4: Run the test to verify it passes**

```bash
bazel test //py/linear_org_sync:linear_org_sync_test --test_output=streamed
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add py/linear_org_sync/org_writer.py py/linear_org_sync/org_writer_test.py
git commit -m "fix(linear-org-sync): use correct spelling 'canceled' in org_writer state check"
```

---

### Task 2: Fix linear_client — correct spelling in all three GraphQL filters

**Files:**
- Modify: `py/linear_org_sync/linear_client.py:37,49,63`

- [ ] **Step 1: Update all three GraphQL queries**

In `py/linear_org_sync/linear_client.py`, change `"cancelled"` → `"canceled"` in each of the three query strings.

`_ASSIGNED_QUERY` (line 37):
```python
            filter: {{ state: {{ type: {{ nin: ["completed", "canceled"] }} }} }}
```

`_TEAM_QUERY` (line 49):
```python
                filter: {{ state: {{ type: {{ nin: ["completed", "canceled"] }} }} }}
```

`_PROJECT_QUERY` (line 63):
```python
            filter: {{ state: {{ type: {{ nin: ["completed", "canceled"] }} }} }}
```

- [ ] **Step 2: Run all tests to verify nothing broke**

```bash
bazel test //py/linear_org_sync:linear_org_sync_test --test_output=streamed
```

Expected: All tests PASS. (The GraphQL strings are not directly unit-tested — they are verified by integration with the live API.)

- [ ] **Step 3: Commit**

```bash
git add py/linear_org_sync/linear_client.py
git commit -m "fix(linear-org-sync): use correct spelling 'canceled' in GraphQL nin filters"
```
