# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Toolchain

- **Bazel**: `~/go/bin/bazel` (v8.0.1 via Bazelisk), also available as `aspect` CLI
- **Python**: 3.12 hermetic interpreter managed by Bazel via `rules_python`; local tooling via `uv`
- **Go**: 1.23.5 at `/usr/local/go/bin`

## Common Commands

```bash
# Build
bazel build //...                        # Build everything
bazel build //go/hello                   # Build specific target
bazel build //py/linear_org_sync         # Build Python binary

# Test
bazel test //...                         # Run all tests
bazel test //py/linear_org_sync:linear_org_sync_test
bazel test //py/examples/hello_tests:hello_tests_test

# Format (Aspect wrapper around gofumpt, ruff, buildifier)
aspect run format                        # Format all code
aspect run format path/to/file          # Format a specific file

# Lint
aspect lint //...                        # Check lint violations

# BUILD file generation (run after adding/removing source files)
aspect configure                         # Update Go + Python BUILD files

# Dependency management
./tools/repin                            # Repin Python and Go dependencies
bazel run //:gazelle_python_manifest.update  # Update Python gazelle manifest
bazel mod tidy                           # Update MODULE.bazel lock
```

## Architecture

This is a polyglot Bazel monorepo with Go and Python. Bazel 8 (bzlmod) is used — `WORKSPACE.bazel` is empty and all dependencies are declared in `MODULE.bazel`.

### Go (`go/`)

Packages are reusable libraries built on top of external `github.com/tellett/gocode` module. Key patterns:
- Uber `fx` for dependency injection throughout
- `go.uber.org/zap` for structured logging
- Import paths use the full module: `example.com/monorepo/go/...`
- Gazelle generates `BUILD.bazel` files automatically

### Python (`py/`)

- `aspect_rules_py` (not `rules_python`) is the preferred rule set for `py_binary` and `py_test`
- Python import paths use the `py.` prefix (e.g., `from py.linear_org_sync.config import Config`)
- Test targets use `py_pytest_main` + `py_test` with `--import-mode=importlib`
- Runtime deps pinned in `requirements/runtime.txt`; all deps (including dev/test) in `requirements/all.txt`

### Key Applications

**`py/linear_org_sync/`** — Syncs Linear.app issues to Emacs org-mode files. Modules: `config.py` (pydantic config), `linear_client.py` (httpx-based GraphQL), `org_writer.py` (org-mode formatting). Reference systemd unit files in `docs/`.

**`go/hello/`** — Example HTTP server using fx DI, zap logging, and reusable handlers from `go/net/httpserver/`.

### Tooling (`tools/`)

- `tools/repin` — Shell script to update Python/Go dependencies
- `tools/workspace_status.sh` — Provides `STABLE_MONOREPO_VERSION` (YYYY.WW) and `STABLE_GIT_COMMIT` for stamped builds
- `tools/format/` — Wraps gofumpt, ruff, buildifier
- `tools/lint/` — rules_lint integration with nogo for Go

### Versioning

Releases use `YYYY.WW` git tags (e.g., `2026.14`). A weekly GitHub Actions workflow auto-tags `HEAD`. Use `--config=release` for stamped builds.
