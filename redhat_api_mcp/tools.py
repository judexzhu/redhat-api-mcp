import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict

from redhat_api_mcp.client import RedHatAPI

_client: RedHatAPI | None = None


def get_client() -> RedHatAPI:
    global _client
    if _client is None:
        _client = RedHatAPI()
    return _client


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
    client = get_client()
    path = "/hydra/rest/search/v2/kcs"

    data = {
        "q": query,
        "rows": rows,
        "expression": urllib.parse.quote(
            'sort=score DESC&fq=documentKind:("Article" OR "Solution") AND accessState:("active" OR "private")&fl=allTitle,caseCount,documentKind,[elevated],hasPublishedRevision,id,language,lastModifiedDate,ModerationState,score,uri,resource_uri,view_uri,createdDate&showRetired=false',
            safe='=&,:()[]"',
        ),
        "start": start,
        "clientName": "mcp",
    }

    result = await client.make_request("post", path, data)

    solutions = []
    if "response" in result and "docs" in result["response"]:
        for doc in result["response"]["docs"]:
            solution = {
                "id": doc.get("id"),
                "title": doc.get("allTitle"),
                "score": doc.get("score"),
                "view_uri": doc.get("view_uri"),
            }
            solutions.append(solution)

    return solutions


async def get_kcs(solution_id: str) -> Dict:
    """Get a specific solution by ID and extract structured content

    Args:
        solution_id: The ID of the solution to retrieve

    Returns:
        Dictionary with title, Environment, Issue, Resolution, and Root Cause
    """
    client = get_client()

    # First, determine the document type via search API
    search_result = await client.make_request("post", "/hydra/rest/search/v2/kcs", {"q": f"id:{solution_id}"})

    doc_kind = None
    if search_result and "response" in search_result and "docs" in search_result["response"] and search_result["response"]["docs"]:
        doc = search_result["response"]["docs"][0]
        doc_kind = doc.get("documentKind", "").lower()

    # Fetch full content via Drupal API
    doc_type = "articles" if doc_kind == "article" else "solutions"
    try:
        drupal = await client.make_request("get", f"/hydra/rest/drupal/{doc_type}/{solution_id}")
    except Exception:
        drupal = {}

    is_teaser = drupal.get("isTeaser", True)

    def extract_text(field):
        if isinstance(field, dict):
            return field.get("text", "")
        if isinstance(field, list):
            return field[0] if field else ""
        return field or ""

    if not is_teaser and drupal:
        solution_data = {
            "title": drupal.get("title", ""),
            "environment": extract_text(drupal.get("environment")),
            "issue": extract_text(drupal.get("issue")),
            "resolution": extract_text(drupal.get("resolution")),
            "root_cause": extract_text(drupal.get("rootCause")),
            "diagnostic_steps": extract_text(drupal.get("diagnosticSteps")),
        }
        if drupal.get("bodyAbstract"):
            solution_data["abstract"] = extract_text(drupal.get("bodyAbstract"))
        return solution_data

    # Fallback to search API fields (teaser or articles without full body)
    if search_result and "response" in search_result and "docs" in search_result["response"] and search_result["response"]["docs"]:
        doc = search_result["response"]["docs"][0]
        return {
            "title": doc.get("publishedTitle", doc.get("allTitle", "")),
            "abstract": doc.get("abstract", ""),
            "environment": doc.get("standard_product", ""),
            "issue": doc.get("issue", ""),
            "resolution": doc.get("solution_resolution", ""),
            "root_cause": doc.get("solution_rootcause", ""),
        }

    return {
        "title": "",
        "environment": "",
        "issue": "",
        "resolution": "",
        "root_cause": "",
    }


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
    client = get_client()
    fq = [
        "-documentKind:(PortalProduct OR ContainerVendor OR Packages)",
        "-id:Other",
        "language:(en)",
        '{!tag=documentKindFilter}documentKind:("Documentation")',
    ]
    if product:
        fq.append(f'standard_product:("{product}")')
    params = {
        "q": query,
        "rows": rows,
        "start": start,
        "fl": "allTitle,abstract,documentKind,lastModifiedDate,view_uri",
        "fq": fq,
    }
    result = await client.make_request("get", "/hydra/rest/search/platform/docs", params=params)

    docs = []
    if "response" in result and "docs" in result["response"]:
        for doc in result["response"]["docs"]:
            docs.append({
                "title": doc.get("allTitle"),
                "abstract": doc.get("abstract"),
                "url": doc.get("view_uri"),
                "last_modified": doc.get("lastModifiedDate"),
            })

    return docs


async def search_cases(
    query: str,
    rows: int = 10,
    start: int = 0,
    account_number: Optional[str] = None,
    created_within_months: Optional[int] = None,
) -> List[Dict]:
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
    client = get_client()
    path = "/hydra/rest/search/v2/cases"

    expression = "sort=case_lastModifiedDate desc&fl=case_createdByName,case_createdDate,case_lastModifiedDate,case_lastModifiedByName,id,uri,case_summary,case_status,case_product,case_version,case_accountNumber,case_number,case_contactName,case_owner,case_severity"

    filters = []
    if account_number:
        filters.append(f"case_accountNumber:{account_number}")
    if created_within_months is not None:
        since = (datetime.now(timezone.utc) - timedelta(days=created_within_months * 30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        filters.append(f"case_createdDate:[{since} TO NOW]")
    if filters:
        fq = " AND ".join(filters)
        expression += f"&fq={fq}"

    data = {
        "q": query,
        "start": start,
        "rows": rows,
        "partnerSearch": False,
        "expression": urllib.parse.quote(expression, safe='=&,:()[]"'),
    }

    result = await client.make_request("post", path, data)

    cases = []
    if "response" in result and "docs" in result["response"]:
        for doc in result["response"]["docs"]:
            case = {
                "case_number": doc.get("case_number"),
                "summary": doc.get("case_summary"),
                "status": doc.get("case_status"),
                "product": doc.get("case_product"),
                "version": doc.get("case_version"),
                "severity": doc.get("case_severity"),
                "owner": doc.get("case_owner"),
                "created_date": doc.get("case_createdDate"),
                "created_by": doc.get("case_createdByName"),
                "last_modified_date": doc.get("case_lastModifiedDate"),
                "uri": doc.get("uri"),
            }
            cases.append(case)

    return cases


async def add_comment(case_number: str, body: str) -> Dict:
    """
    Add a private comment to a Red Hat support case (always private, never customer-visible).

    Args:
        case_number: The case number (e.g., "01234567")
        body: The comment text to post (supports markdown)

    Returns:
        The created comment (author, body, created timestamp)
    """
    client = get_client()
    path = f"/hydra/rest/v1/cases/{case_number}/comments"
    data = {"commentBody": body, "isPublic": False}
    result = await client.make_request("post", path, data)
    return {
        "case_number": case_number,
        "commentBody": result.get("commentBody", ""),
        "isPublic": result.get("isPublic", False),
        "createdBy": result.get("createdBy", ""),
        "createdDate": result.get("createdDate", ""),
    }


async def get_case(case_number: str) -> Dict:
    """
    Get case details by case number.

    Args:
        case_number: The case number (e.g., "01234567")

    Returns:
        Formatted case data with description, severity, issue, case number, and comments
    """
    client = get_client()
    path = f"/hydra/rest/v1/cases/{case_number}"
    data = await client.make_request("get", path)

    comments = data.get("comments", [])

    formatted_result = {
        "summary": data.get("summary", data.get("title", "")),
        "description": data.get("description"),
        "severity": data.get("severity"),
        "comments": [
            {
                "createdDate": comment.get("createdDate"),
                "createdBy": comment.get("createdBy"),
                "commentBody": comment.get("commentBody", comment.get("text", "")),
            }
            for comment in reversed(comments)
        ],
    }

    if "status" in data:
        formatted_result["status"] = data.get("status")
    if "product" in data:
        formatted_result["product"] = data.get("product")
    if "version" in data:
        formatted_result["version"] = data.get("version")
    if "ownerId" in data:
        formatted_result["ownerId"] = data.get("ownerId")
    if "createdDate" in data:
        formatted_result["createdDate"] = data.get("createdDate")
    if "openshiftClusterID" in data:
        formatted_result["openshiftClusterID"] = data.get("openshiftClusterID")
    if "openshiftClusterVersion" in data:
        formatted_result["openshiftClusterVersion"] = data.get("openshiftClusterVersion")
    if "externalTrackers" in data and isinstance(data["externalTrackers"], list):
        formatted_result["external_trackers"] = [
            {
                "resourceKey": tracker.get("resourceKey"),
                "resourceURL": tracker.get("resourceURL"),
                "status": tracker.get("status"),
                "system": tracker.get("system"),
                "title": tracker.get("title"),
            }
            for tracker in data["externalTrackers"]
            if any(tracker.get(k) for k in ("resourceKey", "resourceURL", "status", "system", "title"))
        ]
    if "caseResourceLinks" in data and isinstance(data["caseResourceLinks"], list):
        formatted_result["case_resource_links"] = [
            {
                "resourceType": link.get("resourceType"),
                "resourceViewURI": link.get("resourceViewURI"),
                "solutionTitle": link.get("solutionTitle"),
            }
            for link in data["caseResourceLinks"]
            if any(link.get(k) for k in ("resourceType", "resourceViewURI", "solutionTitle"))
        ]

    return formatted_result


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
    client = get_client()
    params: Dict = {"per_page": per_page, "page": page}
    if severity:
        params["severity"] = severity
    if product:
        params["product"] = product
    if package:
        params["package"] = package
    if advisory:
        params["advisory"] = advisory
    if cvss3_score is not None:
        params["cvss3_score"] = cvss3_score
    if after:
        params["after"] = after
    if before:
        params["before"] = before
    if created_days_ago is not None:
        params["created_days_ago"] = created_days_ago

    result = await client.make_request("get", "/hydra/rest/securitydata/cve.json", params=params)

    if isinstance(result, list):
        return [
            {
                "cve": item.get("CVE"),
                "severity": item.get("severity"),
                "public_date": item.get("public_date"),
                "description": item.get("bugzilla_description"),
                "cvss3_score": item.get("cvss3_score"),
                "cwe": item.get("CWE"),
                "advisories": item.get("advisories", []),
                "url": f"https://access.redhat.com/security/cve/{item.get('CVE')}",
            }
            for item in result
        ]
    return []


async def get_cve(cve_id: str) -> Dict:
    """
    Get detailed information about a specific CVE from Red Hat Security Data.

    Args:
        cve_id: The CVE identifier (e.g., "CVE-2026-31431")

    Returns:
        Detailed CVE information including severity, CVSS, affected releases, and fix status
    """
    client = get_client()
    result = await client.make_request("get", f"/hydra/rest/securitydata/cve/{cve_id}.json")

    affected = result.get("affected_release", [])
    if isinstance(affected, list):
        affected_releases = [
            {
                "product": rel.get("product_name"),
                "advisory": rel.get("advisory"),
                "package": rel.get("package"),
                "release_date": rel.get("release_date"),
            }
            for rel in affected[:20]
        ]
    else:
        affected_releases = []

    package_state = result.get("package_state", [])
    if isinstance(package_state, list):
        fix_state = [
            {
                "product": ps.get("product_name"),
                "fix_state": ps.get("fix_state"),
                "package": ps.get("package_name"),
            }
            for ps in package_state[:20]
        ]
    else:
        fix_state = []

    cvss3 = result.get("cvss3", {})
    bugzilla = result.get("bugzilla", {})
    details = result.get("details", [])

    return {
        "cve": cve_id,
        "severity": result.get("threat_severity"),
        "public_date": result.get("public_date"),
        "cvss3_score": cvss3.get("cvss3_base_score") if isinstance(cvss3, dict) else None,
        "cvss3_vector": cvss3.get("cvss3_scoring_vector") if isinstance(cvss3, dict) else None,
        "cwe": result.get("cwe"),
        "description": details[0] if details else "",
        "statement": result.get("statement"),
        "bugzilla_id": bugzilla.get("id") if isinstance(bugzilla, dict) else None,
        "bugzilla_url": bugzilla.get("url") if isinstance(bugzilla, dict) else None,
        "mitigation": result["mitigation"].get("value") if isinstance(result.get("mitigation"), dict) else result.get("mitigation"),
        "upstream_fix": result.get("upstream_fix"),
        "references": [url for ref in result.get("references", []) for url in ref.split("\n") if url.strip()],
        "affected_releases": affected_releases,
        "package_state": fix_state,
        "url": f"https://access.redhat.com/security/cve/{cve_id}",
    }
