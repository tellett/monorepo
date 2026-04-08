from __future__ import annotations

import pathlib
from datetime import datetime

from pydantic import BaseModel

_PRIORITY_MAP = {
    1: "A",  # urgent
    2: "B",  # high
    3: "C",  # medium
}


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


def _link_properties(name: str, links: list[Link]) -> str:
    if not links:
        return ""
    if len(links) == 1:
        return f"  :{name}: {links[0].url}\n"
    return "".join(f"  :{name}_{i}: {link.url}\n" for i, link in enumerate(links, 1))


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


def write_org_file(path: pathlib.Path, issues: list[Issue], source_label: str) -> None:
    issues = sorted(issues, key=lambda i: (i.priority if i.priority != 0 else 5, i.title.lower()))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"# Linear sync: {source_label} — {timestamp}\n\n"
    content = header + "".join(format_issue(i) for i in issues)
    path.write_text(content)
