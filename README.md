# Red Hat API MCP Server

This project implements a [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server that provides tools for interacting with Red Hat APIs, making it easy to integrate with LLM applications.

## Features

The server exposes the following Red Hat API tools:

1. **Search Red Hat KCS Solutions** - Search for knowledge base solutions
2. **Get Solution by ID** - Retrieve full solution content
3. **Search Red Hat Cases** - Find cases matching a query
4. **Get Case Details** - Retrieve detailed information about a specific case

## Prerequisites

- Python 3.8 or higher
- Red Hat API offline token (obtained from your Red Hat account)

## Installation

1. Clone this repository
2. Install dependencies:

```bash
pip install -e .
```

or

```bash
uv add -e .
```

## Configuration

Create a `.env` file in the project root with your Red Hat API token:

```
RH_API_OFFLINE_TOKEN=your_offline_token_here
```

You can obtain an offline token from your Red Hat account settings.

## Usage

### Running the Server

To start the MCP server:

```bash
python redhat_mcp_server.py
```

### Developing with the MCP Inspector

You can test the server using the MCP development tools:

```bash
mcp dev redhat_mcp_server.py
```

This will start the MCP inspector, allowing you to interact with your tools interactively.

### Integrating with Claude Desktop

To install the server in Claude Desktop:

```bash
mcp install redhat_mcp_server.py
```

## Available Tools

### search_kcs

Search for Red Hat KCS Solutions.

```python
search_kcs(query: str, rows: int = 50, start: int = 0) -> List[Dict]
```

### get_kcs

Get a Red Hat solution by its ID.

```python
get_kcs(solution_id: str) -> Dict
```

### search_cases

Search for Red Hat cases.

```python
search_cases(query: str, rows: int = 10, start: int = 0) -> List[Dict]
```

### get_case

Get case details by case number.

```python
get_case(case_number: str) -> Dict
```

## Understanding the 'expression' Parameter for Hydra Solr Index API

When interacting with the Red Hat Hydra Solr index API (used for searching KCS solutions, articles, and cases), you can use the `expression` parameter to fine-tune your search results. This parameter allows you to specify advanced Solr query options, such as filtering, sorting, and selecting fields.

### Common 'expression' Parameters
- **fq**: (Filter Query) Restricts the results to documents matching the filter. Example: `fq=(documentKind: Solution)`
- **fl**: (Field List) Specifies which fields to return in the response. Example: `fl=id,allTitle,documentKind`
- **sort**: Specifies the sort order of results. Example: `sort=score DESC`
- **showRetired**: Whether to include retired documents. Example: `showRetired=false`

### Example Usage

```json
{
  "q": "id:333213*",
  "expression": "fl=id&sort=id asc&fq=(documentKind: Solution)"
}
```

- This will search for documents with IDs starting with `333213`, return only the `id` field, sort results by `id` ascending, and filter to only those with `documentKind: Solution`.

Another example:

```json
{
  "q": "*:*",
  "expression": "fq=(documentKind: Solution) AND solution_resolution:*&fl=id&sort=id asc"
}
```

- This will return all documents of kind `Solution` that also have a `solution_resolution` field, returning only the `id` field, sorted by `id` ascending.

#### Filtering for Multiple Document Kinds (OR)

If you want to match documents where `documentKind` is either `Article` **or** `Solution`, use an OR condition in the `fq` parameter:

```json
{
  "q": "*:*",
  "expression": "fq=(documentKind: Article OR documentKind: Solution)&fl=id,allTitle,documentKind&sort=score DESC"
}
```

- This will return documents where `documentKind` is either `Article` or `Solution`.

URL-encoded, this would look like:

```
fq=(documentKind%3A%20Article%20OR%20documentKind%3A%20Solution)&fl=id%2CallTitle%2CdocumentKind&sort=score%20DESC
```

### Tips
- You can combine multiple filters using `AND`

### KCS Search Expression

By default, the MCP server's `search_kcs` tool returns only documents where `documentKind` is either `Article` or `Solution` **and** `accessState` is either `active` or `private`.

#### Example (Default)

```json
{
  "q": "CVE",
  "expression": "sort=score DESC&fq=documentKind:(\"Article\" OR \"Solution\") AND accessState:(\"active\" OR \"private\")&fl=allTitle,caseCount,documentKind,[elevated],hasPublishedRevision,id,language,lastModifiedDate,ModerationState,score,uri,resource_uri,view_uri,createdDate&showRetired=false"
}
```

- This will return only active/private Articles or Solutions, sorted by relevance, and include the listed fields.

URL-encoded, this would look like:

```
sort=score%20DESC&fq=documentKind%3A(%22Article%22%20OR%20%22Solution%22)%20AND%20accessState%3A(%22active%22%20OR%20%22private%22)&fl=allTitle%2CcaseCount%2CdocumentKind%2C%5Belevated%5D%2ChasPublishedRevision%2Cid%2Clanguage%2ClastModifiedDate%2CModerationState%2Cscore%2Curi%2Cresource_uri%2Cview_uri%2CcreatedDate&showRetired=false
```

### Case Search Expression

When searching for Red Hat support cases, the MCP server uses an expression like this:

```json
{
  "q": "<your search query>",
  "expression": "sort=case_lastModifiedDate desc&fl=case_createdByName,case_createdDate,case_lastModifiedDate,case_lastModifiedByName,id,uri,case_summary,case_status,case_product,case_version,case_accountNumber,case_number,case_contactName,case_owner,case_severity"
}
```

- **sort=case_lastModifiedDate desc**: Sorts results by the most recently modified cases first.
- **fl=...**: Returns only the listed fields for each case, such as summary, status, product, version, owner, severity, etc.

**Plain English:**
> Return cases sorted by most recently modified, and for each case, include only the specified fields (such as summary, status, product, version, owner, severity, etc.).

There is no filter query (`fq`) in this example, so all cases matching your main query will be returned. To filter further (e.g., by status or product), add an `fq=...` parameter.

### How to URL-Encode an Expression String in Python

You can easily encode your query or expression string for use in API calls using Python's standard library:

```python
import urllib.parse

query = 'sort=score DESC&fq=documentKind:("Article" OR "Solution") AND accessState:("active" OR "private")&fl=id,allTitle,documentKind'
encoded = urllib.parse.quote(query, safe='=&,:()[]')
print(encoded)
```

- The `safe` parameter keeps certain characters (like `=`, `&`, `,`, `:`, `(`, `)`, `[`, `]`) unencoded for readability and compatibility with Solr queries.
- The output will be a URL-encoded string you can use in your API requests.

#### Command-Line One-Liner

To URL-encode your query string directly from the command line, use:

```sh
python3 -c "import urllib.parse; print(urllib.parse.quote('sort=score DESC&fq=documentKind:(\"Article\" OR \"Solution\") AND accessState:(\"active\" OR \"private\")&fl=id,allTitle,documentKind', safe='=&,:()[]'))"
```

- This will print the URL-encoded string to your terminal, ready to use in API requests.