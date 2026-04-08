# Design: linear_org_sync — Link Metadata on Org Headings

**Date:** 2026-04-08
**Status:** Approved

## Summary

Extend the Linear → org-mode sync to surface attached GitHub PRs and external documentation links as org `PROPERTIES` on each issue heading. Links are sourced from both the Linear `attachments` API field and URLs parsed from the issue `description` body.

---

## Data Model

A `Link` model holds a URL and display title:

```python
class Link(BaseModel):
    url: str
    title: str
```

`Issue` gains two new optional fields (default empty):

```python
class Issue(BaseModel):
    ...
    github_prs: list[Link] = []
    other_links: list[Link] = []
```

**Classification rule:** any URL matching `github\.com/.+/pull/\d+` is a GitHub PR and goes into `github_prs`. Everything else (GitHub issues, wikis, Notion, Google Docs, Confluence, arbitrary URLs) goes into `other_links`.

---

## GraphQL Changes

Two fields are added to `_ISSUE_FIELDS` in `linear_client.py`:

```graphql
description
attachments {
    nodes {
        title
        url
    }
}
```

`_parse_issue` is extended to:

1. Collect `(url, title)` pairs from `attachments.nodes`
2. Extract URLs from `description` markdown via regex; use the URL as both `url` and `title` (raw description URLs have no label)
3. Deduplicate by URL — a link appearing in both attachments and description is kept once, preferring the attachment's title
4. Classify each URL into `github_prs` or `other_links`

---

## Org Output Format

Links are rendered as additional `PROPERTIES` entries. Issues with no links are unchanged.

**Single link of a type** — bare key (no numeric suffix):

```org
* TODO [#B] Fix widget rendering
  :PROPERTIES:
  :LINEAR_ID: ENG-456
  :LINEAR_URL: https://linear.app/your-org/issue/ENG-456
  :GITHUB_PR: https://github.com/org/repo/pull/9
  :OTHER_LINK: https://notion.so/some-doc
  :END:
```

**Multiple links of a type** — 1-indexed suffix:

```org
* TODO [#B] Another issue
  :PROPERTIES:
  :LINEAR_ID: ENG-457
  :LINEAR_URL: https://linear.app/your-org/issue/ENG-457
  :GITHUB_PR_1: https://github.com/org/repo/pull/9
  :GITHUB_PR_2: https://github.com/org/repo/pull/12
  :END:
```

The indexing rule applies independently per type: an issue with two PRs and one doc link would render `:GITHUB_PR_1:`, `:GITHUB_PR_2:`, `:OTHER_LINK:`.

---

## Affected Modules

| Module | Change |
|--------|--------|
| `org_writer.py` | `Link` model added; `Issue` gains `github_prs` + `other_links`; `format_issue` renders link properties |
| `linear_client.py` | `_ISSUE_FIELDS` extended; `_parse_issue` extracts, deduplicates, and classifies links |
| `org_writer_test.py` | New test cases for property rendering |
| `linear_client_test.py` | New test cases for classification and deduplication |

---

## Testing

1. **Link classification** — PR regex correctly routes `github.com/.+/pull/\d+` to `github_prs` and everything else to `other_links`
2. **Deduplication** — a URL in both `attachments` and `description` appears once; attachment title is preferred
3. **Property rendering** — single link uses bare key; multiple links use indexed keys; issues with no links produce unchanged output

---

## Out of Scope

- Rendering link titles or labels in the org body (properties only)
- Fetching issue comments for additional URLs
- Distinguishing GitHub issues from GitHub wiki/blob/discussion URLs within `other_links`
- Paginating attachments (Linear issues are unlikely to have more than a handful)
