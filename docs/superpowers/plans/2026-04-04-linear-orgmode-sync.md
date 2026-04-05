# Linear → org-mode Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python script that reads Linear issues from the GraphQL API and writes them as org-mode files, run hourly via a systemd user timer.

**Architecture:** A `py_binary` Bazel target at `//py/linear_org_sync` reads `~/org/linear/config.yaml`, queries Linear's GraphQL API with `httpx`, and rewrites one `.org` file per configured source (assigned, team, or project). Config and data models use Pydantic v2 with discriminated unions. Doom Emacs auto-discovers the org files for the agenda.

**Tech Stack:** Python 3.12, httpx, pyyaml, pydantic v2, absl-py, Bazel (aspect_rules_py), systemd user timer

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `pyproject.toml` | Modify | Add `httpx`, `pyyaml`, `pydantic` to dependencies |
| `requirements/runtime.txt` | Regenerated | Pinned runtime deps |
| `requirements/all.txt` | Regenerated | All pinned deps |
| `py/linear_org_sync/__init__.py` | Create | Package marker |
| `py/linear_org_sync/config.py` | Create | Pydantic models + load_config() |
| `py/linear_org_sync/org_writer.py` | Create | Issue Pydantic model + org rendering |
| `py/linear_org_sync/linear_client.py` | Create | GraphQL queries against Linear API |
| `py/linear_org_sync/__main__.py` | Create | Entry point, orchestrates the sync |
| `py/linear_org_sync/BUILD.bazel` | Create | py_binary + py_test Bazel targets |
| `py/linear_org_sync/config_test.py` | Create | Tests for config.py |
| `py/linear_org_sync/org_writer_test.py` | Create | Tests for org_writer.py |
| `py/linear_org_sync/linear_client_test.py` | Create | Tests for linear_client.py (mocked HTTP) |
| `~/org/linear/config.yaml` | Create | Sample config with placeholder API key |
| `~/.config/doom/config.el` | Modify | Auto-add ~/org/linear/*.org to agenda |
| `~/.config/systemd/user/linear-org-sync.service` | Create | oneshot service |
| `~/.config/systemd/user/linear-org-sync.timer` | Create | Hourly timer |

---

## Task 1: Add dependencies to pyproject.toml and repin

**Files:**
- Modify: `pyproject.toml`
- Regenerated: `requirements/runtime.txt`, `requirements/all.txt`

- [ ] **Step 1: Add dependencies to pyproject.toml**

Edit the `dependencies` list in `pyproject.toml`:

```toml
[project]
name = "monorepo"
classifiers = ["Private :: Do Not Upload"]
version = "0"

dependencies = [
  "absl-py",
  "httpx",
  "pydantic",
  "pyyaml",
]

[dependency-groups]
dev = [
  "pytest"
]

[tool.ruff]
```

- [ ] **Step 2: Repin runtime requirements**

```
bazel run //requirements:runtime
```

Expected: `requirements/runtime.txt` updated with `httpx`, `pydantic`, `pyyaml`, and their transitive deps.

- [ ] **Step 3: Repin all requirements**

```
bazel run //requirements:requirements.all
```

Expected: `requirements/all.txt` updated to include the new packages.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml requirements/runtime.txt requirements/all.txt
git commit -m "deps: add httpx, pydantic, and pyyaml for linear org sync"
```

---

## Task 2: Create config.py with tests (TDD)

**Files:**
- Create: `py/linear_org_sync/__init__.py`
- Create: `py/linear_org_sync/config.py`
- Create: `py/linear_org_sync/config_test.py`
- Create: `py/linear_org_sync/BUILD.bazel`

- [ ] **Step 1: Create package marker**

Create `py/linear_org_sync/__init__.py` as an empty file.

- [ ] **Step 2: Write the failing tests**

Create `py/linear_org_sync/config_test.py`:

```python
import pathlib
import textwrap

import pytest

from py.linear_org_sync.config import (
    AssignedSource,
    ProjectSource,
    TeamSource,
    load_config,
)


def test_load_assigned_source(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(textwrap.dedent("""\
        linear:
          api_key: "lin_api_test"
          sync_interval_minutes: 30
        sources:
          - type: assigned
    """))
    config = load_config(config_file)
    assert config.linear.api_key == "lin_api_test"
    assert config.linear.sync_interval_minutes == 30
    assert len(config.sources) == 1
    assert isinstance(config.sources[0], AssignedSource)
    assert config.sources[0].output_file == "assigned.org"
    assert config.config_dir == tmp_path


def test_load_team_source(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(textwrap.dedent("""\
        linear:
          api_key: "lin_api_test"
        sources:
          - type: team
            slug: eng
            output_file: eng.org
    """))
    config = load_config(config_file)
    assert isinstance(config.sources[0], TeamSource)
    assert config.sources[0].slug == "eng"
    assert config.sources[0].output_file == "eng.org"


def test_load_project_source(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(textwrap.dedent("""\
        linear:
          api_key: "lin_api_test"
        sources:
          - type: project
            id: abc123
            output_file: myproject.org
    """))
    config = load_config(config_file)
    assert isinstance(config.sources[0], ProjectSource)
    assert config.sources[0].id == "abc123"
    assert config.sources[0].output_file == "myproject.org"


def test_sync_interval_defaults_to_60(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(textwrap.dedent("""\
        linear:
          api_key: "lin_api_test"
        sources: []
    """))
    config = load_config(config_file)
    assert config.linear.sync_interval_minutes == 60


def test_assigned_source_default_output_file(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(textwrap.dedent("""\
        linear:
          api_key: "lin_api_test"
        sources:
          - type: assigned
    """))
    config = load_config(config_file)
    assert config.sources[0].output_file == "assigned.org"


def test_unknown_source_type_raises(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(textwrap.dedent("""\
        linear:
          api_key: "lin_api_test"
        sources:
          - type: unknown
    """))
    with pytest.raises(Exception):
        load_config(config_file)


def test_multiple_sources(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(textwrap.dedent("""\
        linear:
          api_key: "lin_api_test"
        sources:
          - type: assigned
          - type: team
            slug: eng
            output_file: eng.org
          - type: project
            id: proj123
            output_file: project.org
    """))
    config = load_config(config_file)
    assert len(config.sources) == 3
    assert isinstance(config.sources[0], AssignedSource)
    assert isinstance(config.sources[1], TeamSource)
    assert isinstance(config.sources[2], ProjectSource)
```

- [ ] **Step 3: Create BUILD.bazel**

Create `py/linear_org_sync/BUILD.bazel`:

```python
load("@aspect_rules_py//py:defs.bzl", "py_binary", "py_library", "py_pytest_main", "py_test")

py_library(
    name = "linear_org_sync_lib",
    srcs = [
        "__init__.py",
        "config.py",
        "linear_client.py",
        "org_writer.py",
    ],
    deps = [
        "@pip//httpx",
        "@pip//pydantic",
        "@pip//pyyaml",
    ],
    visibility = ["//:__subpackages__"],
)

py_binary(
    name = "linear_org_sync",
    srcs = ["__main__.py"],
    main = "__main__.py",
    deps = [
        ":linear_org_sync_lib",
        "@pip//absl_py",
    ],
    visibility = ["//visibility:private"],
)

py_pytest_main(
    name = "__test__",
    deps = ["@pip//pytest"],
)

py_test(
    name = "linear_org_sync_test",
    srcs = [
        "config_test.py",
        "linear_client_test.py",
        "org_writer_test.py",
        ":__test__",
    ],
    main = ":__test__.py",
    deps = [
        ":__test__",
        ":linear_org_sync_lib",
    ],
)
```

- [ ] **Step 4: Run tests to confirm they fail**

```
bazel test //py/linear_org_sync:linear_org_sync_test --test_filter="config_test" --test_output=short
```

Expected: FAILED with `ModuleNotFoundError: No module named 'py.linear_org_sync.config'`

- [ ] **Step 5: Implement config.py**

Create `py/linear_org_sync/config.py`:

```python
from __future__ import annotations

import pathlib
from typing import Annotated, Literal, Union

import yaml
from pydantic import BaseModel, Field


class LinearSettings(BaseModel):
    api_key: str
    sync_interval_minutes: int = 60


class AssignedSource(BaseModel):
    type: Literal["assigned"] = "assigned"
    output_file: str = "assigned.org"


class TeamSource(BaseModel):
    type: Literal["team"]
    slug: str
    output_file: str


class ProjectSource(BaseModel):
    type: Literal["project"]
    id: str
    output_file: str


Source = Annotated[
    Union[AssignedSource, TeamSource, ProjectSource],
    Field(discriminator="type"),
]


class Config(BaseModel):
    model_config = {"arbitrary_types_allowed": True}

    linear: LinearSettings
    sources: list[Source]
    config_dir: pathlib.Path


def load_config(path: pathlib.Path) -> Config:
    raw = yaml.safe_load(path.read_text())
    return Config(config_dir=path.parent, **raw)
```

- [ ] **Step 6: Run config tests and confirm they pass**

```
bazel test //py/linear_org_sync:linear_org_sync_test --test_filter="config_test" --test_output=short
```

Expected: all 7 config tests PASS.

- [ ] **Step 7: Commit**

```bash
git add py/linear_org_sync/__init__.py py/linear_org_sync/config.py py/linear_org_sync/config_test.py py/linear_org_sync/BUILD.bazel
git commit -m "feat: add linear_org_sync config loader with Pydantic models"
```

---

## Task 3: Create org_writer.py with tests (TDD)

**Files:**
- Create: `py/linear_org_sync/org_writer.py`
- Create: `py/linear_org_sync/org_writer_test.py`

- [ ] **Step 1: Write the failing tests**

Create `py/linear_org_sync/org_writer_test.py`:

```python
import pathlib

from py.linear_org_sync.org_writer import Issue, format_issue, write_org_file


def _make_issue(**kwargs) -> Issue:
    defaults = dict(
        identifier="ENG-1",
        title="Test issue",
        priority=0,
        url="https://linear.app/test/issue/ENG-1",
        state_name="Todo",
        state_type="unstarted",
    )
    return Issue(**{**defaults, **kwargs})


def test_todo_keyword_unstarted():
    issue = _make_issue(state_type="unstarted", state_name="Todo")
    text = format_issue(issue)
    assert text.startswith("* TODO ")


def test_todo_keyword_backlog():
    issue = _make_issue(state_type="backlog", state_name="Backlog")
    text = format_issue(issue)
    assert text.startswith("* TODO ")


def test_todo_keyword_in_progress():
    issue = _make_issue(state_type="started", state_name="In Progress")
    text = format_issue(issue)
    assert text.startswith("* IN-PROGRESS ")


def test_todo_keyword_in_review():
    issue = _make_issue(state_type="started", state_name="In Review")
    text = format_issue(issue)
    assert text.startswith("* IN-REVIEW ")


def test_todo_keyword_done():
    issue = _make_issue(state_type="completed", state_name="Done")
    text = format_issue(issue)
    assert text.startswith("* DONE ")


def test_todo_keyword_cancelled():
    issue = _make_issue(state_type="cancelled", state_name="Cancelled")
    text = format_issue(issue)
    assert text.startswith("* DONE ")


def test_priority_urgent():
    issue = _make_issue(priority=1)
    text = format_issue(issue)
    assert "[#A]" in text


def test_priority_high():
    issue = _make_issue(priority=2)
    text = format_issue(issue)
    assert "[#B]" in text


def test_priority_medium():
    issue = _make_issue(priority=3)
    text = format_issue(issue)
    assert "[#C]" in text


def test_priority_low_omitted():
    issue = _make_issue(priority=4)
    text = format_issue(issue)
    assert "[#" not in text


def test_priority_none_omitted():
    issue = _make_issue(priority=0)
    text = format_issue(issue)
    assert "[#" not in text


def test_properties_drawer_contains_id_and_url():
    issue = _make_issue(identifier="ENG-42", url="https://linear.app/x/ENG-42")
    text = format_issue(issue)
    assert ":PROPERTIES:" in text
    assert ":LINEAR_ID: ENG-42" in text
    assert ":LINEAR_URL: https://linear.app/x/ENG-42" in text
    assert ":END:" in text


def test_write_org_file_contains_all_issues(tmp_path):
    output = tmp_path / "test.org"
    issues = [
        _make_issue(identifier="ENG-1", title="First issue"),
        _make_issue(identifier="ENG-2", title="Second issue"),
    ]
    write_org_file(output, issues, "test-source")
    content = output.read_text()
    assert "ENG-1" in content
    assert "ENG-2" in content


def test_write_org_file_has_sync_header(tmp_path):
    output = tmp_path / "test.org"
    write_org_file(output, [], "my-source")
    content = output.read_text()
    assert "Linear sync" in content
    assert "my-source" in content


def test_write_org_file_overwrites_existing(tmp_path):
    output = tmp_path / "test.org"
    output.write_text("old content")
    write_org_file(output, [_make_issue(identifier="NEW-1")], "src")
    content = output.read_text()
    assert "old content" not in content
    assert "NEW-1" in content
```

- [ ] **Step 2: Run tests to confirm they fail**

```
bazel test //py/linear_org_sync:linear_org_sync_test --test_filter="org_writer_test" --test_output=short
```

Expected: FAILED with `ModuleNotFoundError: No module named 'py.linear_org_sync.org_writer'`

- [ ] **Step 3: Implement org_writer.py**

Create `py/linear_org_sync/org_writer.py`:

```python
from __future__ import annotations

import pathlib
from datetime import datetime

from pydantic import BaseModel

_PRIORITY_MAP = {
    1: "A",  # urgent
    2: "B",  # high
    3: "C",  # medium
}


class Issue(BaseModel):
    identifier: str
    title: str
    priority: int
    url: str
    state_name: str
    state_type: str


def _org_todo_keyword(issue: Issue) -> str:
    if issue.state_type in ("completed", "cancelled"):
        return "DONE"
    if issue.state_type == "started":
        if "review" in issue.state_name.lower():
            return "IN-REVIEW"
        return "IN-PROGRESS"
    return "TODO"


def _org_priority(priority: int) -> str:
    letter = _PRIORITY_MAP.get(priority)
    if letter:
        return f" [#{letter}]"
    return ""


def format_issue(issue: Issue) -> str:
    keyword = _org_todo_keyword(issue)
    priority = _org_priority(issue.priority)
    return (
        f"* {keyword}{priority} {issue.title}\n"
        f"  :PROPERTIES:\n"
        f"  :LINEAR_ID: {issue.identifier}\n"
        f"  :LINEAR_URL: {issue.url}\n"
        f"  :END:\n"
    )


def write_org_file(
    path: pathlib.Path, issues: list[Issue], source_label: str
) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"# Linear sync: {source_label} — {timestamp}\n\n"
    content = header + "".join(format_issue(i) for i in issues)
    path.write_text(content)
```

- [ ] **Step 4: Run org_writer tests and confirm they pass**

```
bazel test //py/linear_org_sync:linear_org_sync_test --test_filter="org_writer_test" --test_output=short
```

Expected: all 14 org_writer tests PASS.

- [ ] **Step 5: Commit**

```bash
git add py/linear_org_sync/org_writer.py py/linear_org_sync/org_writer_test.py
git commit -m "feat: add org_writer to format Linear issues as org headings"
```

---

## Task 4: Create linear_client.py with tests (TDD)

**Files:**
- Create: `py/linear_org_sync/linear_client.py`
- Create: `py/linear_org_sync/linear_client_test.py`

- [ ] **Step 1: Write the failing tests**

Create `py/linear_org_sync/linear_client_test.py`:

```python
from unittest.mock import MagicMock, patch

from py.linear_org_sync.linear_client import LinearClient


def _mock_response(data: dict) -> MagicMock:
    response = MagicMock()
    response.json.return_value = {"data": data}
    response.raise_for_status.return_value = None
    return response


def _issue_node(
    identifier="ENG-1",
    title="Test",
    priority=0,
    url="https://linear.app/x/ENG-1",
    state_name="Todo",
    state_type="unstarted",
) -> dict:
    return {
        "identifier": identifier,
        "title": title,
        "priority": priority,
        "url": url,
        "state": {"name": state_name, "type": state_type},
    }


def test_get_assigned_issues_returns_issues():
    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value = _mock_response({
            "viewer": {
                "assignedIssues": {
                    "nodes": [
                        _issue_node("ENG-1", "Fix bug", 2,
                                    state_name="In Progress", state_type="started"),
                    ]
                }
            }
        })
        client = LinearClient("lin_api_test")
        issues = client.get_assigned_issues()
        assert len(issues) == 1
        assert issues[0].identifier == "ENG-1"
        assert issues[0].priority == 2
        assert issues[0].state_type == "started"


def test_get_assigned_issues_empty():
    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value = _mock_response({
            "viewer": {"assignedIssues": {"nodes": []}}
        })
        client = LinearClient("lin_api_test")
        issues = client.get_assigned_issues()
        assert issues == []


def test_get_team_issues_returns_issues():
    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value = _mock_response({
            "teams": {
                "nodes": [{
                    "issues": {
                        "nodes": [_issue_node("ENG-2", "Team task")]
                    }
                }]
            }
        })
        client = LinearClient("lin_api_test")
        issues = client.get_team_issues("eng")
        assert len(issues) == 1
        assert issues[0].identifier == "ENG-2"


def test_get_team_issues_unknown_slug_returns_empty():
    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value = _mock_response({
            "teams": {"nodes": []}
        })
        client = LinearClient("lin_api_test")
        issues = client.get_team_issues("nonexistent")
        assert issues == []


def test_get_project_issues_returns_issues():
    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value = _mock_response({
            "project": {
                "issues": {
                    "nodes": [
                        _issue_node("ENG-3", "Project task", 1,
                                    state_name="In Review", state_type="started"),
                    ]
                }
            }
        })
        client = LinearClient("lin_api_test")
        issues = client.get_project_issues("proj-id-123")
        assert len(issues) == 1
        assert issues[0].state_name == "In Review"
        assert issues[0].priority == 1


def test_linear_client_context_manager_closes():
    with patch("httpx.Client.post") as mock_post, \
         patch("httpx.Client.close") as mock_close:
        mock_post.return_value = _mock_response({
            "viewer": {"assignedIssues": {"nodes": []}}
        })
        with LinearClient("lin_api_test") as client:
            client.get_assigned_issues()
        mock_close.assert_called_once()
```

- [ ] **Step 2: Run tests to confirm they fail**

```
bazel test //py/linear_org_sync:linear_org_sync_test --test_filter="linear_client_test" --test_output=short
```

Expected: FAILED with `ModuleNotFoundError: No module named 'py.linear_org_sync.linear_client'`

- [ ] **Step 3: Implement linear_client.py**

Create `py/linear_org_sync/linear_client.py`:

```python
from __future__ import annotations

import httpx

from py.linear_org_sync.org_writer import Issue

_LINEAR_API_URL = "https://api.linear.app/graphql"

_ISSUE_FIELDS = """
    identifier
    title
    priority
    url
    state {
        name
        type
    }
"""

_ASSIGNED_QUERY = f"""
query AssignedIssues {{
    viewer {{
        assignedIssues(
            filter: {{ state: {{ type: {{ nin: ["completed", "cancelled"] }} }} }}
        ) {{
            nodes {{ {_ISSUE_FIELDS} }}
        }}
    }}
}}
"""

_TEAM_QUERY = f"""
query TeamIssues($slug: String!) {{
    teams(filter: {{ key: {{ eq: $slug }} }}) {{
        nodes {{
            issues(
                filter: {{ state: {{ type: {{ nin: ["completed", "cancelled"] }} }} }}
            ) {{
                nodes {{ {_ISSUE_FIELDS} }}
            }}
        }}
    }}
}}
"""

_PROJECT_QUERY = f"""
query ProjectIssues($id: String!) {{
    project(id: $id) {{
        issues(
            filter: {{ state: {{ type: {{ nin: ["completed", "cancelled"] }} }} }}
        ) {{
            nodes {{ {_ISSUE_FIELDS} }}
        }}
    }}
}}
"""


def _parse_issue(node: dict) -> Issue:
    return Issue(
        identifier=node["identifier"],
        title=node["title"],
        priority=node["priority"],
        url=node["url"],
        state_name=node["state"]["name"],
        state_type=node["state"]["type"],
    )


class LinearClient:
    def __init__(self, api_key: str) -> None:
        self._client = httpx.Client(
            headers={"Authorization": api_key},
            timeout=30.0,
        )

    def _query(self, query: str, variables: dict | None = None) -> dict:
        response = self._client.post(
            _LINEAR_API_URL,
            json={"query": query, "variables": variables or {}},
        )
        response.raise_for_status()
        return response.json()

    def get_assigned_issues(self) -> list[Issue]:
        data = self._query(_ASSIGNED_QUERY)
        nodes = data["data"]["viewer"]["assignedIssues"]["nodes"]
        return [_parse_issue(n) for n in nodes]

    def get_team_issues(self, slug: str) -> list[Issue]:
        data = self._query(_TEAM_QUERY, {"slug": slug})
        teams = data["data"]["teams"]["nodes"]
        if not teams:
            return []
        nodes = teams[0]["issues"]["nodes"]
        return [_parse_issue(n) for n in nodes]

    def get_project_issues(self, project_id: str) -> list[Issue]:
        data = self._query(_PROJECT_QUERY, {"id": project_id})
        nodes = data["data"]["project"]["issues"]["nodes"]
        return [_parse_issue(n) for n in nodes]

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> LinearClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
```

- [ ] **Step 4: Run linear_client tests and confirm they pass**

```
bazel test //py/linear_org_sync:linear_org_sync_test --test_filter="linear_client_test" --test_output=short
```

Expected: all 6 linear_client tests PASS.

- [ ] **Step 5: Run the full test suite**

```
bazel test //py/linear_org_sync:linear_org_sync_test --test_output=short
```

Expected: all tests PASS (7 config + 14 org_writer + 6 linear_client = 27 total, though Bazel may report slightly different grouping).

- [ ] **Step 6: Commit**

```bash
git add py/linear_org_sync/linear_client.py py/linear_org_sync/linear_client_test.py
git commit -m "feat: add LinearClient for Linear GraphQL queries"
```

---

## Task 5: Create __main__.py and wire up the binary

**Files:**
- Create: `py/linear_org_sync/__main__.py`

- [ ] **Step 1: Create __main__.py**

Create `py/linear_org_sync/__main__.py`:

```python
from __future__ import annotations

import pathlib

from absl import app, flags, logging

from py.linear_org_sync.config import AssignedSource, ProjectSource, TeamSource, load_config
from py.linear_org_sync.linear_client import LinearClient
from py.linear_org_sync.org_writer import write_org_file

FLAGS = flags.FLAGS
flags.DEFINE_string("config", None, "Path to config.yaml")
flags.mark_flag_as_required("config")


def main(argv: list[str]) -> None:
    del argv
    config_path = pathlib.Path(FLAGS.config).expanduser()
    config = load_config(config_path)

    with LinearClient(config.linear.api_key) as client:
        for source in config.sources:
            output_path = config.config_dir / source.output_file
            if isinstance(source, AssignedSource):
                issues = client.get_assigned_issues()
                label = "assigned"
            elif isinstance(source, TeamSource):
                issues = client.get_team_issues(source.slug)
                label = f"team:{source.slug}"
            elif isinstance(source, ProjectSource):
                issues = client.get_project_issues(source.id)
                label = f"project:{source.id}"
            else:
                logging.warning("Unknown source type: %s", source)
                continue
            write_org_file(output_path, issues, label)
            logging.info("Wrote %d issues to %s", len(issues), output_path)


app.run(main)
```

- [ ] **Step 2: Verify the binary builds**

```
bazel build //py/linear_org_sync
```

Expected: build succeeds with no errors.

- [ ] **Step 3: Commit**

```bash
git add py/linear_org_sync/__main__.py
git commit -m "feat: add linear_org_sync entry point"
```

---

## Task 6: Create sample config.yaml and smoke test

**Files:**
- Create: `~/org/linear/config.yaml`

- [ ] **Step 1: Create the output directory and sample config**

```bash
mkdir -p ~/org/linear
```

Create `~/org/linear/config.yaml`:

```yaml
linear:
  api_key: "lin_api_REPLACE_WITH_YOUR_KEY"
  sync_interval_minutes: 60  # informational; timer interval is set in the systemd .timer file

sources:
  - type: assigned
    output_file: assigned.org

  # Uncomment and configure additional sources as needed:
  # - type: team
  #   slug: eng
  #   output_file: eng.org

  # - type: project
  #   id: YOUR_PROJECT_ID_HERE
  #   output_file: myproject.org
```

- [ ] **Step 2: Get your Linear API key**

In Linear: Settings → API → Personal API keys → Create key. Copy the `lin_api_...` value into `~/org/linear/config.yaml`.

- [ ] **Step 3: Run the sync manually to verify end-to-end**

From the monorepo root:

```
bazel run //py/linear_org_sync -- --config ~/org/linear/config.yaml
```

Expected:
```
I0404 10:00:00.000000 12345 __main__.py:30] Wrote 7 issues to /home/tellett/org/linear/assigned.org
```

- [ ] **Step 4: Verify the org file format**

```bash
head -20 ~/org/linear/assigned.org
```

Expected output (content will vary):
```
# Linear sync: assigned — 2026-04-04 10:00

* TODO [#B] Fix widget rendering
  :PROPERTIES:
  :LINEAR_ID: ENG-456
  :LINEAR_URL: https://linear.app/your-org/issue/ENG-456
  :END:
```

---

## Task 7: Update Doom Emacs config

**Files:**
- Modify: `~/.config/doom/config.el`

- [ ] **Step 1: Add the org-agenda-files snippet**

Edit `~/.config/doom/config.el`. After the `(setq org-directory "~/org/")` line, add:

```elisp
(after! org
  (setq org-agenda-files
        (append org-agenda-files
                (directory-files "~/org/linear" t "\\.org$"))))
```

The full relevant section of `config.el` should look like:

```elisp
(setq org-directory "~/org/")

(after! org
  (setq org-agenda-files
        (append org-agenda-files
                (directory-files "~/org/linear" t "\\.org$"))))
```

- [ ] **Step 2: Reload Doom config**

In Emacs, run: `M-x doom/reload`

- [ ] **Step 3: Verify Linear files appear in agenda**

In Emacs, run `M-x org-agenda` → press `a` for the week view.

Expected: your Linear issues appear alongside any other org tasks.

---

## Task 8: Create and enable the systemd user timer

**Files:**
- Create: `~/.config/systemd/user/linear-org-sync.service`
- Create: `~/.config/systemd/user/linear-org-sync.timer`

- [ ] **Step 1: Create the service unit**

Create `~/.config/systemd/user/linear-org-sync.service`:

```ini
[Unit]
Description=Sync Linear issues to org-mode files

[Service]
Type=oneshot
WorkingDirectory=%h/src/github/tellett/monorepo
ExecStart=/home/tellett/go/bin/bazel run //py/linear_org_sync -- --config %h/org/linear/config.yaml
StandardOutput=journal
StandardError=journal
```

- [ ] **Step 2: Create the timer unit**

Create `~/.config/systemd/user/linear-org-sync.timer`:

```ini
[Unit]
Description=Run Linear org sync periodically

[Timer]
OnBootSec=5min
OnUnitActiveSec=1h
Persistent=true

[Install]
WantedBy=timers.target
```

- [ ] **Step 3: Reload systemd and enable the timer**

```bash
systemctl --user daemon-reload
systemctl --user enable --now linear-org-sync.timer
```

Expected:
```
Created symlink ~/.config/systemd/user/timers.target.wants/linear-org-sync.timer → ~/.config/systemd/user/linear-org-sync.timer.
```

- [ ] **Step 4: Verify the timer is active**

```bash
systemctl --user status linear-org-sync.timer
```

Expected: `Active: active (waiting)` with a next trigger time shown.

- [ ] **Step 5: Trigger a manual run via systemd to verify the service works**

```bash
systemctl --user start linear-org-sync.service
journalctl --user -u linear-org-sync.service -n 20
```

Expected: log lines showing issues written to org files, service exits cleanly.

- [ ] **Step 6: Copy unit files into the monorepo for reference and commit**

```bash
mkdir -p ~/src/github/tellett/monorepo/docs/systemd
cp ~/.config/systemd/user/linear-org-sync.* ~/src/github/tellett/monorepo/docs/systemd/
```

```bash
git add docs/systemd/
git commit -m "docs: add reference systemd unit files for linear org sync"
```
