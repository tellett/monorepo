# Bazel 9 Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade from Aspect's Bazel 8 distribution to upstream Bazel 9 (latest 9.x patch) and bump all 13 `bazel_dep` entries in `MODULE.bazel` to their latest BCR versions, in a single commit on `main`.

**Architecture:** All changes are to build configuration files — no application code changes expected. The upgrade touches `.bazelversion`, `.bazeliskrc`, `.bazelrc`, `.aspect/bazelrc/`, and `MODULE.bazel`. Any rule API breakage discovered during verification is fixed in the same pass.

**Tech Stack:** Bazel 9.x, Bazelisk, Bazel Central Registry (BCR), Aspect CLI

---

### Task 1: Look up latest versions

No file changes. Gather the version strings needed for Task 2.

- [ ] **Step 1: Find latest Bazel 9.x release**

```bash
gh release list -R bazelbuild/bazel --limit 20 | grep "^v9\." | head -5
```

Note the highest `9.x.y` version (e.g., `9.0.1`).

- [ ] **Step 2: Find latest BCR versions for all 13 deps**

```bash
for mod in aspect_bazel_lib aspect_rules_lint buildifier_prebuilt rules_multitool \
            rules_python rules_python_gazelle_plugin aspect_rules_py rules_uv \
            rules_go gazelle rules_shell rules_oci platforms; do
  latest=$(curl -s "https://bcr.bazel.build/modules/${mod}/metadata.json" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(sorted(d['versions'])[-1])")
  echo "${mod}: ${latest}"
done
```

Record all 13 version strings. You will fill them in during Task 2, Step 5.

---

### Task 2: Apply all config changes

- [ ] **Step 1: Update `.bazelversion`**

Replace the file content with the latest 9.x version found in Task 1 (e.g.):

```
9.0.1
```

- [ ] **Step 2: Clear `.bazeliskrc`**

Remove both lines — Bazelisk falls back to `.bazelversion` and downloads from GitHub Releases:

```bash
> /home/tellett/src/github/tellett/monorepo/.bazeliskrc
```

The file stays (empty) so the path doesn't become a dangling reference in any script.

- [ ] **Step 3: Update `.bazelrc`**

Replace the full file with:

```
# Import Aspect bazelrc presets
import %workspace%/.aspect/bazelrc/bazel9.bazelrc
import %workspace%/.aspect/bazelrc/convenience.bazelrc
import %workspace%/.aspect/bazelrc/correctness.bazelrc
import %workspace%/.aspect/bazelrc/debug.bazelrc
import %workspace%/.aspect/bazelrc/performance.bazelrc

### YOUR PROJECT SPECIFIC OPTIONS GO HERE ###

# To stamp release builds, run with
# --config=release
common:release --stamp --workspace_status_command=./tools/workspace_status.sh


# Load any settings & overrides specific to the current user from `.aspect/bazelrc/user.bazelrc`.
# This file should appear in `.gitignore` so that settings are not shared with team members. This
# should be last statement in this config so the user configuration is able to overwrite flags from
# this file. See https://bazel.build/configure/best-practices#bazelrc-file.
try-import %workspace%/.aspect/bazelrc/user.bazelrc
```

Two intentional changes vs the current file:
- `bazel8.bazelrc` → `bazel9.bazelrc`
- `--noexperimental_merged_skyframe_analysis_execution` line removed (Bazel 8 skymeld workaround; this flag does not exist in Bazel 9 and causes a startup error)

- [ ] **Step 4: Create `.aspect/bazelrc/bazel9.bazelrc`**

```bash
cp .aspect/bazelrc/bazel8.bazelrc .aspect/bazelrc/bazel9.bazelrc
```

`bazel8.bazelrc` is empty, so `bazel9.bazelrc` starts empty too. Leave it as-is unless Aspect publishes Bazel 9-specific presets (check `github.com/aspect-build/bazel-lib` → `bazelrc/` directory for any `bazel9.bazelrc` content to copy in).

- [ ] **Step 5: Update `MODULE.bazel` dep versions**

Replace all 13 `bazel_dep` lines at the top of `MODULE.bazel` with the versions from Task 1. Only the version strings change; everything else in the file stays identical:

```python
bazel_dep(name = "aspect_bazel_lib", version = "<from Task 1>")
bazel_dep(name = "aspect_rules_lint", version = "<from Task 1>")
bazel_dep(name = "buildifier_prebuilt", version = "<from Task 1>")
bazel_dep(name = "rules_multitool", version = "<from Task 1>")
bazel_dep(name = "rules_python", version = "<from Task 1>")
bazel_dep(name = "rules_python_gazelle_plugin", version = "<from Task 1>")
bazel_dep(name = "aspect_rules_py", version = "<from Task 1>")
bazel_dep(name = "rules_uv", version = "<from Task 1>")
bazel_dep(name = "rules_go", version = "<from Task 1>")
bazel_dep(name = "gazelle", version = "<from Task 1>")
bazel_dep(name = "rules_shell", version = "<from Task 1>")
bazel_dep(name = "rules_oci", version = "<from Task 1>")
bazel_dep(name = "platforms", version = "<from Task 1>")
```

---

### Task 3: Validate MODULE.bazel with `bazel mod tidy`

- [ ] **Step 1: Run `bazel mod tidy`**

```bash
~/go/bin/bazel mod tidy
```

Expected: exits 0, possibly updates the lock section of `MODULE.bazel`. If there are transitive version conflicts, Bazel prints which modules disagree. Resolve by accepting the version Bazel requests (or finding a newer BCR version that satisfies all constraints), then re-run until it exits 0.

---

### Task 4: Full verification and fix

Run each verification command. Fix any failures before moving to the next one.

- [ ] **Step 1: Build everything**

```bash
~/go/bin/bazel build //...
```

Expected: exits 0. Common Bazel 9 failure patterns to watch for:

- **Unknown flag errors** — if `.aspect/bazelrc/performance.bazelrc` or `correctness.bazelrc` use flags prefixed with `--experimental_` that were promoted or removed in Bazel 9, Bazel will error at startup. Fix: remove the `--experimental_` prefix or delete the line. The two candidates are `--experimental_reuse_sandbox_directories` (performance.bazelrc) and `--experimental_fetch_all_coverage_outputs` (correctness.bazelrc).
- **Load errors from `tools/lint/BUILD.bazel`** — if `rules_go` renamed `TOOLS_NOGO`, update the `load` statement to match the new symbol name/path.
- **Load errors from `tools/lint/linters.bzl`** — if `aspect_rules_lint` changed `lint_ruff_aspect`, `lint_shellcheck_aspect`, or `lint_test` signatures, update the call sites to match.
- **`pip.parse` attribute errors** — if `rules_python` renamed `requirements_lock`, update `MODULE.bazel` to use the new attribute name.
- **`oci.pull` attribute errors** — if `rules_oci` changed accepted attributes, update the `oci.pull` calls in `MODULE.bazel`.

- [ ] **Step 2: Run all tests**

```bash
~/go/bin/bazel test //...
```

Expected: all tests pass.

- [ ] **Step 3: Run lint**

```bash
aspect lint //...
```

Expected: no violations. If the lint aspect wiring fails (load error in `tools/lint/linters.bzl`), this would have already surfaced in Step 1 — fix there.

- [ ] **Step 4: Run formatter**

```bash
aspect run format
```

Expected: exits 0 (all files already formatted). If the formatter toolchain fails to resolve, check that `buildifier_prebuilt` still exposes the same `@buildifier_prebuilt//:buildifier` target.

---

### Task 5: Commit

- [ ] **Step 1: Stage all changed files**

```bash
git status  # review the full diff
git add .bazelversion .bazeliskrc .bazelrc MODULE.bazel \
    .aspect/bazelrc/bazel9.bazelrc
# If bazel mod tidy or fixing breakage modified additional files, add them too
```

- [ ] **Step 2: Commit**

```bash
git commit -m "$(cat <<'EOF'
build: upgrade to upstream Bazel 9 and bump all MODULE.bazel deps

- Switch from Aspect Bazel distribution (aspect/2024.51.11) to upstream
  Bazel 9.x; remove BAZELISK_BASE_URL override
- Add bazel9.bazelrc preset, drop bazel8.bazelrc import
- Remove --noexperimental_merged_skyframe_analysis_execution (Bazel 8 workaround)
- Bump all 13 bazel_dep entries to latest BCR versions

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```
