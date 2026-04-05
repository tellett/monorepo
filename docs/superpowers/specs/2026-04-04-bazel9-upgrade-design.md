# Bazel 9 Upgrade Design

**Date:** 2026-04-04
**Status:** Approved

## Goal

Upgrade this monorepo from Aspect's Bazel 8 distribution (`aspect/2024.51.11`) to upstream Bazel 9.x (latest patch release at implementation time), and bump all 13 `bazel_dep` entries in `MODULE.bazel` to their latest published versions on the Bazel Central Registry.

## Approach

Single big-bang commit on `main` covering all changes. No feature branch.

## Changes

### 1. Bazel version & Bazelisk config

**`.bazelversion`** — set to the highest `9.x.y` available on GitHub Releases at implementation time.

**`.bazeliskrc`** — remove both lines (`BAZELISK_BASE_URL` and `USE_BAZEL_VERSION`). With no override, Bazelisk falls back to `.bazelversion` and downloads from the default GitHub Releases URL. File can be left empty or deleted.

**`.bazelrc`** — two changes:
- Change `import %workspace%/.aspect/bazelrc/bazel8.bazelrc` → `bazel9.bazelrc`
- Remove the `--noexperimental_merged_skyframe_analysis_execution` workaround (a Bazel 8 bug fix; this flag may not exist in Bazel 9 and will cause a startup error if left in)

### 2. MODULE.bazel — dependency bumps

All 13 `bazel_dep` entries bumped to latest BCR versions at implementation time:

| Dep | Current | Notes |
|---|---|---|
| `aspect_bazel_lib` | 2.11.0 | Active development |
| `aspect_rules_lint` | 1.0.8 | Check for lint API changes |
| `buildifier_prebuilt` | 8.0.0 | Tracks buildifier releases, not Bazel |
| `rules_multitool` | 1.0.0 | Likely stable |
| `rules_python` | 1.1.0 | Check pip extension API changes |
| `rules_python_gazelle_plugin` | 1.1.0 | Keep in sync with `rules_python` major version |
| `aspect_rules_py` | 1.1.0 | Check `py_binary`/`py_test` attribute changes |
| `rules_uv` | 0.51.0 | Active development |
| `rules_go` | 0.52.0 | Check nogo API changes |
| `gazelle` | 0.41.0 | Keep in sync with `rules_go` |
| `rules_shell` | 0.3.0 | Likely stable |
| `rules_oci` | 2.2.0 | Check `oci.pull` attribute changes |
| `platforms` | 0.0.11 | Minor bump expected |

After bumping, run `bazel mod tidy` to validate the lock and catch transitive dependency conflicts. Fix any breaking API changes (renamed attributes, changed extension APIs) in the same commit.

### 3. Verification

All of the following must pass before the commit is considered complete:

1. `bazel build //...` — full build graph resolves under Bazel 9
2. `bazel test //...` — all Python (pytest) and Go tests pass
3. `aspect lint //...` — ruff, shellcheck, nogo all wire up correctly
4. `aspect run format` — gofumpt, ruff, buildifier toolchain resolves
