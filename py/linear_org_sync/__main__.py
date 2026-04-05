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
