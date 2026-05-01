---
name: rhapi
description: >
  Use the `rhapi` CLI to search and retrieve Red Hat support cases and KCS
  articles. Trigger this skill whenever the user asks about Red Hat support
  cases, customer tickets, case searches, KCS solutions, or wants to look up
  support information — even if they don't say "rhapi" explicitly. Common
  triggers include asking about cases for a customer, looking up a case number,
  searching KCS articles, filtering cases by account or time range, or any
  request involving Red Hat support data.
---

# rhapi — Red Hat API CLI

`rhapi` is a globally installed CLI that queries Red Hat's Hydra API for support cases and KCS articles. Requires `RH_API_OFFLINE_TOKEN` in the environment.

## Commands

### Search cases

```bash
rhapi search-cases [QUERY] [OPTIONS]
```

| Flag | Purpose |
|------|---------|
| `QUERY` | Solr query string (default: `*:*` = match all) |
| `--account` | Filter by customer EBS account number |
| `--months` | Only cases created within N months |
| `--rows` | Results per page (default: 10) |
| `--start` | Pagination offset (default: 0) |

### Get case details

```bash
rhapi get-case CASE_NUMBER
```

Returns summary, description, severity, status, product, comments, external trackers, and resource links.

### Search KCS articles

```bash
rhapi search-kcs QUERY [OPTIONS]
```

| Flag | Purpose |
|------|---------|
| `QUERY` | Search keywords (required) |
| `--rows` | Results per page (default: 50) |
| `--start` | Pagination offset (default: 0) |

### Get KCS solution

```bash
rhapi get-kcs SOLUTION_ID
```

Returns title, environment, issue, resolution, and root cause.

## Output format

JSON by default. Use `-o table` for human-readable output. The flag goes on any command:

```bash
rhapi search-cases --months 6 -o table
```

## Pagination

When the user wants all results, paginate by incrementing `--start`:

```bash
rhapi search-cases --account ACCT --months 12 --rows 200 --start 0
rhapi search-cases --account ACCT --months 12 --rows 200 --start 200
```

Continue until the result count is less than `--rows`.

## Tips

- The `--account` flag takes the EBS account number, not a company name.
- Case numbers are 8-digit strings. KCS solution IDs are numeric.
- For broad customer queries, use `*:*` as the query with `--account` and `--months` filters.
- Output can be piped through `jq` for analysis.
