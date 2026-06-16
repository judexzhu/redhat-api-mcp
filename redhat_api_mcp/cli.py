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

    Query Red Hat's Hydra API for support cases and KCS articles.
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
@_output_option
def get_case_cmd(case_number, fmt):
    """Get case details by case number.

    \b
    CASE_NUMBER is the 8-digit case number (e.g. 01234567).
    Returns summary, description, severity, status, comments, and linked resources.
    """
    result = run_async(tools.get_case(case_number))
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


if __name__ == "__main__":
    cli()
