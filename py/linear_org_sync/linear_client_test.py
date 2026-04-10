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


def test_extract_links_markdown_link_with_url_as_label():
    # Observed in ENG-1124 OTHER_LINK_3 and CS-4 OTHER_LINK:
    # [https://url](https://url) produces url](url in the property value.
    node = _issue_node(
        description="See [https://www.site24x7.com/uptime-monitoring.html](https://www.site24x7.com/uptime-monitoring.html) for details",
    )
    prs, others = _extract_links(node)
    assert len(others) == 1
    assert others[0].url == "https://www.site24x7.com/uptime-monitoring.html"
    assert "](" not in others[0].url


def test_extract_links_markdown_link_with_prose_label():
    node = _issue_node(
        description="[click here](https://notion.so/some-doc) for details",
    )
    prs, others = _extract_links(node)
    assert len(others) == 1
    assert others[0].url == "https://notion.so/some-doc"
    assert others[0].title == "https://notion.so/some-doc"


def test_extract_links_markdown_link_label_url_differs_from_href():
    # When the label is a different URL to the href, only the href is extracted.
    # The label URL is intentionally discarded — we follow the link destination.
    node = _issue_node(
        description="[https://old.example.com](https://new.example.com) for context",
    )
    prs, others = _extract_links(node)
    assert len(others) == 1
    assert others[0].url == "https://new.example.com"


def test_extract_links_slack_format_url_with_label():
    # Observed in INC-34 OTHER_LINK_1: <http://url|label> → url|label>
    node = _issue_node(
        description="Check <http://discovery.k8s.io/v1|discovery.k8s.io/v1> for more",
    )
    prs, others = _extract_links(node)
    assert len(others) == 1
    assert others[0].url == "http://discovery.k8s.io/v1"
    assert others[0].title == "http://discovery.k8s.io/v1"
    assert "|" not in others[0].url
    assert ">" not in others[0].url


def test_extract_links_slack_format_with_trailing_quote():
    # Observed in INC-34 OTHER_LINK_2-4: <http://url|label>" → url|label>"
    node = _issue_node(
        description='<http://logging.gke.io/some_field|logging.gke.io/some_field>"',
    )
    prs, others = _extract_links(node)
    assert len(others) == 1
    assert others[0].url == "http://logging.gke.io/some_field"
    assert others[0].title == "http://logging.gke.io/some_field"
    assert '"' not in others[0].url
    assert ">" not in others[0].url


def test_extract_links_bare_url_with_trailing_angle_bracket():
    # Observed in ENG-1610 OTHER_LINK: url without opener < but still has trailing >
    node = _issue_node(
        description="https://github.com/org/repo/security/dependabot?q=is%3Aopen>",
    )
    prs, others = _extract_links(node)
    assert len(others) == 1
    assert others[0].url == "https://github.com/org/repo/security/dependabot?q=is%3Aopen"
    assert others[0].title == "https://github.com/org/repo/security/dependabot?q=is%3Aopen"
    assert ">" not in others[0].url


def test_extract_links_deduplication_slack_url_prefers_attachment_title():
    # Observed in ENG-1596: same PR in attachment (clean) and description (Slack-format).
    # Before fix: url != url> so both appear as GITHUB_PR_3 and GITHUB_PR_4.
    # After fix: both resolve to the same URL and deduplicate to one entry.
    node = _issue_node(
        attachments=[{"url": "https://github.com/org/repo/pull/9", "title": "My PR"}],
        description="See <https://github.com/org/repo/pull/9|My PR> for details",
    )
    prs, others = _extract_links(node)
    assert len(prs) == 1
    assert prs[0].url == "https://github.com/org/repo/pull/9"
    assert prs[0].title == "My PR"
    assert others == []
