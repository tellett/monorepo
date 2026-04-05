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
