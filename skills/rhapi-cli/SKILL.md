---
name: rhapi
description: >
  Use the `rhapi` CLI to search and retrieve Red Hat support cases, KCS
  articles, product documentation, CVEs, errata/advisories, and case
  attachments. Trigger this skill whenever the user asks about Red Hat support
  cases, customer tickets, case searches, KCS solutions, product docs, CVEs,
  security advisories, errata, operator compatibility, or wants to look up
  support information — even if they don't say "rhapi" explicitly. Common
  triggers include asking about cases for a customer, looking up a case number,
  searching KCS articles, finding product documentation, filtering cases by
  account or time range, searching CVEs by severity or product, looking up
  errata/advisories, downloading case attachments, checking operator
  compatibility across OCP versions, or any request involving Red Hat support
  data.
---

# rhapi — Red Hat API CLI

`rhapi` is a globally installed CLI that queries Red Hat APIs for support cases, KCS articles, product documentation, CVEs, errata, case attachments, and operator compatibility (Pyxis catalog). Requires `RH_API_OFFLINE_TOKEN` in the environment (except `list-operator-bundles` which uses the public Pyxis API).

Run `rhapi --help` for full command reference with all flags and examples.

## Tips

- `--account` takes the EBS account number, not a company name.
- Case numbers are 8-digit strings. KCS solution IDs are numeric.
- For broad customer queries, use `*:*` as the query with `--account` and `--months` filters.
- Output can be piped through `jq` for analysis.
- No product/version filter exists for errata. To find errata for a specific OCP version (e.g. 4.21.25), use `rhapi search-docs "OpenShift 4.21 release notes"` then `rhapi get-doc <url>` on the release notes page and search for the version string.
- Comments posted via `add-comment` are always private (never customer-visible).
- `list-operator-bundles` queries the public Pyxis catalog (no auth). Use `--ocp-version` to check operator compatibility with a target OCP version. Use `--channel` to see all versions in a channel (for manual approval subscriptions).

## Pagination

When the user wants all results, paginate by incrementing `--start`:

```bash
rhapi search-cases --account ACCT --months 12 --rows 200 --start 0
rhapi search-cases --account ACCT --months 12 --rows 200 --start 200
```

Continue until the result count is less than `--rows`.
