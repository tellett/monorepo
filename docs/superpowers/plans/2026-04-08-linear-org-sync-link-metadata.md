# Linear Org Sync — Link Metadata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface GitHub PR and external doc links from Linear issue attachments and descriptions as `PROPERTIES` entries in the org-mode output.

**Architecture:** `Link` model and two new fields added to `Issue` in `org_writer.py`; a new `_extract_links` helper in `linear_client.py` collects URLs from the `attachments` API field and description body text, deduplicates, and classifies them; `format_issue` renders them as indexed or bare `:GITHUB_PR:` / `:OTHER_LINK:` properties.

**Tech Stack:** Python 3.12, Pydantic, httpx, regex (stdlib `re`), Bazel + pytest

---

## File Map

| File | Change |
|------|--------|
| `py/linear_org_sync/org_writer.py` | Add `Link` model; extend `Issue` with `github_prs` + `other_links`; add `_link_properties`; update `format_issue` |
| `py/linear_org_sync/linear_client.py` | Extend `_ISSUE_FIELDS` with `description` + `attachments`; add `_extract_links`; update `_parse_issue` |
| `py/linear_org_sync/org_writer_test.py` | Add tests for link property rendering |
| `py/linear_org_sync/linear_client_test.py` | Update `_issue_node` helper; add tests for `_extract_links` |

---

## Task 1: Add `Link` model and extend `Issue`

**Files:**
- Modify: `py/linear_org_sync/org_writer.py`
- Test: `py/linear_org_sync/org_writer_test.py`

- [ ] **Step 1: Write a failing test confirming no link properties appear on an issue with empty link lists**

Add to `py/linear_org_sync/org_writer_test.py` (after the existing imports):

```python
from py.linear_org_sync.org_writer import Issue, Link, format_issue, write_org_file
```

Replace the existing import line:
```python
from py.linear_org_sync.org_writer import Issue, format_issue, write_org_file
```

Then add after `test_properties_drawer_contains_id_and_url`:

```python
def test_format_issue_no_links_produces_no_link_properties():
    issue = _make_issue()
    text = format_issue(issue)
    assert ":GITHUB_PR" not in text
    assert ":OTHER_LINK" not in text
```

- [ ] **Step 2: Run test to verify it fails**

```bash
bazel test //py/linear_org_sync:linear_org_sync_test --test_output=short 2>&1 | grep -A5 "FAILED\|ImportError\|cannot import"
```

Expected: ImportError — `Link` does not exist yet.

- [ ] **Step 3: Add `Link` model and extend `Issue` in `org_writer.py`**

In `py/linear_org_sync/org_writer.py`, replace the `Issue` class with:

```python
class Link(BaseModel):
    url: str
    title: str


class Issue(BaseModel):
    identifier: str
    title: str
    priority: int
    url: str
    state_name: str
    state_type: str
    github_prs: list[Link] = []
    other_links: list[Link] = []
```

- [ ] **Step 4: Run test to verify it passes**

```bash
bazel test //py/linear_org_sync:linear_org_sync_test --test_output=short 2>&1 | grep -E "PASSED|FAILED|ERROR"
```

Expected: all tests pass (new `list[Link]` fields default to `[]`, existing tests unaffected).

- [ ] **Step 5: Commit**

```bash
git add py/linear_org_sync/org_writer.py py/linear_org_sync/org_writer_test.py
git commit -m "feat(linear-org-sync): add Link model and link fields to Issue"
```

---

## Task 2: Render link properties in `format_issue`

**Files:**
- Modify: `py/linear_org_sync/org_writer.py`
- Test: `py/linear_org_sync/org_writer_test.py`

- [ ] **Step 1: Write failing tests for all rendering cases**

Add to `py/linear_org_sync/org_writer_test.py`:

```python
def test_format_issue_single_pr_uses_bare_key():
    issue = _make_issue(
        github_prs=[Link(url="https://github.com/org/repo/pull/9", title="Fix: org/repo#9")]
    )
    text = format_issue(issue)
    assert ":GITHUB_PR: https://github.com/org/repo/pull/9" in text
    assert ":GITHUB_PR_1:" not in text


def test_format_issue_multiple_prs_uses_indexed_keys():
    issue = _make_issue(
        github_prs=[
            Link(url="https://github.com/org/repo/pull/9", title="PR 1"),
            Link(url="https://github.com/org/repo/pull/12", title="PR 2"),
        ]
    )
    text = format_issue(issue)
    assert ":GITHUB_PR_1: https://github.com/org/repo/pull/9" in text
    assert ":GITHUB_PR_2: https://github.com/org/repo/pull/12" in text
    assert ":GITHUB_PR: https" not in text


def test_format_issue_single_other_link_uses_bare_key():
    issue = _make_issue(
        other_links=[Link(url="https://notion.so/some-doc", title="Doc")]
    )
    text = format_issue(issue)
    assert ":OTHER_LINK: https://notion.so/some-doc" in text
    assert ":OTHER_LINK_1:" not in text


def test_format_issue_multiple_other_links_uses_indexed_keys():
    issue = _make_issue(
        other_links=[
            Link(url="https://notion.so/doc-a", title="Doc A"),
            Link(url="https://docs.google.com/doc-b", title="Doc B"),
        ]
    )
    text = format_issue(issue)
    assert ":OTHER_LINK_1: https://notion.so/doc-a" in text
    assert ":OTHER_LINK_2: https://docs.google.com/doc-b" in text
    assert ":OTHER_LINK: https" not in text


def test_format_issue_mixed_links_index_types_independently():
    issue = _make_issue(
        github_prs=[
            Link(url="https://github.com/org/repo/pull/9", title="PR 1"),
            Link(url="https://github.com/org/repo/pull/12", title="PR 2"),
        ],
        other_links=[Link(url="https://notion.so/doc", title="Doc")],
    )
    text = format_issue(issue)
    assert ":GITHUB_PR_1: https://github.com/org/repo/pull/9" in text
    assert ":GITHUB_PR_2: https://github.com/org/repo/pull/12" in text
    assert ":OTHER_LINK: https://notion.so/doc" in text
    assert ":OTHER_LINK_1:" not in text
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
bazel test //py/linear_org_sync:linear_org_sync_test --test_output=short 2>&1 | grep -E "FAILED|PASSED"
```

Expected: the 5 new tests fail (`:GITHUB_PR:` etc. not yet rendered).

- [ ] **Step 3: Implement `_link_properties` and update `format_issue`**

In `py/linear_org_sync/org_writer.py`, add after `_org_priority`:

```python
def _link_properties(name: str, links: list[Link]) -> str:
    if not links:
        return ""
    if len(links) == 1:
        return f"  :{name}: {links[0].url}\n"
    return "".join(f"  :{name}_{i}: {link.url}\n" for i, link in enumerate(links, 1))
```

Replace `format_issue` with:

```python
def format_issue(issue: Issue) -> str:
    keyword = _org_todo_keyword(issue)
    priority = _org_priority(issue.priority)
    pr_props = _link_properties("GITHUB_PR", issue.github_prs)
    link_props = _link_properties("OTHER_LINK", issue.other_links)
    return (
        f"* {keyword}{priority} {issue.title}\n"
        f"  :PROPERTIES:\n"
        f"  :LINEAR_ID: {issue.identifier}\n"
        f"  :LINEAR_URL: {issue.url}\n"
        f"{pr_props}"
        f"{link_props}"
        f"  :END:\n"
    )
```

- [ ] **Step 4: Run tests to verify all pass**

```bash
bazel test //py/linear_org_sync:linear_org_sync_test --test_output=short 2>&1 | grep -E "FAILED|PASSED|ERROR"
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add py/linear_org_sync/org_writer.py py/linear_org_sync/org_writer_test.py
git commit -m "feat(linear-org-sync): render GitHub PR and other link properties in org output"
```

---

## Task 3: Implement `_extract_links` in `linear_client.py`

**Files:**
- Modify: `py/linear_org_sync/linear_client.py`
- Test: `py/linear_org_sync/linear_client_test.py`

- [ ] **Step 1: Write failing tests for `_extract_links`**

Add to `py/linear_org_sync/linear_client_test.py`, after the existing imports:

```python
from py.linear_org_sync.linear_client import LinearClient, _extract_links
```

Replace:
```python
from py.linear_org_sync.linear_client import LinearClient
```

Then add at the end of the file:

```python
def _node_with_attachments(attachments=None, description=None):
    return {
        "identifier": "ENG-1",
        "title": "Test",
        "priority": 0,
        "url": "https://linear.app/x/ENG-1",
        "state": {"name": "Todo", "type": "unstarted"},
        "description": description,
        "attachments": {"nodes": attachments or []},
    }


def test_extract_links_pr_url_goes_to_github_prs():
    node = _node_with_attachments(
        attachments=[{"url": "https://github.com/org/repo/pull/9", "title": "My PR"}]
    )
    prs, others = _extract_links(node)
    assert len(prs) == 1
    assert prs[0].url == "https://github.com/org/repo/pull/9"
    assert prs[0].title == "My PR"
    assert others == []


def test_extract_links_non_pr_url_goes_to_other_links():
    node = _node_with_attachments(
        attachments=[{"url": "https://notion.so/some-doc", "title": "Doc"}]
    )
    prs, others = _extract_links(node)
    assert prs == []
    assert len(others) == 1
    assert others[0].url == "https://notion.so/some-doc"
    assert others[0].title == "Doc"


def test_extract_links_github_issue_url_goes_to_other_links():
    node = _node_with_attachments(
        attachments=[
            {"url": "https://github.com/org/repo/issues/42", "title": "Issue"}
        ]
    )
    prs, others = _extract_links(node)
    assert prs == []
    assert len(others) == 1


def test_extract_links_description_url_extracted():
    node = _node_with_attachments(
        attachments=[],
        description="See https://notion.so/doc for context",
    )
    prs, others = _extract_links(node)
    assert len(others) == 1
    assert others[0].url == "https://notion.so/doc"
    assert others[0].title == "https://notion.so/doc"


def test_extract_links_deduplication_prefers_attachment_title():
    node = _node_with_attachments(
        attachments=[{"url": "https://github.com/org/repo/pull/9", "title": "My PR"}],
        description="Check https://github.com/org/repo/pull/9 for details",
    )
    prs, others = _extract_links(node)
    assert len(prs) == 1
    assert prs[0].title == "My PR"


def test_extract_links_no_attachments_no_description_returns_empty():
    node = _node_with_attachments()
    prs, others = _extract_links(node)
    assert prs == []
    assert others == []
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
bazel test //py/linear_org_sync:linear_org_sync_test --test_output=short 2>&1 | grep -E "FAILED|ImportError|cannot import"
```

Expected: ImportError — `_extract_links` does not exist yet.

- [ ] **Step 3: Implement `_extract_links` in `linear_client.py`**

Add at the top of `py/linear_org_sync/linear_client.py`, after `import httpx`:

```python
import re
```

Add after the existing imports and before `_LINEAR_API_URL`:

```python
_GITHUB_PR_RE = re.compile(r"github\.com/.+/pull/\d+")
_URL_RE = re.compile(r"https?://\S+")
```

Update the import at the top of `linear_client.py`:

Replace:
```python
from py.linear_org_sync.org_writer import Issue
```

With:
```python
from py.linear_org_sync.org_writer import Issue, Link
```

Note: write `_extract_links` with the correct type annotation from the start — `Link` is available because the import above is updated in this same step:

```python
def _extract_links(node: dict) -> tuple[list[Link], list[Link]]:
    seen: dict[str, Link] = {}

    for att in node.get("attachments", {}).get("nodes", []):
        url = att.get("url", "")
        if url:
            seen[url] = Link(url=url, title=att.get("title", url))

    for url in _URL_RE.findall(node.get("description") or ""):
        if url not in seen:
            seen[url] = Link(url=url, title=url)

    github_prs = []
    other_links = []
    for link in seen.values():
        if _GITHUB_PR_RE.search(link.url):
            github_prs.append(link)
        else:
            other_links.append(link)

    return github_prs, other_links
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
bazel test //py/linear_org_sync:linear_org_sync_test --test_output=short 2>&1 | grep -E "FAILED|PASSED|ERROR"
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add py/linear_org_sync/linear_client.py py/linear_org_sync/linear_client_test.py
git commit -m "feat(linear-org-sync): add _extract_links to classify and deduplicate issue links"
```

---

## Task 4: Wire `_extract_links` into `_parse_issue` and fetch links from the API

**Files:**
- Modify: `py/linear_org_sync/linear_client.py`
- Modify: `py/linear_org_sync/linear_client_test.py`

- [ ] **Step 1: Update `_ISSUE_FIELDS` to fetch `description` and `attachments`**

In `py/linear_org_sync/linear_client.py`, replace `_ISSUE_FIELDS` with:

```python
_ISSUE_FIELDS = """
    identifier
    title
    priority
    url
    state {
        name
        type
    }
    description
    attachments {
        nodes {
            title
            url
        }
    }
"""
```

- [ ] **Step 2: Update `_parse_issue` to call `_extract_links`**

Replace `_parse_issue` in `py/linear_org_sync/linear_client.py` with:

```python
def _parse_issue(node: dict) -> Issue:
    github_prs, other_links = _extract_links(node)
    return Issue(
        identifier=node["identifier"],
        title=node["title"],
        priority=node["priority"],
        url=node["url"],
        state_name=node["state"]["name"],
        state_type=node["state"]["type"],
        github_prs=github_prs,
        other_links=other_links,
    )
```

- [ ] **Step 3: Update `_issue_node` helper in `linear_client_test.py` to include the new fields**

In `py/linear_org_sync/linear_client_test.py`, replace `_issue_node` with:

```python
def _issue_node(
    identifier="ENG-1",
    title="Test",
    priority=0,
    url="https://linear.app/x/ENG-1",
    state_name="Todo",
    state_type="unstarted",
    description=None,
    attachments=None,
) -> dict:
    return {
        "identifier": identifier,
        "title": title,
        "priority": priority,
        "url": url,
        "state": {"name": state_name, "type": state_type},
        "description": description,
        "attachments": {"nodes": attachments or []},
    }
```

- [ ] **Step 4: Run all tests to verify nothing is broken**

```bash
bazel test //py/linear_org_sync:linear_org_sync_test --test_output=short 2>&1 | grep -E "FAILED|PASSED|ERROR"
```

Expected: all tests pass. The existing `get_assigned_issues`, `get_team_issues`, and `get_project_issues` tests continue to pass because `_issue_node` now supplies the new fields with safe defaults.

- [ ] **Step 5: Commit**

```bash
git add py/linear_org_sync/linear_client.py py/linear_org_sync/linear_client_test.py
git commit -m "feat(linear-org-sync): fetch attachments and description from Linear API"
```
