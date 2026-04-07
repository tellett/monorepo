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


def write_org_file(path: pathlib.Path, issues: list[Issue], source_label: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"# Linear sync: {source_label} — {timestamp}\n\n"
    content = header + "".join(format_issue(i) for i in issues)
    path.write_text(content)
