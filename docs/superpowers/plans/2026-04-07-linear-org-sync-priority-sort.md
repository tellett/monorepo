# linear_org_sync Priority Sort Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sort issues in the generated org file by priority (urgent first, no-priority last), then alphabetically by title within each priority level.

**Architecture:** Add one `sorted()` call at the top of `write_org_file` in `org_writer.py`. Priority `0` (no priority) is remapped to `5` so it sorts after low priority (`4`). Title comparison is case-insensitive.

**Tech Stack:** Python 3.12, pytest, Bazel (`bazel test`)

---

### Task 1: Add failing tests for sort order

**Files:**
- Modify: `py/linear_org_sync/org_writer_test.py`

- [ ] **Step 1: Add three new test functions** to `py/linear_org_sync/org_writer_test.py` after the existing `test_write_org_file_overwrites_existing` test:

```python
def test_write_org_file_sorts_by_priority(tmp_path):
    output = tmp_path / "test.org"
    issues = [
        _make_issue(identifier="ENG-5", title="No priority issue", priority=0),
        _make_issue(identifier="ENG-4", title="Low priority issue", priority=4),
        _make_issue(identifier="ENG-3", title="Medium priority issue", priority=3),
        _make_issue(identifier="ENG-2", title="High priority issue", priority=2),
        _make_issue(identifier="ENG-1", title="Urgent issue", priority=1),
    ]
    write_org_file(output, issues, "test")
    content = output.read_text()
    pos_urgent = content.index("ENG-1")
    pos_high = content.index("ENG-2")
    pos_medium = content.index("ENG-3")
    pos_low = content.index("ENG-4")
    pos_none = content.index("ENG-5")
    assert pos_urgent < pos_high < pos_medium < pos_low < pos_none


def test_write_org_file_sorts_alphabetically_within_priority(tmp_path):
    output = tmp_path / "test.org"
    issues = [
        _make_issue(identifier="ENG-3", title="Zebra task", priority=2),
        _make_issue(identifier="ENG-1", title="Apple task", priority=2),
        _make_issue(identifier="ENG-2", title="Mango task", priority=2),
    ]
    write_org_file(output, issues, "test")
    content = output.read_text()
    pos_apple = content.index("Apple task")
    pos_mango = content.index("Mango task")
    pos_zebra = content.index("Zebra task")
    assert pos_apple < pos_mango < pos_zebra


def test_write_org_file_no_priority_sorts_after_low(tmp_path):
    output = tmp_path / "test.org"
    issues = [
        _make_issue(identifier="ENG-2", title="No priority issue", priority=0),
        _make_issue(identifier="ENG-1", title="Low priority issue", priority=4),
    ]
    write_org_file(output, issues, "test")
    content = output.read_text()
    pos_low = content.index("ENG-1")
    pos_none = content.index("ENG-2")
    assert pos_low < pos_none
```

- [ ] **Step 2: Run the new tests to verify they fail**

```bash
bazel test //py/linear_org_sync:linear_org_sync_test --test_output=short 2>&1 | grep -E "FAIL|PASS|ERROR|test_write_org_file_sorts"
```

Expected: the three new tests FAIL (issues appear in insertion order, not sorted order).

---

### Task 2: Implement the sort

**Files:**
- Modify: `py/linear_org_sync/org_writer.py:53-57`

- [ ] **Step 1: Add the sort line** at the top of `write_org_file`, making it read:

```python
def write_org_file(path: pathlib.Path, issues: list[Issue], source_label: str) -> None:
    issues = sorted(issues, key=lambda i: (i.priority if i.priority != 0 else 5, i.title.lower()))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"# Linear sync: {source_label} — {timestamp}\n\n"
    content = header + "".join(format_issue(i) for i in issues)
    path.write_text(content)
```

- [ ] **Step 2: Run all tests to verify they pass**

```bash
bazel test //py/linear_org_sync:linear_org_sync_test --test_output=short
```

Expected: all tests PASS, including the three new ones.

- [ ] **Step 3: Commit**

```bash
git add py/linear_org_sync/org_writer.py py/linear_org_sync/org_writer_test.py
git commit -m "feat(linear-org-sync): sort issues by priority then alphabetically"
```
