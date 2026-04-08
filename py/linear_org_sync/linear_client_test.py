from unittest.mock import MagicMock, patch

from py.linear_org_sync.linear_client import LinearClient, _extract_links


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


def test_get_assigned_issues_returns_issues():
    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value = _mock_response(
            {
                "viewer": {
                    "assignedIssues": {
                        "nodes": [
                            _issue_node(
                                "ENG-1",
                                "Fix bug",
                                2,
                                state_name="In Progress",
                                state_type="started",
                            ),
                        ]
                    }
                }
            }
        )
        client = LinearClient("lin_api_test")
        issues = client.get_assigned_issues()
        assert len(issues) == 1
        assert issues[0].identifier == "ENG-1"
        assert issues[0].priority == 2
        assert issues[0].state_type == "started"


def test_get_assigned_issues_empty():
    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value = _mock_response(
            {"viewer": {"assignedIssues": {"nodes": []}}}
        )
        client = LinearClient("lin_api_test")
        issues = client.get_assigned_issues()
        assert issues == []


def test_get_team_issues_returns_issues():
    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value = _mock_response(
            {
                "teams": {
                    "nodes": [
                        {"issues": {"nodes": [_issue_node("ENG-2", "Team task")]}}
                    ]
                }
            }
        )
        client = LinearClient("lin_api_test")
        issues = client.get_team_issues("eng")
        assert len(issues) == 1
        assert issues[0].identifier == "ENG-2"


def test_get_team_issues_unknown_slug_returns_empty():
    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value = _mock_response({"teams": {"nodes": []}})
        client = LinearClient("lin_api_test")
        issues = client.get_team_issues("nonexistent")
        assert issues == []


def test_get_project_issues_returns_issues():
    with patch("httpx.Client.post") as mock_post:
        mock_post.return_value = _mock_response(
            {
                "project": {
                    "issues": {
                        "nodes": [
                            _issue_node(
                                "ENG-3",
                                "Project task",
                                1,
                                state_name="In Review",
                                state_type="started",
                            ),
                        ]
                    }
                }
            }
        )
        client = LinearClient("lin_api_test")
        issues = client.get_project_issues("proj-id-123")
        assert len(issues) == 1
        assert issues[0].state_name == "In Review"
        assert issues[0].priority == 1


def test_linear_client_context_manager_closes():
    with (
        patch("httpx.Client.post") as mock_post,
        patch("httpx.Client.close") as mock_close,
    ):
        mock_post.return_value = _mock_response(
            {"viewer": {"assignedIssues": {"nodes": []}}}
        )
        with LinearClient("lin_api_test") as client:
            client.get_assigned_issues()
        mock_close.assert_called_once()


def test_extract_links_pr_url_goes_to_github_prs():
    node = _issue_node(
        attachments=[{"url": "https://github.com/org/repo/pull/9", "title": "My PR"}]
    )
    prs, others = _extract_links(node)
    assert len(prs) == 1
    assert prs[0].url == "https://github.com/org/repo/pull/9"
    assert prs[0].title == "My PR"
    assert others == []


def test_extract_links_non_pr_url_goes_to_other_links():
    node = _issue_node(
        attachments=[{"url": "https://notion.so/some-doc", "title": "Doc"}]
    )
    prs, others = _extract_links(node)
    assert prs == []
    assert len(others) == 1
    assert others[0].url == "https://notion.so/some-doc"
    assert others[0].title == "Doc"


def test_extract_links_github_issue_url_goes_to_other_links():
    node = _issue_node(
        attachments=[
            {"url": "https://github.com/org/repo/issues/42", "title": "Issue"}
        ]
    )
    prs, others = _extract_links(node)
    assert prs == []
    assert len(others) == 1


def test_extract_links_description_url_extracted():
    node = _issue_node(
        description="See https://notion.so/doc for context",
    )
    prs, others = _extract_links(node)
    assert len(others) == 1
    assert others[0].url == "https://notion.so/doc"
    assert others[0].title == "https://notion.so/doc"


def test_extract_links_deduplication_prefers_attachment_title():
    node = _issue_node(
        attachments=[{"url": "https://github.com/org/repo/pull/9", "title": "My PR"}],
        description="Check https://github.com/org/repo/pull/9 for details",
    )
    prs, others = _extract_links(node)
    assert len(prs) == 1
    assert prs[0].title == "My PR"


def test_extract_links_no_attachments_no_description_returns_empty():
    node = _issue_node()
    prs, others = _extract_links(node)
    assert prs == []
    assert others == []


def test_extract_links_description_strips_trailing_punctuation():
    node = _issue_node(description="See https://notion.so/doc. For context")
    prs, others = _extract_links(node)
    assert len(others) == 1
    assert others[0].url == "https://notion.so/doc"
