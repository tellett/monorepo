# Design: linear_org_sync — Sort Issues by Priority then Alphabetically

**Date:** 2026-04-07
**Status:** Approved

## Summary

Add sorting to `write_org_file` in `py/linear_org_sync/org_writer.py` so that output org files list issues in priority order, with alphabetical ordering within each priority level.

## Sort Order

Linear priorities are integers:

| Value | Meaning     |
|-------|-------------|
| 1     | Urgent      |
| 2     | High        |
| 3     | Medium      |
| 4     | Low         |
| 0     | No priority |

"No priority" (`0`) sorts **last** — below low (`4`) — by remapping `0` → `5` in the sort key.

Within each priority level, issues are sorted case-insensitively by title.

## Implementation

One line added at the top of `write_org_file` in `py/linear_org_sync/org_writer.py`:

```python
issues = sorted(issues, key=lambda i: (i.priority if i.priority != 0 else 5, i.title.lower()))
```

- `sorted()` returns a new list; the caller's list is not mutated.
- No new functions, classes, or files required.

## Testing

Add cases to `py/linear_org_sync/org_writer_test.py`:

1. **Priority order** — issues with priorities 1, 2, 3, 4, 0 appear in that order in the output.
2. **Alphabetical within priority** — two issues at the same priority level appear alphabetically by title (case-insensitive).
3. **No-priority sorts last** — a no-priority (`0`) issue appears after a low-priority (`4`) issue.
