import pytest
import respx
from httpx import Response

from redhat_api_mcp import tools

SSO_URL = "https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token"
BASE = "https://access.redhat.com"


def _mock_token(respx_mock):
    respx_mock.post(SSO_URL).mock(return_value=Response(200, json={
        "access_token": "fake-token",
        "expires_in": 900,
    }))


# ── search_kcs ──────────────────────────────────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_search_kcs(respx_mock):
    _mock_token(respx_mock)
    respx_mock.post(f"{BASE}/hydra/rest/search/v2/kcs").mock(return_value=Response(200, json={
        "response": {
            "docs": [
                {"id": "123", "allTitle": "Test KCS", "score": 1.5, "view_uri": "https://example.com/123"},
            ]
        }
    }))

    result = await tools.search_kcs("test")
    assert len(result) == 1
    assert result[0]["id"] == "123"
    assert result[0]["title"] == "Test KCS"


@pytest.mark.asyncio
@respx.mock
async def test_search_kcs_empty(respx_mock):
    _mock_token(respx_mock)
    respx_mock.post(f"{BASE}/hydra/rest/search/v2/kcs").mock(return_value=Response(200, json={
        "response": {"docs": []}
    }))

    result = await tools.search_kcs("nothing")
    assert result == []


# ── get_kcs ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_get_kcs_full_drupal(respx_mock):
    _mock_token(respx_mock)
    respx_mock.post(f"{BASE}/hydra/rest/search/v2/kcs").mock(return_value=Response(200, json={
        "response": {"docs": [{"documentKind": "Solution"}]}
    }))
    respx_mock.get(f"{BASE}/hydra/rest/drupal/solutions/7001").mock(return_value=Response(200, json={
        "isTeaser": False,
        "title": "Full Solution",
        "environment": {"text": "RHEL 9"},
        "issue": {"text": "Crash on boot"},
        "resolution": {"text": "Update kernel"},
        "rootCause": {"text": "Bug in driver"},
    }))

    result = await tools.get_kcs("7001")
    assert result["title"] == "Full Solution"
    assert result["resolution"] == "Update kernel"


@pytest.mark.asyncio
@respx.mock
async def test_get_kcs_teaser_fallback(respx_mock):
    _mock_token(respx_mock)
    respx_mock.post(f"{BASE}/hydra/rest/search/v2/kcs").mock(return_value=Response(200, json={
        "response": {"docs": [{"documentKind": "Article", "publishedTitle": "Teaser Title", "abstract": "summary"}]}
    }))
    respx_mock.get(f"{BASE}/hydra/rest/drupal/articles/8001").mock(return_value=Response(200, json={
        "isTeaser": True,
    }))

    result = await tools.get_kcs("8001")
    assert result["title"] == "Teaser Title"


# ── search_docs ─────────────────────────────────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_search_docs(respx_mock):
    _mock_token(respx_mock)
    respx_mock.get(f"{BASE}/hydra/rest/search/platform/docs").mock(return_value=Response(200, json={
        "response": {
            "docs": [
                {"allTitle": "ROSA Guide", "abstract": "Guide for ROSA", "view_uri": "https://docs.redhat.com/rosa", "lastModifiedDate": "2026-01-01"},
            ]
        }
    }))

    result = await tools.search_docs("ROSA")
    assert len(result) == 1
    assert result[0]["title"] == "ROSA Guide"
    assert result[0]["url"] == "https://docs.redhat.com/rosa"


# ── search_cases ────────────────────────────────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_search_cases(respx_mock):
    _mock_token(respx_mock)
    respx_mock.post(f"{BASE}/hydra/rest/search/v2/cases").mock(return_value=Response(200, json={
        "response": {
            "docs": [
                {
                    "case_number": "01234567",
                    "case_summary": "Cluster down",
                    "case_status": "Waiting on Red Hat",
                    "case_product": "OpenShift",
                    "case_version": "4.14",
                    "case_severity": "1 (Urgent)",
                    "case_owner": "sre@redhat.com",
                    "case_createdDate": "2026-01-01",
                    "case_createdByName": "Customer",
                    "case_lastModifiedDate": "2026-01-02",
                    "uri": "https://access.redhat.com/support/cases/01234567",
                },
            ]
        }
    }))

    result = await tools.search_cases("cluster down")
    assert len(result) == 1
    assert result[0]["case_number"] == "01234567"
    assert result[0]["summary"] == "Cluster down"


@pytest.mark.asyncio
@respx.mock
async def test_search_cases_with_filters(respx_mock):
    _mock_token(respx_mock)
    respx_mock.post(f"{BASE}/hydra/rest/search/v2/cases").mock(return_value=Response(200, json={
        "response": {"docs": []}
    }))

    result = await tools.search_cases("*:*", account_number="12345678", created_within_months=6)
    assert result == []


# ── add_comment ─────────────────────────────────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_add_comment(respx_mock):
    _mock_token(respx_mock)
    respx_mock.post(f"{BASE}/hydra/rest/v1/cases/01234567/comments").mock(return_value=Response(200, json={
        "commentBody": "test comment",
        "isPublic": False,
        "createdBy": "user@redhat.com",
        "createdDate": "2026-01-01",
    }))

    result = await tools.add_comment("01234567", "test comment")
    assert result["case_number"] == "01234567"
    assert result["isPublic"] is False
    assert result["commentBody"] == "test comment"


# ── get_case ────────────────────────────────────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_get_case(respx_mock):
    _mock_token(respx_mock)
    respx_mock.get(f"{BASE}/hydra/rest/v1/cases/01234567").mock(return_value=Response(200, json={
        "summary": "Cluster crash",
        "description": "Cluster crashed after upgrade",
        "severity": "1 (Urgent)",
        "status": "Waiting on Red Hat",
        "product": "OpenShift",
        "version": "4.14",
        "comments": [
            {"createdDate": "2026-01-01", "createdBy": "user", "commentBody": "first comment"},
        ],
    }))

    result = await tools.get_case("01234567")
    assert result["summary"] == "Cluster crash"
    assert result["severity"] == "1 (Urgent)"
    assert len(result["comments"]) == 1


@pytest.mark.asyncio
@respx.mock
async def test_get_case_with_external_trackers(respx_mock):
    _mock_token(respx_mock)
    respx_mock.get(f"{BASE}/hydra/rest/v1/cases/01234567").mock(return_value=Response(200, json={
        "summary": "Bug",
        "severity": "2",
        "comments": [],
        "externalTrackers": [
            {"resourceKey": "OCPBUGS-123", "resourceURL": "https://issues.redhat.com/browse/OCPBUGS-123", "status": "Open", "system": "Jira", "title": "Bug title"},
        ],
        "caseResourceLinks": [
            {"resourceType": "KCS", "resourceViewURI": "https://access.redhat.com/solutions/123", "solutionTitle": "KCS title"},
        ],
    }))

    result = await tools.get_case("01234567")
    assert len(result["external_trackers"]) == 1
    assert result["external_trackers"][0]["resourceKey"] == "OCPBUGS-123"
    assert len(result["case_resource_links"]) == 1


# ── search_cve ──────────────────────────────────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_search_cve(respx_mock):
    _mock_token(respx_mock)
    respx_mock.get(f"{BASE}/hydra/rest/securitydata/cve.json").mock(return_value=Response(200, json=[
        {
            "CVE": "CVE-2026-0001",
            "severity": "important",
            "public_date": "2026-01-01",
            "bugzilla_description": "A bad bug",
            "cvss3_score": "8.1",
            "CWE": "CWE-79",
            "advisories": ["RHSA-2026:0001"],
        },
    ]))

    result = await tools.search_cve(severity="important")
    assert len(result) == 1
    assert result[0]["cve"] == "CVE-2026-0001"
    assert result[0]["severity"] == "important"


@pytest.mark.asyncio
@respx.mock
async def test_search_cve_empty(respx_mock):
    _mock_token(respx_mock)
    respx_mock.get(f"{BASE}/hydra/rest/securitydata/cve.json").mock(return_value=Response(200, json=[]))

    result = await tools.search_cve()
    assert result == []


# ── get_cve ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_get_cve(respx_mock):
    _mock_token(respx_mock)
    respx_mock.get(f"{BASE}/hydra/rest/securitydata/cve/CVE-2026-0001.json").mock(return_value=Response(200, json={
        "threat_severity": "Important",
        "public_date": "2026-01-01",
        "cvss3": {"cvss3_base_score": "8.1", "cvss3_scoring_vector": "CVSS:3.1/AV:N"},
        "cwe": "CWE-79",
        "details": ["Memory corruption in kernel"],
        "statement": "Affects RHEL 9",
        "bugzilla": {"id": "12345", "url": "https://bugzilla.redhat.com/12345"},
        "mitigation": {"value": "Disable module"},
        "upstream_fix": "kernel-6.1.5",
        "references": ["https://example.com/ref1\nhttps://example.com/ref2"],
        "affected_release": [
            {"product_name": "RHEL 9", "advisory": "RHSA-2026:0001", "package": "kernel-6.1.4", "release_date": "2026-02-01"},
        ],
        "package_state": [
            {"product_name": "RHEL 8", "fix_state": "Not affected", "package_name": "kernel"},
        ],
    }))

    result = await tools.get_cve("CVE-2026-0001")
    assert result["cve"] == "CVE-2026-0001"
    assert result["severity"] == "Important"
    assert result["cvss3_score"] == "8.1"
    assert len(result["affected_releases"]) == 1
    assert len(result["references"]) == 2


# ── get_doc ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_doc_invalid_url():
    with pytest.raises(ValueError, match="docs.redhat.com"):
        await tools.get_doc("https://google.com/something")


@pytest.mark.asyncio
@respx.mock
async def test_get_doc(respx_mock):
    html = """<html><head><title>Test Doc</title></head><body>
    <nav>sidebar</nav>
    <main><h1>Hello</h1><p>Doc content here</p></main>
    </body></html>"""
    respx_mock.get("https://docs.redhat.com/en/doc/test").mock(return_value=Response(200, text=html))

    result = await tools.get_doc("https://docs.redhat.com/en/doc/test")
    assert result["title"] == "Test Doc"
    assert "Doc content here" in result["content"]
    assert "sidebar" not in result["content"]
