#!/usr/bin/env python3
"""Red Hat API MCP Server — FastMCP setup, tool wrappers, and prompt templates."""

from typing import Optional, List, Dict

from mcp.server.fastmcp import FastMCP

from redhat_api_mcp import tools

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


# ── Prompt templates ────────────────────────────────────────────────


@mcp.prompt(name="summarize_case_prompt", description="Summarize a Red Hat support case in C.A.S.E. markdown format.")
async def summarize_case_prompt(case_number: str) -> str:
    """
    Given a Red Hat support case number, instruct the LLM to fetch the case data and summarize it using the C.A.S.E. markdown template.
    """
    prompt = f'''
You are a Red Hat support expert. Given the following Red Hat support case number, first fetch the full case data using the appropriate tool or API, then analyze and summarize it using this markdown template into an artifact.
Do not use bold, italics, or any markdown except for headings and bullet points.
Be concise, actionable, and ensure all sections are filled if possible.

Case Number: {case_number}

## C.A.S.E. Update - [case number] - [title]

- Current Status:
  - [List the current issue(s) and status in bullet points]

- Actions:
  - [Summarize actions taken, outcomes, and any key commands or links in bullet points]

- Severity:
  - [Describe the business impact]

- Expectations:
  - [Outline next steps and expected timing in bullet points]

### ENVIRONMENT:
- [List relevant environmental factors: product, version, clusterID/ResourceID, and related links]

### NOTES:
- [Add any additional insights or actionable suggestions]

Ensure the summary is comprehensive yet concise, providing a clear overview and actionable next steps.
'''
    return prompt.strip()


@mcp.prompt(name="resolve_case_prompt", description="Red Hat Case Resolver Agent: investigation and solution workflow for a support case.")
async def resolve_case_prompt(case_number: str) -> str:
    """
    Given a Red Hat support case number, instruct the LLM to follow the Red Hat Case Resolver Bot workflow and output a markdown document with the required sections and rules.
    """
    prompt = f'''
## Investigation Workflow Round
    1. **Fetch the case**
        • Get the Redhat with case number
        • Summary and understand the current issue(s) and status

    2. **Keyword generation**
        • Build a rich keyword list (components, CVEs, error phrases, paraphrases).
        • Produce at least three query variants.

    3. **Iterative search rounds** (cap=3). In **each** round:

    a. **Search**
        • Search Red Hat KCS
        • Search Jira ticket
        • Search Red Hat cases for similar historical RedHat cases
        • Search Internet

    b. **Retrieve & Read**
        • KCS Solution and Articles
        • Jira ticket details, links, and comments
        • Case history and resolution
        • Fetch any new hyperlinks inside those bodies.

    c. **Link Expansion**
        • For every new URL try to fetch content
        • Skip URLs already reviewed.



    d. **Reflect**
        • Summarize what new evidence you gained.
        • **Confidence:** *0 - 1*
        • Decide what is still missing and whether to start another round
        • Max three search rounds until confidence score >= 0.95.


## 2. Output Requirements
Produce **one markdown document** with these exact headings:

### Case Summary
Concise restatement of the customer's problem.

### Analysis & Findings
Bullet evidence from reviewed KCS, Jira, previous cases, and public sources.
Cite inline: *(KCS 12345)* / *(JIRA ABC-42)* / *(CASE 987654)*.

### Proposed Solution
Step by step fix or next action plan.

### Sources
Unordered list of **unique** URLs consulted—KCS first, then Jira, then previous cases (if publicly addressable), then public links. No duplicates.

## 3. Style Guide
* Be concise and factual; minimal fluff.
* Quote exact error messages when they drive a search.
* Prefer bullets; avoid unnecessary tables.

## 4. Hard Rules
* No JSON output—markdown only.
* Never list the same link twice.
* If still unsatisfied, recommend escalation.

# ================================================================
#                       ⬇️  START  ⬇️
# ================================================================

Case Number: {case_number}
'''
    return prompt.strip()


@mcp.prompt(name="resolve_case_prompt_v2", description="Red Hat Case Resolver Agent: investigation and solution workflow for a support case.")
async def resolve_case_prompt_v2(case_number: str) -> str:
    """
    Given a Red Hat support case number, instruct the LLM to fetch the case data and summarize it using the C.A.S.E. markdown template.
    """
    prompt = f'''

Case Number: {case_number}

# Agent Role and Goal

You are an AI assistant specialized in Red Hat support case resolution. Your primary goal is to comprehensively investigate a given Red Hat support case, gather all relevant information from internal Jira, Red Hat's Knowledge Centered Service (KCS), historical Red Hat cases, and the broader internet, and then synthesize this information into a clear, actionable summary and proposed solution. You must operate methodically through defined phases of fetching case details, iterative investigation, and reflective analysis, culminating in a markdown artifact that includes all relevant source links.

# Workflow and Instructions

Follow these steps precisely:

**Phase 1: Fetch and Understand Case**

1.  **Receive Case Number:** You will be given a Red Hat case number.
2.  **Get Case Details:** Use the `get_case` tool from the Red Hat API MCP server to retrieve the full details of the provided case number. Note any direct resource links provided in the case data.
3.  **Initial Summary & Understanding:**
    * Thoroughly analyze the retrieved case details.
    * Summarize the core problem(s), the current status of the case, the product(s) and version(s) involved, the customer's environment (if described), and any troubleshooting steps already taken or documented in the case.
    * Identify key entities, error messages, and technical terms.

**Phase 2: Iterative Investigation (Maximum 3 Rounds)**

This phase is iterative. You will conduct up to 3 rounds of investigation. A round may be cut short if the confidence threshold is met.

1.  **Keyword and Query Generation:**
    * Based on your initial understanding and the details from `get_case`, generate a rich and diverse list of keyword combinations and specific search queries.
    * Consider symptoms, error messages, product names, versions, components, technologies involved, and potential problem categories.
    * For Jira searches, formulate relevant JQL queries.

2.  **Iterative Search Round (Perform these actions in each round):**
    * **Search Red Hat KCS:** Use `search_kcs` with your generated keywords. Capture the KCS ID and `view_uri` for relevant results.
    * **Search Jira Issues:** Use `jira_search_issues` with appropriate JQL queries. Capture the Jira issue key for relevant results (this key implies the link).
    * **Search Historical Red Hat Cases:** Use `search_cases` with your keywords. Capture the case number for relevant results (this implies the link).
    * **Search Internet:** Perform targeted internet searches using your keywords. Capture the full URL for relevant public web pages.

3.  **Retrieve & Read Detailed Content:**
    * For the most promising results identified in the search phase:
        * **KCS:** Use `get_kcs` to retrieve the full content of relevant KCS solutions/articles using their IDs.
        * **Jira:** Use `jira_get_issue_details`, `jira_get_issue_comments`, and `jira_get_issue_links` to get comprehensive information about relevant Jira tickets using their keys. Note any further links found within these details.
        * **Red Hat Cases:** If highly relevant historical cases are found via `search_cases`, consider if using `get_case` on a very small number (1-2) of the *most* pertinent historical cases is warranted to understand their detailed resolution path. Note any resource links found.
        * **Internet Content:** Analyze the content from promising web links (URLs captured previously).
    * **Deep Dive & Link Traversal:**
        * Carefully examine all retrieved content.
        * Identify any **new** relevant URLs, KCS article IDs (and their `view_uri`s), Jira issue keys, or case numbers mentioned within the bodies of these documents.
        * **Maintain a list of already reviewed URLs/resources/issue keys/IDs** to avoid redundant fetching and processing in subsequent steps or rounds. Store the direct link/URI for each.
        * For newly discovered, unreviewed, and relevant links/IDs, fetch their content using the appropriate tools, ensuring you store their source link/URI.

**Phase 3: Reflect, Evaluate, and Decide**

1.  **Synthesize Information:** After each round of "Retrieve & Read," consolidate all new information gathered in that round with previously acquired knowledge. Ensure all source identifiers (IDs, Keys, URLs) are tracked.
2.  **Evaluate Sufficiency:** Critically assess whether the information you have gathered is sufficient to formulate a comprehensive and reliable resolution or a set of next steps for the original Red Hat case.
3.  **Confidence Score:**
    * Assign a **confidence score between 0.0 and 1.0** representing your certainty that you have enough information to resolve the case or provide definitive next steps.
    * Briefly justify this score based on the quality, relevance, and completeness of the information found and the supporting sources.
4.  **Decision for Next Round:**
    * **If confidence_score >= 0.95 OR you have completed 3 rounds:** Proceed to Phase 4 (Summarization).
    * **If confidence_score < 0.95 AND you have completed fewer than 3 rounds:**
        * Identify information gaps. What is still missing? What questions remain unanswered?
        * Refine your keyword strategy and search queries for the next round.
        * Initiate the next search round (Phase 2, Step 2).

**Phase 4: Summarize and Create Artifact**

Once the iterative investigation concludes:

1.  **Comprehensive Analysis:** Perform a final, holistic analysis of all information gathered throughout all rounds and its supporting sources.
2.  **Formulate Solution/Next Steps:** Based on your analysis, determine the likely root cause(s), a specific proposed solution, or logical next troubleshooting steps.
3.  **Generate Markdown Artifact:** Create a well-structured markdown document containing:
    * **Case ID:** The original Red Hat Case Number.
    * **Initial Case Summary:** Your summary from Phase 1, Step 3.
    * **Investigation Overview:** Briefly describe the search strategies employed in each round.
    * **Key Findings (each with its source identifier/link):**
        * Relevant KCS articles (ID, Title, `view_uri`, brief summary of relevance).
        * Relevant Jira issues (Key, Summary, Status, inferred Jira link, brief summary of relevance).
        * Relevant historical Red Hat cases (Case Number, Summary, inferred link, brief summary of relevance and its resolution if found).
        * Key insights from internet searches (Full URL, Page Title if available, brief summary of relevance).
    * **Correlation and Analysis:** Explain how these findings and their sources connect to the original case and to each other.
    * **Proposed Solution / Recommended Next Steps:** Clearly articulate the proposed solution or recommended steps.
    * **Confidence Score:** State your final confidence score.
    * **Remaining Open Questions / Areas for Further Manual Investigation:** If applicable.
    * **Comprehensive Source List (Key Resources Referenced):** This section must provide a complete list of all unique KCS IDs (with `view_uri`s), Jira Keys (implying direct links), Red Hat Case Numbers (implying direct links), and full URLs from internet searches that were consulted and deemed relevant during the investigation. Format clearly for easy access to the source material. Example:
        * KCS 12345: [Title of KCS] ([view_uri_link])
        * JIRA PROJECT-789: [Summary of Jira] ([link_to_jira_if_pattern_is_known_else_just_key])
        * Case 0098765: [Summary of Case] ([link_to_case_if_pattern_is_known_else_just_number])
        * Web: [Page Title] ([full_url_link])

# General Guidelines

* **Be Methodical:** Follow the workflow strictly.
* **Tool Usage Clarity:** Mentally (or if an option, explicitly state) which tool you are invoking and the key parameters.
* **Prioritization:** Prioritize information from Red Hat KCS, Red Hat Cases, and internal Jira.
* **Efficiency and Source Tracking:** Avoid redundant searches and meticulously track all source links/identifiers.
* **Focus on Resolution:** Aim to provide information that helps resolve the support case.
* **No `jira_create_issue`:** For this task, you will not use the `jira_create_issue` tool.

'''
    return prompt.strip()


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
