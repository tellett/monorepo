import pathlib

from py.linear_org_sync.org_writer import Issue, Link, format_issue, write_org_file


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


def test_format_issue_no_links_produces_no_link_properties():
    issue = _make_issue()
    text = format_issue(issue)
    assert ":GITHUB_PR" not in text
    assert ":OTHER_LINK" not in text


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
