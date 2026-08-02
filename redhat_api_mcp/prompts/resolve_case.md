## Investigation Workflow Round
    1. **Fetch the case**
        - Get the Redhat with case number
        - Summary and understand the current issue(s) and status

    2. **Keyword generation**
        - Build a rich keyword list (components, CVEs, error phrases, paraphrases).
        - Produce at least three query variants.

    3. **Iterative search rounds** (cap=3). In **each** round:

    a. **Search**
        - Search Red Hat KCS
        - Search Jira ticket
        - Search Red Hat cases for similar historical RedHat cases
        - Search Internet

    b. **Retrieve & Read**
        - KCS Solution and Articles
        - Jira ticket details, links, and comments
        - Case history and resolution
        - Fetch any new hyperlinks inside those bodies.

    c. **Link Expansion**
        - For every new URL try to fetch content
        - Skip URLs already reviewed.



    d. **Reflect**
        - Summarize what new evidence you gained.
        - **Confidence:** *0 - 1*
        - Decide what is still missing and whether to start another round
        - Max three search rounds until confidence score >= 0.95.


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
#                       START
# ================================================================

Case Number: {case_number}
