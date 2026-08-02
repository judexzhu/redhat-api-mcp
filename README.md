# Red Hat API MCP Server & CLI

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io)
[![UV](https://img.shields.io/badge/package%20manager-uv-blue)](https://docs.astral.sh/uv/)

This project implements a [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server **and CLI** that provides tools for interacting with [Red Hat APIs](https://developers.redhat.com/api-catalog/api/case-management), making it easy to integrate with LLM applications or use directly from the terminal.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [CLI](#cli)
- [Available Tools](#available-tools)
- [Claude Code Skill](#claude-code-skill)
- [Advanced Usage](#advanced-usage)

## Features

The server exposes the following Red Hat API tools:

1. **Search KCS Solutions** (`search_kcs`) - Search knowledge base solutions and articles
2. **Get KCS Solution** (`get_kcs`) - Retrieve full solution content by ID
3. **Search Documentation** (`search_docs`) - Search Red Hat product documentation (docs.redhat.com)
4. **Get Documentation Page** (`get_doc`) - Fetch full content from a docs.redhat.com page
5. **Search Cases** (`search_cases`) - Find support cases matching a query
6. **Get Case Details** (`get_case`) - Retrieve detailed case information with comments
7. **Add Case Comment** (`add_comment`) - Post a private comment to a support case
8. **Search CVEs** (`search_cve`) - Search Red Hat CVEs via the Security Data API
9. **Get CVE Details** (`get_cve`) - Get detailed CVE information including affected releases

## Prerequisites

- Python 3.13 or higher
- [UV package manager](https://docs.astral.sh/uv/) (recommended Python package manager)
- Red Hat API offline token (obtained from your Red Hat account)

## Installation

### 1. Install UV (if not already installed)

### 2. Clone and Setup Project

```bash
git clone <your-repository-url>
cd redhat-api-mcp
uv sync
```

### 3. Install CLI globally (optional)

```bash
uv tool install .
```

This makes the `rhapi` command available system-wide at `~/.local/bin/rhapi`.

## Configuration

### 1. Get Your Red Hat API Token

1. Visit the [Red Hat API Token Management page](https://access.redhat.com/management/api) per [KCS](https://access.redhat.com/articles/3626371)
2. Log in to your Red Hat account
3. Generate an offline token
4. Copy and save the token securely

### 2. Environment Setup

Create a `.env` file in the project root with your Red Hat API token:

```bash
# Create .env file
echo "RH_API_OFFLINE_TOKEN=your_offline_token_here" > .env
```

Replace `your_offline_token_here` with your actual offline token from step 1.

## Usage

### Developing with the MCP Inspector

You can test the server using the MCP development tools:

```bash
uv run mcp dev redhat_mcp_server.py
```

This will start the MCP inspector, allowing you to interact with your tools interactively.

### Integrating with Claude Desktop

To install the server in Claude Desktop, add this configuration to your Claude Desktop config file.

```json
{
  "mcpServers": {
    "redhat": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/your/redhat-api-mcp",
        "run",
        "redhat_mcp_server.py"
      ],
      "env": {
        "RH_API_OFFLINE_TOKEN": "your_actual_offline_token_here"
      }
    }
  }
}
```

### Integrating with Claude Code

#### Option 1: CLI (recommended)

```bash
claude mcp add --scope user redhat \
  -e RH_API_OFFLINE_TOKEN=your_actual_offline_token_here \
  -- uv --directory /path/to/your/redhat-api-mcp run redhat_mcp_server.py
```

#### Option 2: Project config (`.mcp.json`)

Create `.mcp.json` in your project root to share with teammates:

```json
{
  "mcpServers": {
    "redhat": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/your/redhat-api-mcp",
        "run",
        "redhat_mcp_server.py"
      ],
      "env": {
        "RH_API_OFFLINE_TOKEN": "your_actual_offline_token_here"
      }
    }
  }
}
```

See [Claude Code MCP docs](https://code.claude.com/docs/en/mcp-quickstart) for details on scopes and authentication.

## CLI

The `rhapi` CLI exposes the same tools as the MCP server, usable directly from the terminal.

```bash
# Search cases (query defaults to *:* when using only filters)
rhapi search-cases --account 12345678 --months 12 --rows 50
rhapi search-cases "apiserver timeout" --months 6

# Get case details
rhapi get-case 01234567

# Add a private comment to a case
rhapi add-comment 01234567 "Investigating the issue"

# Search KCS articles
rhapi search-kcs "OCP upgrade" --rows 10

# Get a specific KCS solution
rhapi get-kcs 1234567

# Search Red Hat documentation
rhapi search-docs "ROSA networking" --product "Red Hat OpenShift Service on AWS"

# Fetch full content from a documentation page
rhapi get-doc https://docs.redhat.com/en/documentation/...

# Search CVEs
rhapi search-cve --severity critical --after 2026-01-01
rhapi search-cve --product openshift --package kernel

# Get CVE details
rhapi get-cve CVE-2026-31431

# Output formats: json (default), table, or markdown
rhapi search-cases --months 3 -o table
rhapi get-case 01234567 -o md
```

If installed locally (without `uv tool install`), prefix with `uv run`:

```bash
uv run rhapi search-cases --months 6
```

## Available Tools

### search_kcs

Search for Red Hat KCS Solutions and Articles.

```python
search_kcs(query: str, rows: int = 50, start: int = 0) -> List[Dict]
```

**Parameters:**

- `query` (str): Search terms (supports advanced Solr syntax)
- `rows` (int, optional): Number of results to return (default: 50, max: 100)
- `start` (int, optional): Starting index for pagination (default: 0)

**Returns:** List of solution objects with id, title, score, and view_uri

### get_kcs

Get a Red Hat solution by its ID and extract structured content.

```python
get_kcs(solution_id: str) -> Dict
```

**Parameters:**

- `solution_id` (str): The KCS solution ID

**Returns:** Dictionary with title, environment, issue, resolution, and root_cause

### search_docs

Search Red Hat product documentation (docs.redhat.com).

```python
search_docs(query: str, rows: int = 10, start: int = 0, product: str = None) -> List[Dict]
```

**Parameters:**

- `query` (str): Search terms
- `rows` (int, optional): Number of results to return (default: 10)
- `start` (int, optional): Starting index for pagination (default: 0)
- `product` (str, optional): Filter by product name (e.g. "Red Hat OpenShift Service on AWS")

**Returns:** List of documentation pages with title, abstract, url, and last_modified

### get_doc

Fetch full content from a Red Hat documentation page.

```python
get_doc(url: str) -> Dict
```

**Parameters:**

- `url` (str): Full URL of the docs.redhat.com page

**Returns:** Dictionary with title, url, and plain-text content extracted from the page

### search_cases

Search for Red Hat support cases.

```python
search_cases(query: str, rows: int = 10, start: int = 0, account_number: str = None, created_within_months: int = None) -> List[Dict]
```

**Parameters:**

- `query` (str): Search terms
- `rows` (int, optional): Number of results to return (default: 10)
- `start` (int, optional): Starting index for pagination (default: 0)
- `account_number` (str, optional): Filter by customer EBS account number
- `created_within_months` (int, optional): Only return cases created within N months

**Returns:** List of case objects with case_number, summary, status, product, etc.

### get_case

Get detailed information about a specific Red Hat support case.

```python
get_case(case_number: str) -> Dict
```

**Parameters:**

- `case_number` (str): The Red Hat case number (e.g., "01234567")

**Returns:** Detailed case information with summary, description, severity, comments, external trackers, and linked resources

### add_comment

Add a private comment to a Red Hat support case.

```python
add_comment(case_number: str, body: str) -> Dict
```

**Parameters:**

- `case_number` (str): The Red Hat case number (e.g., "01234567")
- `body` (str): The comment text (supports markdown)

**Returns:** The created comment with author and timestamp. Comments are always private (never customer-visible).

### search_cve

Search Red Hat CVEs via the Security Data API.

```python
search_cve(severity: str = None, product: str = None, package: str = None, advisory: str = None, cvss3_score: float = None, after: str = None, before: str = None, created_days_ago: int = None, per_page: int = 10, page: int = 1) -> List[Dict]
```

**Parameters:**

- `severity` (str, optional): Filter by severity (low, moderate, important, critical)
- `product` (str, optional): Filter by product (e.g. "openshift")
- `package` (str, optional): Filter by package name (e.g. "kernel", "samba")
- `advisory` (str, optional): Filter by advisory (e.g. "RHSA-2026:13565")
- `cvss3_score` (float, optional): Minimum CVSSv3 score (e.g. 7.0, 9.0)
- `after` (str, optional): Only CVEs published after this date (YYYY-MM-DD)
- `before` (str, optional): Only CVEs published before this date (YYYY-MM-DD)
- `created_days_ago` (int, optional): Only CVEs created within N days
- `per_page` (int, optional): Number of results to return (default: 10)
- `page` (int, optional): Page number for pagination (default: 1)

**Returns:** List of CVEs with severity, CVSS score, and advisories

### get_cve

Get detailed information about a specific CVE.

```python
get_cve(cve_id: str) -> Dict
```

**Parameters:**

- `cve_id` (str): The CVE identifier (e.g., "CVE-2026-31431")

**Returns:** Detailed CVE information including severity, CVSS, affected releases, fix status, mitigation, and references

## Claude Code Skill

A ready-to-use Claude Code skill is included in `skills/rhapi-cli/`. It teaches the agent how to use the `rhapi` CLI for case and KCS lookups.

To install it, copy the skill to your Claude Code commands directory:

```bash
# Project-level (available in a specific project)
cp skills/rhapi-cli/SKILL.md /path/to/project/.claude/commands/rhapi.md

# Global (available in all projects)
cp skills/rhapi-cli/SKILL.md ~/.claude/commands/rhapi.md
```

## Advanced Usage

### Advanced Query Parameters

For detailed information about using advanced Solr query expressions with the Red Hat Hydra API, see [expression.md](./expression.md).

### Running Tests

```bash
uv run pytest tests/ -v
```

### Custom Configuration

You can override default API endpoints by adding these to your `.env` file:

```bash
# Optional: Custom API endpoints
RH_API_BASE_URL=https://access.redhat.com
RH_SSO_URL=https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Note**: This MCP server requires a valid Red Hat account and API access. Ensure you have the appropriate permissions for the Red Hat services you intend to access.
