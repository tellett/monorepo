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
