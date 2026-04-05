# Linear → org-mode Sync: Design

**Date:** 2026-04-04
**Status:** Approved

## Overview

A read-only sync from Linear to org-mode. A Python script (invoked via `bazel run`) queries the Linear GraphQL API and writes one `.org` file per configured source (team or project) into `~/org/linear/`. A systemd user timer runs the sync hourly. Doom Emacs auto-discovers the resulting files for the org agenda.

No writes are made back to Linear. org-mode is a read-only view.

---

## Architecture

```
~/org/linear/config.yaml          ← config (API key, sources, interval)
        │
        ▼
~/src/github/tellett/monorepo/py/linear_org_sync/
        │   __main__.py           ← arg parsing, orchestration
        │   config.py             ← loads config.yaml, validates structure
        │   linear_client.py      ← GraphQL queries to Linear API
        │   org_writer.py         ← renders issues → org headings, writes files
        │   BUILD.bazel           ← py_binary target
        │
        ▼
~/org/linear/
        assigned.org
        <team-slug>.org           ← one file per team source
        <project-name>.org        ← one file per project source
        │
        ▼
Doom Emacs org-agenda             ← auto-discovers ~/org/linear/*.org
        │
        ▼
systemd user timer                ← runs bazel run //py/linear_org_sync hourly
```

---

## Config File

Location: `~/org/linear/config.yaml`

The script infers the output directory as the directory containing the config file. All `.org` output files are written there.

```yaml
linear:
  api_key: "lin_api_..."
  sync_interval_minutes: 60  # informational; timer interval is set in the systemd .timer file

sources:
  - type: assigned
    output_file: assigned.org

  - type: team
    slug: eng
    output_file: eng.org

  - type: project
    id: abc123
    output_file: project-foo.org
```

**Source types:**

| Type | Required fields | Description |
|------|----------------|-------------|
| `assigned` | — | Open issues assigned to the API key's user |
| `team` | `slug`, `output_file` | All open issues for a team |
| `project` | `id`, `output_file` | All open issues for a project |

At most one `assigned` source should be configured.

---

## Data Model

Each Linear issue becomes an org heading:

```org
* TODO [#B] Fix widget rendering
  :PROPERTIES:
  :LINEAR_ID: ENG-456
  :LINEAR_URL: https://linear.app/your-org/issue/ENG-456
  :END:
```

**Priority mapping (Linear → org):**

| Linear priority | Org priority |
|-----------------|-------------|
| urgent | `#A` |
| high | `#B` |
| medium | `#C` |
| low / none | (omitted) |

**Status mapping (Linear → org TODO keyword):**

| Linear status | Org keyword |
|---------------|-------------|
| In Progress | `IN-PROGRESS` |
| In Review | `IN-REVIEW` |
| Done / Cancelled | `DONE` |
| Everything else | `TODO` |

Files are fully rewritten on each sync run (not incrementally patched). Each file begins with a header comment indicating the last sync time.

---

## Python Module

```
py/linear_org_sync/
├── BUILD.bazel
├── __main__.py        ← CLI entry point, orchestrates config → client → writer
├── config.py          ← parses and validates config.yaml
├── linear_client.py   ← Linear GraphQL API queries
└── org_writer.py      ← converts issue data to org format, writes files
```

**`BUILD.bazel`:**

```python
py_binary(
    name = "linear_org_sync",
    srcs = glob(["*.py"]),
    deps = [
        "//requirements:httpx",
        "//requirements:pydantic",
        "//requirements:pyyaml",
    ],
    main = "__main__.py",
    visibility = ["//visibility:private"],
)
```

Dependencies: `httpx` (Linear GraphQL over HTTPS), `pyyaml` (config parsing), `pydantic` (config and data model validation). All require entries in the monorepo's requirements pinning.

Invoked as:
```
bazel run //py/linear_org_sync -- --config ~/org/linear/config.yaml
```

---

## Doom Emacs Integration

Added to `~/.config/doom/config.el`:

```elisp
(after! org
  (setq org-agenda-files
        (append org-agenda-files
                (directory-files "~/org/linear" t "\\.org$"))))
```

Auto-discovers all `.org` files in `~/org/linear/` — no manual update needed when sources are added or removed.

---

## Systemd User Timer

Two files under `~/.config/systemd/user/`:

**`linear-org-sync.service`:**
```ini
[Unit]
Description=Sync Linear issues to org-mode files

[Service]
Type=oneshot
WorkingDirectory=%h/src/github/tellett/monorepo
ExecStart=/home/tellett/go/bin/bazel run //py/linear_org_sync -- --config %h/org/linear/config.yaml
StandardOutput=journal
StandardError=journal
```

**`linear-org-sync.timer`:**
```ini
[Unit]
Description=Run Linear org sync periodically

[Timer]
OnBootSec=5min
OnUnitActiveSec=1h
Persistent=true

[Install]
WantedBy=timers.target
```

`Persistent=true` ensures a missed sync (e.g. machine was off) runs once on next boot.

Enable with:
```
systemctl --user enable --now linear-org-sync.timer
```

Logs via:
```
journalctl --user -u linear-org-sync.service
```

---

## Out of Scope

- Writing back to Linear from org-mode
- Conflict resolution
- Incremental/delta syncing (full rewrite per run is sufficient at hourly cadence)
- Pulling issue descriptions or comments
