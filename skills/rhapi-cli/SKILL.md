---
name: rhapi
description: >
  Use the `rhapi` CLI to search and retrieve Red Hat support cases, KCS
  articles, and product documentation. Trigger this skill whenever the user
  asks about Red Hat support cases, customer tickets, case searches, KCS
  solutions, product docs, or wants to look up support information — even if
  they don't say "rhapi" explicitly. Common triggers include asking about
  cases for a customer, looking up a case number, searching KCS articles,
  finding product documentation, filtering cases by account or time range,
  or any request involving Red Hat support data.
---

# rhapi — Red Hat API CLI

`rhapi` is a globally installed CLI that queries Red Hat's Hydra API for support cases, KCS articles, and product documentation. Requires `RH_API_OFFLINE_TOKEN` in the environment.

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

### Add comment to case

```bash
rhapi add-comment CASE_NUMBER BODY
```

| Flag | Purpose |
|------|---------|
| `CASE_NUMBER` | 8-digit case number (required) |
| `BODY` | Comment text in markdown (required, quote multi-word) |

Comments are **always private** (internal only, not customer-visible).

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

### Search product documentation

```bash
rhapi search-docs QUERY [OPTIONS]
```

| Flag | Purpose |
|------|---------|
| `QUERY` | Search keywords (required) |
| `--product` | Filter by product name (e.g. "Red Hat OpenShift Service on AWS") |
| `--rows` | Results per page (default: 10) |
| `--start` | Pagination offset (default: 0) |

Searches docs.redhat.com for official product documentation pages. Include version in the query string (e.g. "upgrade 4.18") since the API has no version filter field.

### Search CVEs

```bash
rhapi search-cve [OPTIONS]
```

| Flag | Purpose |
|------|---------|
| `--severity` | Filter: low, moderate, important, critical |
| `--product` | Filter by product (e.g. "openshift") |
| `--package` | Filter by package (e.g. "kernel", "samba") |
| `--advisory` | Filter by advisory (e.g. "RHSA-2026:13565") |
| `--cvss3-score` | Minimum CVSSv3 score (e.g. 7.0, 9.0) |
| `--after` | Only CVEs after date (YYYY-MM-DD) |
| `--before` | Only CVEs before date (YYYY-MM-DD) |
| `--created-days-ago` | Only CVEs created within N days |
| `--per-page` | Results per page (default: 10) |
| `--page` | Page number (default: 1) |

### Get CVE details

```bash
rhapi get-cve CVE_ID
```

Returns severity, CVSS score/vector, affected releases, fix status, mitigation, upstream fix, references, bugzilla link, and statement.

## Output format

JSON by default. Use `-o table` for key-value or `-o md` for markdown tables. The flag goes on any command:

```bash
rhapi search-cases --months 6 -o table
rhapi search-cases --months 6 -o md
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
