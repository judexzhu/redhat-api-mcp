import pytest
import respx
from httpx import Response

from redhat_api_mcp import tools
from redhat_api_mcp.client import RedHatAPI

SSO_URL = "https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token"
BASE = "https://access.redhat.com"
PYXIS = "https://catalog.redhat.com/api/containers/v1/operators"


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


@pytest.mark.asyncio
@respx.mock
async def test_get_kcs_drupal_failure_fallback(respx_mock):
    _mock_token(respx_mock)
    respx_mock.post(f"{BASE}/hydra/rest/search/v2/kcs").mock(return_value=Response(200, json={
        "response": {"docs": [{"documentKind": "Solution", "publishedTitle": "Fallback Title", "abstract": "abs"}]}
    }))
    respx_mock.get(f"{BASE}/hydra/rest/drupal/solutions/9001").mock(return_value=Response(500))

    result = await tools.get_kcs("9001")
    assert result["title"] == "Fallback Title"


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


# ── search_errata ───────────────────────────────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_search_errata(respx_mock):
    _mock_token(respx_mock)
    respx_mock.get(f"{BASE}/hydra/rest/securitydata/csaf.json").mock(return_value=Response(200, json=[
        {
            "RHSA": "RHSA-2026:46885",
            "severity": "critical",
            "released_on": "2026-07-27",
            "title": "Security update for MCE",
            "CVEs": ["CVE-2026-16242"],
        },
    ]))

    result = await tools.search_errata(severity="critical")
    assert len(result) == 1
    assert result[0]["advisory_id"] == "RHSA-2026:46885"
    assert "CVE-2026-16242" in result[0]["cves"]


@pytest.mark.asyncio
@respx.mock
async def test_search_errata_empty(respx_mock):
    _mock_token(respx_mock)
    respx_mock.get(f"{BASE}/hydra/rest/securitydata/csaf.json").mock(return_value=Response(200, json=[]))

    result = await tools.search_errata(package="nonexistent")
    assert result == []


# ── get_errata ──────────────────────────────────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_get_errata(respx_mock):
    _mock_token(respx_mock)
    respx_mock.get(f"{BASE}/hydra/rest/securitydata/csaf/RHSA-2026:46885.json").mock(return_value=Response(200, json={
        "document": {
            "title": "Red Hat Security Advisory: MCE security update",
            "aggregate_severity": {"text": "Critical"},
            "tracking": {"current_release_date": "2026-07-27", "status": "final"},
            "notes": [{"category": "description", "text": "An update for MCE"}],
            "references": [{"url": "https://access.redhat.com/errata/RHSA-2026:46885"}],
        },
        "vulnerabilities": [
            {"cve": "CVE-2026-16242"},
            {"cve": "CVE-2025-58183"},
        ],
        "product_tree": {},
    }))

    result = await tools.get_errata("RHSA-2026:46885")
    assert result["advisory_id"] == "RHSA-2026:46885"
    assert result["severity"] == "Critical"
    assert result["cve_count"] == 2
    assert "CVE-2026-16242" in result["cves"]
    assert result["description"] == "An update for MCE"


# ── list_attachments ────────────────────────────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_list_attachments(respx_mock):
    _mock_token(respx_mock)
    respx_mock.get("https://api.access.redhat.com/support/v1/cases/01234567/attachments").mock(return_value=Response(200, json=[
        {"uuid": "abc-123", "fileName": "must-gather.tar.gz", "sizeKB": 5120},
    ]))

    result = await tools.list_attachments("01234567")
    assert len(result) == 1
    assert result[0]["uuid"] == "abc-123"
    assert result[0]["filename"] == "must-gather.tar.gz"
    assert result[0]["size_kb"] == 5120


@pytest.mark.asyncio
@respx.mock
async def test_get_attachment(respx_mock, tmp_path, monkeypatch):
    _mock_token(respx_mock)
    respx_mock.get("https://api.access.redhat.com/support/v1/cases/01234567/attachments").mock(return_value=Response(200, json=[
        {"uuid": "abc-123", "fileName": "notes.txt", "sizeKB": 1},
    ]))
    respx_mock.get("https://api.access.redhat.com/support/v1/cases/01234567/attachments/abc-123").mock(return_value=Response(200, content=b"hello world"))

    monkeypatch.setattr("redhat_api_mcp.tools.Path", lambda *a: tmp_path.joinpath(*[str(p).lstrip("/") for p in a]))

    result = await tools.get_attachment("01234567", "abc-123")
    assert result["filename"] == "notes.txt"
    assert result["size_bytes"] == 11


# ── get_doc ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_doc_invalid_url():
    with pytest.raises(ValueError, match="docs.redhat.com"):
        await tools.get_doc("https://google.com/something")


@pytest.mark.asyncio
@respx.mock
async def test_get_doc(respx_mock):
    html = """<html><head><title>Test Doc</title></head><body>
    <nav>global nav</nav>
    <main>
      <div class="breadcrumbs">Home &gt; Docs</div>
      <nav>Table of contents</nav>
      <div class="toc-container">TOC items</div>
      <div class="mobile-nav-wrapper">mobile</div>
      <select><option>Multi-page</option></select>
      <h1>Hello</h1>
      <p>Doc content here</p>
      <pre>$ oc get pods</pre>
      <ul><li>Item one</li><li>Item two</li></ul>
      <span>Copy link</span>
      <span>Format</span>
    </main>
    </body></html>"""
    respx_mock.get("https://docs.redhat.com/en/doc/test").mock(return_value=Response(200, text=html))

    result = await tools.get_doc("https://docs.redhat.com/en/doc/test")
    assert result["title"] == "Test Doc"
    assert "Doc content here" in result["content"]
    assert "# Hello" in result["content"]
    assert "```" in result["content"]
    assert "oc get pods" in result["content"]
    assert "- Item one" in result["content"]
    assert "global nav" not in result["content"]
    assert "breadcrumbs" not in result["content"]
    assert "TOC items" not in result["content"]
    assert "Copy link" not in result["content"]
    assert "Multi-page" not in result["content"]


@pytest.mark.asyncio
@respx.mock
async def test_get_doc_no_main(respx_mock):
    html = "<html><head><title>No Main</title></head><body><p>orphan</p></body></html>"
    respx_mock.get("https://docs.redhat.com/en/doc/empty").mock(return_value=Response(200, text=html))

    result = await tools.get_doc("https://docs.redhat.com/en/doc/empty")
    assert result["title"] == "No Main"
    assert result["content"] == ""


@pytest.mark.asyncio
@respx.mock
async def test_get_doc_tables_and_inline_code(respx_mock):
    html = """<html><head><title>Rich Doc</title></head><body>
    <main>
      <table><tr><th>Name</th><th>Value</th></tr><tr><td>cpu</td><td>4</td></tr></table>
      <p>Run oc login first</p>
      <div><section><p>Nested content</p></section></div>
      <blockquote><p>Quoted text</p></blockquote>
      <span>Other element text</span>
      <script>var x=1;</script>
      <style>.x{color:red}</style>
    </main>
    </body></html>"""
    respx_mock.get("https://docs.redhat.com/en/doc/rich").mock(return_value=Response(200, text=html))

    result = await tools.get_doc("https://docs.redhat.com/en/doc/rich")
    assert "| Name | Value |" in result["content"]
    assert "| --- | --- |" in result["content"]
    assert "| cpu | 4 |" in result["content"]
    assert "Run oc login first" in result["content"]
    assert "Nested content" in result["content"]
    assert "Quoted text" in result["content"]
    assert "Other element text" in result["content"]
    assert "var x=1" not in result["content"]


# ── client coverage ────────────────────────────────────────────────


def test_client_missing_token(monkeypatch, tmp_path):
    monkeypatch.delenv("RH_API_OFFLINE_TOKEN", raising=False)
    monkeypatch.delenv("RH_API_BASE_URL", raising=False)
    monkeypatch.delenv("RH_SSO_URL", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("redhat_api_mcp.client.load_dotenv", lambda: None)
    with pytest.raises(ValueError, match="RH_API_OFFLINE_TOKEN"):
        RedHatAPI()


@pytest.mark.asyncio
async def test_client_close(monkeypatch):
    monkeypatch.setenv("RH_API_OFFLINE_TOKEN", "fake")
    client = RedHatAPI()
    await client.close()


@pytest.mark.asyncio
@respx.mock
async def test_client_unsupported_method(respx_mock):
    _mock_token(respx_mock)
    client = tools.get_client()
    with pytest.raises(ValueError, match="Unsupported method"):
        await client.make_request("delete", "/test")


@pytest.mark.asyncio
@respx.mock
async def test_client_non_json_response(respx_mock):
    _mock_token(respx_mock)
    respx_mock.get(f"{BASE}/test").mock(return_value=Response(200, text="plain text", headers={"content-type": "text/plain"}))

    client = tools.get_client()
    result = await client.make_request("get", "/test")
    assert result == {"content": "plain text"}


# ── get_kcs extra branches ────────────────────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_get_kcs_with_abstract_and_list_fields(respx_mock):
    _mock_token(respx_mock)
    respx_mock.post(f"{BASE}/hydra/rest/search/v2/kcs").mock(return_value=Response(200, json={
        "response": {"docs": [{"documentKind": "Solution"}]}
    }))
    respx_mock.get(f"{BASE}/hydra/rest/drupal/solutions/5001").mock(return_value=Response(200, json={
        "isTeaser": False,
        "title": "With Abstract",
        "environment": ["RHEL 9", "RHEL 8"],
        "issue": {"text": "Issue text"},
        "resolution": {"text": "Fix it"},
        "rootCause": {"text": "Root cause"},
        "bodyAbstract": {"text": "Abstract text"},
    }))

    result = await tools.get_kcs("5001")
    assert result["title"] == "With Abstract"
    assert result["abstract"] == "Abstract text"
    assert result["environment"] == "RHEL 9"


@pytest.mark.asyncio
@respx.mock
async def test_get_kcs_empty_search(respx_mock):
    _mock_token(respx_mock)
    respx_mock.post(f"{BASE}/hydra/rest/search/v2/kcs").mock(return_value=Response(200, json={
        "response": {"docs": []}
    }))
    respx_mock.get(f"{BASE}/hydra/rest/drupal/solutions/0000").mock(return_value=Response(404))

    result = await tools.get_kcs("0000")
    assert result["title"] == ""
    assert result["resolution"] == ""


# ── search_docs with product filter ───────────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_search_docs_with_product(respx_mock):
    _mock_token(respx_mock)
    respx_mock.get(f"{BASE}/hydra/rest/search/platform/docs").mock(return_value=Response(200, json={
        "response": {"docs": [{"allTitle": "ROSA Guide", "view_uri": "https://docs.redhat.com/rosa"}]}
    }))

    result = await tools.search_docs("ROSA", product="Red Hat OpenShift Service on AWS")
    assert len(result) == 1


# ── get_case with all optional fields ─────────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_get_case_all_optional_fields(respx_mock):
    _mock_token(respx_mock)
    respx_mock.get(f"{BASE}/hydra/rest/v1/cases/01234567").mock(return_value=Response(200, json={
        "summary": "Full case",
        "severity": "2",
        "comments": [],
        "status": "Closed",
        "product": "OpenShift",
        "version": "4.14",
        "ownerId": "engineer@redhat.com",
        "createdDate": "2026-01-01",
        "openshiftClusterID": "abc-123",
        "openshiftClusterVersion": "4.14.12",
    }))

    result = await tools.get_case("01234567")
    assert result["status"] == "Closed"
    assert result["product"] == "OpenShift"
    assert result["version"] == "4.14"
    assert result["ownerId"] == "engineer@redhat.com"
    assert result["createdDate"] == "2026-01-01"
    assert result["openshiftClusterID"] == "abc-123"
    assert result["openshiftClusterVersion"] == "4.14.12"


# ── search_cve with all params ────────────────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_search_cve_all_params(respx_mock):
    _mock_token(respx_mock)
    respx_mock.get(f"{BASE}/hydra/rest/securitydata/cve.json").mock(return_value=Response(200, json=[
        {"CVE": "CVE-2026-9999", "severity": "critical"},
    ]))

    result = await tools.search_cve(
        severity="critical", product="openshift", package="kernel",
        advisory="RHSA-2026:0001", cvss3_score=7.0,
        after="2026-01-01", before="2026-12-31", created_days_ago=30,
    )
    assert len(result) == 1
    assert result[0]["cve"] == "CVE-2026-9999"


# ── get_cve minimal (no affected_release, no package_state) ───────


@pytest.mark.asyncio
@respx.mock
async def test_get_cve_minimal(respx_mock):
    _mock_token(respx_mock)
    respx_mock.get(f"{BASE}/hydra/rest/securitydata/cve/CVE-2026-0002.json").mock(return_value=Response(200, json={
        "threat_severity": "Low",
        "public_date": "2026-06-01",
        "affected_release": "not-a-list",
        "package_state": "not-a-list",
    }))

    result = await tools.get_cve("CVE-2026-0002")
    assert result["severity"] == "Low"
    assert result["affected_releases"] == []
    assert result["package_state"] == []


# ── search_errata with all params ─────────────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_search_errata_all_params(respx_mock):
    _mock_token(respx_mock)
    respx_mock.get(f"{BASE}/hydra/rest/securitydata/csaf.json").mock(return_value=Response(200, json=[
        {"RHSA": "RHSA-2026:0001", "severity": "important"},
    ]))

    result = await tools.search_errata(
        advisory="RHSA-2026:0001", cve="CVE-2026-0001", severity="important",
        package="kernel", after="2026-01-01", before="2026-12-31", created_days_ago=7,
    )
    assert len(result) == 1


# ── list_attachments empty ─────────────────────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_list_attachments_non_list(respx_mock):
    _mock_token(respx_mock)
    respx_mock.get("https://api.access.redhat.com/support/v1/cases/01234567/attachments").mock(
        return_value=Response(200, json={"error": "none"})
    )

    result = await tools.list_attachments("01234567")
    assert result == []


# ── get_attachment not found ───────────────────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_get_attachment_not_found(respx_mock):
    _mock_token(respx_mock)
    respx_mock.get("https://api.access.redhat.com/support/v1/cases/01234567/attachments").mock(
        return_value=Response(200, json=[{"uuid": "other", "fileName": "x.txt", "sizeKB": 1}])
    )

    with pytest.raises(ValueError, match="not found"):
        await tools.get_attachment("01234567", "nonexistent-uuid")


# ── search_cve/errata dict response (non-list) ────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_search_cve_dict_response(respx_mock):
    _mock_token(respx_mock)
    respx_mock.get(f"{BASE}/hydra/rest/securitydata/cve.json").mock(
        return_value=Response(200, json={"error": "bad request"})
    )

    result = await tools.search_cve()
    assert result == []


@pytest.mark.asyncio
@respx.mock
async def test_search_errata_dict_response(respx_mock):
    _mock_token(respx_mock)
    respx_mock.get(f"{BASE}/hydra/rest/securitydata/csaf.json").mock(
        return_value=Response(200, json={"error": "bad request"})
    )

    result = await tools.search_errata()
    assert result == []


# ── _html_to_markdown remaining branches ──────────────────────────


@pytest.mark.asyncio
@respx.mock
async def test_get_doc_inline_code_and_bare_text(respx_mock):
    html = """<html><head><title>Code Doc</title></head><body>
    <main>
      bare text node
      <code>kubectl</code>
    </main>
    </body></html>"""
    respx_mock.get("https://docs.redhat.com/en/doc/code").mock(return_value=Response(200, text=html))

    result = await tools.get_doc("https://docs.redhat.com/en/doc/code")
    assert "bare text node" in result["content"]
    assert "`kubectl`" in result["content"]


# ── list_operator_bundles ────────────────────────────────────────


PYXIS_BUNDLES = [
    {
        "version": "1.23.1", "channel_name": "latest", "ocp_version": "4.19",
        "skip_range": ">=1.22.0 <1.23.1", "latest_in_channel": True,
    },
    {
        "version": "1.23.1", "channel_name": "pipelines-1.23", "ocp_version": "4.19",
        "skip_range": ">=1.22.0 <1.23.1", "latest_in_channel": True,
    },
    {
        "version": "1.22.5", "channel_name": "pipelines-1.22", "ocp_version": "4.19",
        "skip_range": ">=1.21.0 <1.22.5", "latest_in_channel": True,
    },
    {
        "version": "1.22.4", "channel_name": "pipelines-1.22", "ocp_version": "4.19",
        "skip_range": ">=1.21.0 <1.22.4", "latest_in_channel": False,
    },
]


def _pyxis_bundles_response(bundles=PYXIS_BUNDLES):
    return Response(200, json={"data": bundles, "total": len(bundles)})


def _pyxis_packages_response():
    return Response(200, json={
        "data": [
            {"package_name": "openshift-pipelines-operator-rh", "source": "redhat-operators"},
            {"package_name": "servicemeshoperator", "source": "redhat-operators"},
            {"package_name": "cluster-logging", "source": "redhat-operators"},
        ],
        "total": 3,
    })


@pytest.mark.asyncio
@respx.mock
async def test_list_operator_bundles_latest_default(respx_mock):
    _mock_token(respx_mock)
    respx_mock.get(url__startswith=f"{PYXIS}/bundles").mock(return_value=_pyxis_bundles_response())

    result = await tools.list_operator_bundles("openshift-pipelines-operator-rh", "4.19")
    assert result["package"] == "openshift-pipelines-operator-rh"
    assert result["ocp_version"] == "4.19"
    assert result["channels"] == 3
    assert all(b["latest_in_channel"] for b in result["bundles"])


@pytest.mark.asyncio
@respx.mock
async def test_list_operator_bundles_channel_filter(respx_mock):
    _mock_token(respx_mock)
    respx_mock.get(url__startswith=f"{PYXIS}/bundles").mock(return_value=_pyxis_bundles_response())

    result = await tools.list_operator_bundles("openshift-pipelines-operator-rh", "4.19", channel="pipelines-1.22")
    assert result["channel"] == "pipelines-1.22"
    assert result["total"] == 2
    assert result["bundles"][0]["version"] == "1.22.5"
    assert result["bundles"][1]["version"] == "1.22.4"


@pytest.mark.asyncio
@respx.mock
async def test_list_operator_bundles_did_you_mean(respx_mock):
    _mock_token(respx_mock)
    import json
    respx_mock.get(url__startswith=f"{PYXIS}/bundles").mock(
        return_value=Response(200, text=json.dumps({"data": [], "total": 0}))
    )
    respx_mock.get(url__startswith=f"{PYXIS}/packages").mock(return_value=_pyxis_packages_response())

    result = await tools.list_operator_bundles("mesh")
    assert "did_you_mean" in result
    assert "servicemeshoperator" in result["did_you_mean"]


@pytest.mark.asyncio
@respx.mock
async def test_list_operator_bundles_no_ocp_version(respx_mock):
    _mock_token(respx_mock)
    respx_mock.get(url__startswith=f"{PYXIS}/bundles").mock(return_value=_pyxis_bundles_response())

    result = await tools.list_operator_bundles("openshift-pipelines-operator-rh")
    assert result["ocp_version"] == "all"


@pytest.mark.asyncio
@respx.mock
async def test_list_operator_bundles_cache_hit(respx_mock):
    _mock_token(respx_mock)
    route = respx_mock.get(url__startswith=f"{PYXIS}/bundles").mock(return_value=_pyxis_bundles_response())

    await tools.list_operator_bundles("openshift-pipelines-operator-rh", "4.19")
    await tools.list_operator_bundles("openshift-pipelines-operator-rh", "4.19", channel="pipelines-1.22")
    assert route.call_count == 1
