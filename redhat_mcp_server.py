#!/usr/bin/env python3
"""
Red Hat API MCP Server

This MCP server implements tools to interact with Red Hat APIs:
1. Search Red Hat KCS Solutions
2. Get a Solution by ID
3. Search Red Hat Cases
4. Get Case details

The server uses the Model Context Protocol (MCP) to expose these tools to LLM applications.
"""

import os
import json
from typing import Optional, List, Dict, Any, Union
import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP, Context
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

# Create MCP server
mcp = FastMCP("RedHat API", description="Interact with Red Hat KCS and Case APIs", version="1.0.0")

# Configuration
class RedHatAPI:
    """Red Hat API client with authentication and request handling."""
    
    def __init__(self):
        self.base_url = "https://access.redhat.com"
        self.sso_url = "https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token"
        self.offline_token = os.getenv("RH_API_OFFLINE_TOKEN")
        if not self.offline_token:
            raise ValueError("RH_API_OFFLINE_TOKEN environment variable is required")
        
        self.access_token = None
        self.token_expiry = None
        
    async def get_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary."""
        if self.access_token and self.token_expiry and datetime.now() < self.token_expiry:
            return self.access_token
        
        # Refresh token
        async with httpx.AsyncClient() as client:
            payload = {
                "grant_type": "refresh_token",
                "client_id": "rhsm-api",
                "refresh_token": self.offline_token
            }
            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            response = await client.post(self.sso_url, data=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            self.access_token = data["access_token"]
            # Set expiry time slightly before actual expiry to be safe
            self.token_expiry = datetime.now() + timedelta(seconds=data["expires_in"] - 60)
            
            return self.access_token
    
    async def make_request(self, method: str, path: str, data: Optional[Dict] = None) -> Dict:
        """Make an authenticated request to the Red Hat API."""
        token = await self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}{path}"
        
        async with httpx.AsyncClient() as client:
            if method.lower() == "get":
                response = await client.get(url, headers=headers)
            elif method.lower() == "post":
                response = await client.post(url, json=data, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            
            # Handle both JSON responses and text responses
            if "application/json" in response.headers.get("content-type", ""):
                return response.json()
            return {"content": response.text}

# Initialize API client
rhapi = RedHatAPI()

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
    path = "/hydra/rest/search/v2/kcs"
    
    data = {
        "q": query,
        "rows": rows,
        "expression": "sort=score%20DESC&fq=documentKind%3A(%22Article%22%20OR%20%22Solution%22)%20AND%20accessState%3A(%22active%22%20OR%20%22private%22)&fl=allTitle%2CcaseCount%2CdocumentKind%2C%5Belevated%5D%2ChasPublishedRevision%2Cid%2Clanguage%2ClastModifiedDate%2CModerationState%2Cscore%2Curi%2Cresource_uri%2Cview_uri%2CcreatedDate&showRetired=false",
        "start": start,
        "clientName": "mcp"
    }
    
    result = await rhapi.make_request("post", path, data)
    
    # Format the response to include only relevant information
    solutions = []
    if "response" in result and "docs" in result["response"]:
        for doc in result["response"]["docs"]:
            solution = {
                "id": doc.get("id"),
                "title": doc.get("allTitle"),
                "score": doc.get("score"),
                "view_uri": doc.get("view_uri")
            }
            solutions.append(solution)
    
    return solutions

@mcp.tool()
async def get_kcs(solution_id: str) -> Dict:
    """Get a specific solution by ID and extract structured content

    Args:
        solution_id: The ID of the solution to retrieve

    Returns:
        Dictionary with title, Environment, Issue, Resolution, and Root Cause
    """
    # Use the KCS search API to get the solution data
    path = "/hydra/rest/search/v2/kcs"
    
    data = {
        "q": f"id:{solution_id}",
}
    
    result = await rhapi.make_request("post", path, data)
    
    # Check if we got a result
    if not result or "response" not in result or "docs" not in result["response"] or not result["response"]["docs"]:
        return {
            "title": "",
            "environment": "",
            "issue": "",
            "resolution": "",
            "root_cause": ""
        }
    
    # Extract the solution data from the first document
    doc = result["response"]["docs"][0]
    
    # Initialize the result dictionary
    solution_data = {
        "title": doc.get("publishedTitle", ""),
        "environment": doc.get("standard_product", ""),
        "issue": doc.get("issue", ""),
        "resolution": doc.get("solution_resolution", ""),
        "root_cause": doc.get("solution_rootcause", ""),
    }
    
    return solution_data



@mcp.tool()
async def search_cases(query: str, rows: int = 10, start: int = 0) -> List[Dict]:
    """
    Search for Red Hat cases and return a list of case numbers.
    
    Args:
        query: Search query string
        rows: Number of results to return (default: 10)
        start: Starting index for pagination (default: 0)
        
    Returns:
        List of cases with their numbers and metadata
    """
    path = "/hydra/rest/search/v2/cases"
    
    data = {
        "q": query,
        "start": start,
        "rows": rows,
        "partnerSearch": False,
        "expression": "sort=case_lastModifiedDate%20desc&fl=case_createdByName%2Ccase_createdDate%2Ccase_lastModifiedDate%2Ccase_lastModifiedByName%2Cid%2Curi%2Ccase_summary%2Ccase_status%2Ccase_product%2Ccase_version%2Ccase_accountNumber%2Ccase_number%2Ccase_contactName%2Ccase_owner%2Ccase_severity"
    }
    
    result = await rhapi.make_request("post", path, data)
    
    # Format the response to include only relevant information
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
                "uri": doc.get("uri")
            }
            cases.append(case)
    
    return cases

@mcp.tool()
async def get_case(case_number: str) -> Dict:
    """
    Get case details by case number.
    
    Args:
        case_number: The case number (e.g., "04145487")
        
    Returns:
        Formatted case data with description, severity, issue, case number, and comments
    """
    path = f"/hydra/rest/v1/cases/{case_number}"
    data = await rhapi.make_request("get", path)
    
    # Extract comments from the main response
    comments = data.get("comments", [])
    
    # Format the response according to the specified schema
    formatted_result = {
        "summary": data.get("summary", data.get("title", "")),
        "description": data.get("description"),
        "severity": data.get("severity"),
        "comments": [
            {
                "createdDate": comment.get("createdDate"),
                "createdBy": comment.get("createdBy"),
                "commentBody": comment.get("commentBody", comment.get("text", ""))
            }
            for comment in reversed(comments)
        ]
    }
    
    # Add any additional useful fields from the original response
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
    
    return formatted_result

# Run the server if executed directly
if __name__ == "__main__":
    mcp.run(transport="stdio")
