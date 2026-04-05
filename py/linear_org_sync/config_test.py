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
