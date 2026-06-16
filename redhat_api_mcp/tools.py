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
