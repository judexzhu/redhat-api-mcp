#!/usr/bin/env python3
"""Red Hat API MCP Server — FastMCP setup and tool registration."""

from mcp.server.fastmcp import FastMCP

from redhat_api_mcp import tools

mcp = FastMCP("RedHat API", description="Interact with Red Hat KCS and Case APIs", version="1.0.0")

mcp.tool()(tools.search_kcs)
mcp.tool()(tools.get_kcs)
mcp.tool()(tools.search_docs)
mcp.tool()(tools.get_doc)
mcp.tool()(tools.search_cases)
mcp.tool()(tools.get_case)
mcp.tool()(tools.add_comment)
mcp.tool()(tools.search_cve)
mcp.tool()(tools.get_cve)
mcp.tool()(tools.search_errata)
mcp.tool()(tools.get_errata)
mcp.tool()(tools.list_attachments)
mcp.tool()(tools.get_attachment)
mcp.tool()(tools.list_operator_bundles)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
