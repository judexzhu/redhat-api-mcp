#!/usr/bin/env python3
"""Red Hat API MCP Server — FastMCP setup, tool wrappers, and prompt templates."""

from pathlib import Path
from typing import Optional, List, Dict

from mcp.server.fastmcp import FastMCP

from redhat_api_mcp import tools

_PROMPTS_DIR = Path(__file__).parent / "prompts"

mcp = FastMCP("RedHat API", description="Interact with Red Hat KCS and Case APIs", version="1.0.0")


@mcp.tool()
async def search_kcs(query: str, rows: int = 50, start: int = 0) -> List[Dict]:
    """
    Search for Red Hat KCS Solutions and return a list with Solution IDs.

    Args:
        query: Search query string
        rows: Number of results to return (default: 50)
        start: Starting index for pagination (default: 0)

    Returns:
        List of solutions with their IDs and metadata

    By default, this tool returns only documents where documentKind is either "Article" or "Solution" and accessState is either "active" or "private".
    """
    return await tools.search_kcs(query, rows, start)


@mcp.tool()
async def get_kcs(solution_id: str) -> Dict:
    """Get a specific solution by ID and extract structured content

    Args:
        solution_id: The ID of the solution to retrieve

    Returns:
        Dictionary with title, Environment, Issue, Resolution, and Root Cause
    """
    return await tools.get_kcs(solution_id)


@mcp.tool()
async def search_docs(query: str, rows: int = 10, start: int = 0, product: Optional[str] = None) -> List[Dict]:
    """
    Search Red Hat product documentation (docs.redhat.com).

    Args:
        query: Search query string
        rows: Number of results to return (default: 10)
        start: Starting index for pagination (default: 0)
        product: Filter by product name (e.g. "Red Hat OpenShift Service on AWS")

    Returns:
        List of documentation pages with their titles and URLs
    """
    return await tools.search_docs(query, rows, start, product)


@mcp.tool()
async def search_cases(query: str, rows: int = 10, start: int = 0, account_number: Optional[str] = None, created_within_months: Optional[int] = None) -> List[Dict]:
    """
    Search for Red Hat cases and return a list of case numbers.

    Args:
        query: Search query string
        rows: Number of results to return (default: 10)
        start: Starting index for pagination (default: 0)
        account_number: Filter by customer EBS account number
        created_within_months: Only return cases created within this many months (e.g., 12 for last year)

    Returns:
        List of cases with their numbers and metadata
    """
    return await tools.search_cases(query, rows, start, account_number, created_within_months)


@mcp.tool()
async def add_comment(case_number: str, body: str) -> Dict:
    """
    Add a private comment to a Red Hat support case (always private, never customer-visible).

    Args:
        case_number: The case number (e.g., "01234567")
        body: The comment text to post (supports markdown)

    Returns:
        The created comment (author, body, created timestamp)
    """
    return await tools.add_comment(case_number, body)


@mcp.tool()
async def get_case(case_number: str) -> Dict:
    """
    Get case details by case number.

    Args:
        case_number: The case number (e.g., "01234567")

    Returns:
        Formatted case data with description, severity, issue, case number, and comments
    """
    return await tools.get_case(case_number)


@mcp.tool()
async def search_cve(
    severity: Optional[str] = None,
    product: Optional[str] = None,
    package: Optional[str] = None,
    advisory: Optional[str] = None,
    cvss3_score: Optional[float] = None,
    after: Optional[str] = None,
    before: Optional[str] = None,
    created_days_ago: Optional[int] = None,
    per_page: int = 10,
    page: int = 1,
) -> List[Dict]:
    """
    Search Red Hat CVEs via the Security Data API.

    Args:
        severity: Filter by severity (low, moderate, important, critical)
        product: Filter by product (e.g. "openshift")
        package: Filter by package name (e.g. "kernel", "samba")
        advisory: Filter by advisory (e.g. "RHSA-2026:13565")
        cvss3_score: Minimum CVSSv3 score (e.g. 7.0, 9.0)
        after: Only CVEs published after this date (YYYY-MM-DD)
        before: Only CVEs published before this date (YYYY-MM-DD)
        created_days_ago: Only CVEs created within N days
        per_page: Number of results to return (default: 10)
        page: Page number for pagination (default: 1)

    Returns:
        List of CVEs with severity, CVSS score, and advisories
    """
    return await tools.search_cve(severity, product, package, advisory, cvss3_score, after, before, created_days_ago, per_page, page)


@mcp.tool()
async def get_cve(cve_id: str) -> Dict:
    """
    Get detailed information about a specific CVE from Red Hat Security Data.

    Args:
        cve_id: The CVE identifier (e.g., "CVE-2026-31431")

    Returns:
        Detailed CVE information including severity, CVSS, affected releases, and fix status
    """
    return await tools.get_cve(cve_id)


@mcp.tool()
async def get_doc(url: str) -> Dict:
    """
    Fetch full content from a Red Hat documentation page (docs.redhat.com).

    Args:
        url: Full URL of the documentation page (e.g. "https://docs.redhat.com/en/documentation/...")

    Returns:
        Dictionary with title and plain-text content extracted from the page
    """
    return await tools.get_doc(url)


# ── Prompt templates ────────────────────────────────────────────────


def _load_prompt(name: str, **kwargs: str) -> str:
    return (_PROMPTS_DIR / f"{name}.md").read_text().format(**kwargs).strip()


@mcp.prompt(name="summarize_case_prompt", description="Summarize a Red Hat support case in C.A.S.E. markdown format.")
async def summarize_case_prompt(case_number: str) -> str:
    """Given a case number, return the C.A.S.E. summary prompt."""
    return _load_prompt("summarize_case", case_number=case_number)


@mcp.prompt(name="resolve_case_prompt", description="Red Hat Case Resolver Agent: investigation and solution workflow for a support case.")
async def resolve_case_prompt(case_number: str) -> str:
    """Given a case number, return the case resolver workflow prompt."""
    return _load_prompt("resolve_case", case_number=case_number)


@mcp.prompt(name="resolve_case_prompt_v2", description="Red Hat Case Resolver Agent: investigation and solution workflow for a support case.")
async def resolve_case_prompt_v2(case_number: str) -> str:
    """Given a case number, return the v2 case resolver workflow prompt."""
    return _load_prompt("resolve_case_v2", case_number=case_number)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
