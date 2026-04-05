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
