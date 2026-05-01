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

1. **Search Red Hat KCS Solutions** - Search for knowledge base solutions
2. **Get Solution by ID** - Retrieve full solution content
3. **Search Red Hat Cases** - Find cases matching a query
4. **Get Case Details** - Retrieve detailed information about a specific case

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


## CLI

The `rhapi` CLI exposes the same tools as the MCP server, usable directly from the terminal.

```bash
# Search cases (query defaults to *:* when using only filters)
rhapi search-cases --account 12345678 --months 12 --rows 50
rhapi search-cases "apiserver timeout" --months 6

# Get case details
rhapi get-case 01234567

# Search KCS articles
rhapi search-kcs "OCP upgrade" --rows 10

# Get a specific KCS solution
rhapi get-kcs 1234567

# Table output instead of JSON
rhapi search-cases --months 3 -o table
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

**Returns:** Detailed case information with summary, description, severity, and comments


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

### Prompt Templates

The server includes sophisticated prompt templates for case analysis:

- **Case Summary**: Generates C.A.S.E. format summaries
- **Case Resolution**: Provides investigation workflows
- **Multi-phase Analysis**: Advanced case resolution protocols

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