#!/usr/bin/env python3
"""CLI interface for Red Hat API tools."""

import asyncio
import json
import sys

import click
import httpx

from redhat_api_mcp import tools

_output_option = click.option("--output", "-o", "fmt", type=click.Choice(["json", "table", "md"]), default="json", help="Output format")


def run_async(coro):
    """Run an async coroutine with error handling."""
    try:
        return asyncio.run(coro)
    except ValueError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        click.echo(f"API error: {e.response.status_code} {e.response.text}", err=True)
        sys.exit(2)
    except httpx.ConnectError as e:
        click.echo(f"Connection error: {e}", err=True)
        sys.exit(3)


def _md_table(rows: list[dict]) -> str:
    if not rows:
        return ""
    keys = list(rows[0].keys())
    header = "| " + " | ".join(keys) + " |"
    sep = "| " + " | ".join("---" for _ in keys) + " |"
    lines = [header, sep]
    for row in rows:
        cells = [str(row.get(k, "") or "").replace("\n", " ").replace("|", "\\|") for k in keys]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _md_dict(data: dict) -> str:
    lines = []
    for k, v in data.items():
        if isinstance(v, list) and v and isinstance(v[0], dict):
            lines.append(f"\n### {k}\n")
            lines.append(_md_table(v))
        elif isinstance(v, list):
            lines.append(f"**{k}:** {', '.join(str(i) for i in v)}")
        else:
            val = str(v).replace("\n", "\n> ") if v and "\n" in str(v) else v
            lines.append(f"**{k}:** {val}")
    return "\n\n".join(lines)


def output(data, fmt="json"):
    """Format and print output."""
    if fmt == "json":
        click.echo(json.dumps(data, indent=2, default=str))
    elif fmt == "md":
        if isinstance(data, list):
            click.echo(_md_table(data))
        elif isinstance(data, dict):
            click.echo(_md_dict(data))
    elif fmt == "table":
        if isinstance(data, list):
            for item in data:
                for k, v in item.items():
                    click.echo(f"  {k}: {v}")
                click.echo("---")
        elif isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    click.echo(f"{k}:")
                    for entry in v:
                        parts = [f"{ek}={ev}" for ek, ev in entry.items() if ev]
                        click.echo(f"  - {', '.join(parts)}")
                elif isinstance(v, list):
                    click.echo(f"{k}: {', '.join(str(i) for i in v)}")
                else:
                    click.echo(f"{k}: {v}")


@click.group()
def cli():
    """rhapi - Red Hat API command-line tools.

    Query Red Hat's Hydra API for support cases, KCS articles, docs, and CVEs.
    Requires RH_API_OFFLINE_TOKEN in the environment.

    \b
    search-cases [QUERY] [OPTIONS]
      Search Red Hat support cases.
      QUERY is a Solr search string (e.g. "apiserver timeout").
      Defaults to "*:*" (match all) when omitted, useful with filter flags.
      --account TEXT     Filter by customer EBS account number
      --months INTEGER   Only cases created within N months
      --rows INTEGER     Number of results (default: 10)
      --start INTEGER    Pagination offset (default: 0)
      -o [json|table|md] Output format (default: json)

    \b
    search-docs QUERY [OPTIONS]
      Search Red Hat product documentation (docs.redhat.com).
      QUERY is a search string (e.g. "ROSA networking", "ARO upgrade").
      --product TEXT     Filter by product (e.g. "Red Hat OpenShift Service on AWS")
      --rows INTEGER     Number of results (default: 10)
      --start INTEGER    Pagination offset (default: 0)
      -o [json|table|md] Output format (default: json)

    \b
    add-comment CASE_NUMBER BODY [OPTIONS]
      Add a private comment to a support case (always private).
      CASE_NUMBER is the 8-digit case number.
      BODY is the comment text in markdown (quote multi-word strings).
      -o [json|table|md] Output format (default: json)

    \b
    get-case CASE_NUMBER [OPTIONS]
      Get full case details by case number.
      CASE_NUMBER is an 8-digit string (e.g. 01234567).
      Returns summary, description, severity, status, comments, and linked resources.
      -o [json|table|md] Output format (default: json)

    \b
    search-kcs QUERY [OPTIONS]
      Search Red Hat KCS solutions and articles.
      QUERY is a search string (e.g. "etcd defrag", "OCP upgrade").
      --rows INTEGER     Number of results (default: 10)
      --start INTEGER    Pagination offset (default: 0)
      -o [json|table|md] Output format (default: json)

    \b
    get-kcs SOLUTION_ID [OPTIONS]
      Get a specific KCS solution by its numeric ID.
      Returns title, environment, issue, resolution, and root cause.
      -o [json|table|md] Output format (default: json)

    \b
    search-cve [OPTIONS]
      Search Red Hat CVEs via the Security Data API.
      --severity TEXT         Filter: low, moderate, important, critical
      --product TEXT          Filter by product (e.g. "openshift")
      --package TEXT          Filter by package (e.g. "kernel", "samba")
      --advisory TEXT         Filter by advisory (e.g. "RHSA-2026:13565")
      --cvss3-score FLOAT    Minimum CVSSv3 score (e.g. 7.0, 9.0)
      --after DATE            Only CVEs after this date (YYYY-MM-DD)
      --before DATE           Only CVEs before this date (YYYY-MM-DD)
      --created-days-ago INT  Only CVEs created within N days
      --per-page INT          Number of results (default: 10)
      --page INT              Page number (default: 1)
      -o [json|table|md]      Output format (default: json)

    \b
    get-cve CVE_ID [OPTIONS]
      Get detailed CVE information from Red Hat Security Data.
      CVE_ID is the CVE identifier (e.g. CVE-2026-31431).
      Returns severity, CVSS, affected releases, fix status, mitigation,
      upstream fix, references, and advisories.
      -o [json|table|md] Output format (default: json)

    \b
    get-doc URL [OPTIONS]
      Fetch full content from a Red Hat documentation page.
      URL is the full docs.redhat.com URL.
      Returns title and plain-text content extracted from the page.
      -o [json|table|md] Output format (default: json)

    \b
    search-errata [OPTIONS]
      Search Red Hat errata/advisories via the CSAF Security Data API.
      --advisory TEXT         Comma-separated advisory IDs
      --cve TEXT              Comma-separated CVE IDs
      --severity TEXT         Filter: low, moderate, important, critical
      --package TEXT          Filter by package (e.g. "kernel", "openshift-hyperkube")
      --after DATE            Only advisories after this date (YYYY-MM-DD)
      --before DATE           Only advisories before this date (YYYY-MM-DD)
      --created-days-ago INT  Only advisories created within N days
      --per-page INT          Number of results (default: 10)
      --page INT              Page number (default: 1)
      -o [json|table|md]      Output format (default: json)

    \b
    get-errata ADVISORY_ID [OPTIONS]
      Get detailed advisory information from Red Hat Security Data.
      ADVISORY_ID is the advisory identifier (e.g. RHSA-2026:46885).
      Returns severity, CVEs, affected products, and references.
      -o [json|table|md] Output format (default: json)

    \b
    list-attachments CASE_NUMBER [OPTIONS]
      List attachments on a support case.
      CASE_NUMBER is the 8-digit case number.
      Returns filename, size, and UUID for each attachment.
      -o [json|table|md] Output format (default: json)

    \b
    get-attachment CASE_NUMBER ATTACHMENT_UUID [OPTIONS]
      Download a case attachment to /tmp.
      CASE_NUMBER is the 8-digit case number.
      ATTACHMENT_UUID is the UUID from list-attachments.
      Downloads to /tmp/rhapi-attachments/<case>/<filename>.
      -o [json|table|md] Output format (default: json)

    \b
    list-operator-bundles PACKAGE [OPTIONS]
      List operator bundles from the Red Hat Pyxis catalog (no auth needed).
      PACKAGE is the operator package name (e.g. openshift-pipelines-operator-rh).
      Returns latest-in-channel by default; use --channel for all versions.
      --ocp-version TEXT  Filter by OCP version (e.g. "4.18")
      --channel TEXT      Show all versions in this channel (manual approval)
      -o [json|table|md]  Output format (default: json)

    \b
    Output:
      JSON by default. Use -o table for key-value, -o md for markdown tables.

    \b
    Pagination:
      Use --rows and --start to paginate. To get all results, increase --rows
      or loop with incrementing --start until fewer than --rows are returned.

    \b
    Examples:
      rhapi search-cases --account 12345678 --months 12
      rhapi search-cases "apiserver timeout" --rows 50
      rhapi get-case 01234567
      rhapi search-kcs "etcd defrag" -o table
      rhapi get-kcs 1234567
      rhapi search-docs "networking" --product "Red Hat OpenShift Service on AWS"
      rhapi add-comment 01234567 "Investigating the issue"
      rhapi search-cve --severity critical --after 2026-01-01
      rhapi get-cve CVE-2026-31431
      rhapi get-doc https://docs.redhat.com/en/documentation/...
      rhapi search-errata --severity critical --created-days-ago 7
      rhapi search-errata --cve CVE-2026-16242
      rhapi get-errata RHSA-2026:46885
      rhapi list-attachments 01234567
      rhapi get-attachment 01234567 <uuid-from-list>
      rhapi list-operator-bundles openshift-pipelines-operator-rh --ocp-version 4.19
      rhapi list-operator-bundles cluster-logging --ocp-version 4.18 --channel stable-6.2

    \b
    Tips:
      - --account takes the EBS account number, not a company name.
      - Case numbers are 8-digit strings. KCS solution IDs are numeric.
      - Pipe JSON output through jq for analysis.
    """


@cli.command("search-kcs")
@click.argument("query")
@click.option("--rows", default=10, help="Number of results")
@click.option("--start", default=0, help="Pagination offset")
@_output_option
def search_kcs_cmd(query, rows, start, fmt):
    """Search Red Hat KCS solutions and articles.

    \b
    QUERY is a search string (e.g. "etcd defrag", "OCP upgrade").
    """
    result = run_async(tools.search_kcs(query, rows, start))
    output(result, fmt)


@cli.command("get-kcs")
@click.argument("solution_id")
@_output_option
def get_kcs_cmd(solution_id, fmt):
    """Get a KCS solution by ID.

    \b
    SOLUTION_ID is the numeric KCS ID (e.g. 1234567).
    Returns title, environment, issue, resolution, and root cause.
    """
    result = run_async(tools.get_kcs(solution_id))
    output(result, fmt)


@cli.command("search-docs")
@click.argument("query")
@click.option("--product", default=None, help="Filter by product name")
@click.option("--rows", default=10, help="Number of results")
@click.option("--start", default=0, help="Pagination offset")
@_output_option
def search_docs_cmd(query, product, rows, start, fmt):
    """Search Red Hat product documentation (docs.redhat.com).

    \b
    QUERY is a search string (e.g. "ROSA networking", "ARO upgrade").
    """
    result = run_async(tools.search_docs(query, rows, start, product))
    output(result, fmt)


@cli.command("search-cases")
@click.argument("query", default="*:*")
@click.option("--rows", default=10, help="Number of results")
@click.option("--start", default=0, help="Pagination offset")
@click.option("--account", "account_number", default=None, help="Filter by account number")
@click.option("--months", "created_within_months", default=None, type=int, help="Only cases created within N months")
@_output_option
def search_cases_cmd(query, rows, start, account_number, created_within_months, fmt):
    """Search Red Hat support cases.

    \b
    QUERY is a Solr search string (e.g. "apiserver timeout").
    Defaults to "*:*" (match all) when omitted, useful with --account/--months filters.
    """
    result = run_async(tools.search_cases(query, rows, start, account_number, created_within_months))
    output(result, fmt)


@cli.command("get-case")
@click.argument("case_number")
@click.option("--include-ai-comments", is_flag=True, default=False, help="Include XE AI Assistant comments (filtered by default)")
@_output_option
def get_case_cmd(case_number, include_ai_comments, fmt):
    """Get case details by case number.

    \b
    CASE_NUMBER is the 8-digit case number (e.g. 01234567).
    Returns summary, description, severity, status, comments, and linked resources.
    AI-generated comments (XE AI Assistant) are filtered by default to save tokens.
    """
    result = run_async(tools.get_case(case_number, include_ai_comments=include_ai_comments))
    output(result, fmt)


@cli.command("add-comment")
@click.argument("case_number")
@click.argument("body")
@_output_option
def add_comment_cmd(case_number, body, fmt):
    """Add a private comment to a support case (always private).

    \b
    CASE_NUMBER is the 8-digit case number (e.g. 01234567).
    BODY is the comment text in markdown (quote multi-word strings).
    """
    result = run_async(tools.add_comment(case_number, body))
    output(result, fmt)


@cli.command("search-cve")
@click.option("--severity", default=None, help="Filter: low, moderate, important, critical")
@click.option("--product", default=None, help="Filter by product")
@click.option("--package", default=None, help="Filter by package name")
@click.option("--advisory", default=None, help="Filter by advisory (e.g. RHSA-2026:13565)")
@click.option("--cvss3-score", default=None, type=float, help="Minimum CVSSv3 score")
@click.option("--after", default=None, help="Only CVEs after this date (YYYY-MM-DD)")
@click.option("--before", default=None, help="Only CVEs before this date (YYYY-MM-DD)")
@click.option("--created-days-ago", default=None, type=int, help="Only CVEs created within N days")
@click.option("--per-page", default=10, help="Number of results")
@click.option("--page", default=1, help="Page number")
@_output_option
def search_cve_cmd(severity, product, package, advisory, cvss3_score, after, before, created_days_ago, per_page, page, fmt):
    """Search Red Hat CVEs via the Security Data API.

    \b
    At least one filter is recommended. Without filters, returns recent CVEs.
    """
    result = run_async(tools.search_cve(severity, product, package, advisory, cvss3_score, after, before, created_days_ago, per_page, page))
    output(result, fmt)


@cli.command("get-cve")
@click.argument("cve_id")
@_output_option
def get_cve_cmd(cve_id, fmt):
    """Get detailed CVE information from Red Hat Security Data.

    \b
    CVE_ID is the CVE identifier (e.g. CVE-2026-31431).
    Returns severity, CVSS, affected releases, fix status, mitigation, and references.
    """
    result = run_async(tools.get_cve(cve_id))
    output(result, fmt)


@cli.command("get-doc")
@click.argument("url")
@_output_option
def get_doc_cmd(url, fmt):
    """Fetch full content from a Red Hat documentation page.

    \b
    URL is the full docs.redhat.com URL.
    Returns title and plain-text content extracted from the page.
    """
    result = run_async(tools.get_doc(url))
    output(result, fmt)


@cli.command("search-errata")
@click.option("--advisory", default=None, help="Comma-separated advisory IDs (e.g. RHSA-2026:46885)")
@click.option("--cve", default=None, help="Comma-separated CVE IDs")
@click.option("--severity", default=None, help="Filter: low, moderate, important, critical")
@click.option("--package", default=None, help="Filter by package name")
@click.option("--after", default=None, help="Only advisories after this date (YYYY-MM-DD)")
@click.option("--before", default=None, help="Only advisories before this date (YYYY-MM-DD)")
@click.option("--created-days-ago", default=None, type=int, help="Only advisories created within N days")
@click.option("--per-page", default=10, help="Number of results")
@click.option("--page", default=1, help="Page number")
@_output_option
def search_errata_cmd(advisory, cve, severity, package, after, before, created_days_ago, per_page, page, fmt):
    """Search Red Hat errata/advisories via the CSAF Security Data API.

    \b
    At least one filter is recommended.
    """
    result = run_async(tools.search_errata(advisory, cve, severity, package, after, before, created_days_ago, per_page, page))
    output(result, fmt)


@cli.command("get-errata")
@click.argument("advisory_id")
@_output_option
def get_errata_cmd(advisory_id, fmt):
    """Get detailed advisory information from Red Hat Security Data.

    \b
    ADVISORY_ID is the advisory identifier (e.g. RHSA-2026:46885).
    Returns severity, CVEs, affected products, and references.
    """
    result = run_async(tools.get_errata(advisory_id))
    output(result, fmt)


@cli.command("list-attachments")
@click.argument("case_number")
@_output_option
def list_attachments_cmd(case_number, fmt):
    """List attachments on a support case.

    \b
    CASE_NUMBER is the 8-digit case number (e.g. 01234567).
    Returns filename, size, creator, and UUID for each attachment.
    """
    result = run_async(tools.list_attachments(case_number))
    output(result, fmt)


@cli.command("get-attachment")
@click.argument("case_number")
@click.argument("attachment_uuid")
@_output_option
def get_attachment_cmd(case_number, attachment_uuid, fmt):
    """Download a case attachment to /tmp.

    \b
    CASE_NUMBER is the 8-digit case number.
    ATTACHMENT_UUID is the UUID from list-attachments.
    Downloads to /tmp/rhapi-attachments/<case>/<filename>.
    """
    result = run_async(tools.get_attachment(case_number, attachment_uuid))
    output(result, fmt)


@cli.command("list-operator-bundles")
@click.argument("package")
@click.option("--ocp-version", default=None, help="Filter by OCP version (e.g. 4.18)")
@click.option("--channel", default=None, help="Show all versions in this channel")
@_output_option
def list_operator_bundles_cmd(package, ocp_version, channel, fmt):
    """List operator bundles from the Red Hat Pyxis catalog.

    \b
    PACKAGE is the operator package name (e.g. openshift-pipelines-operator-rh).
    Returns latest-in-channel by default. Use --channel for all versions
    in a specific channel (useful for manual approval subscriptions).
    No authentication required.
    """
    result = run_async(tools.list_operator_bundles(package, ocp_version, channel))
    output(result, fmt)


if __name__ == "__main__":
    cli()
