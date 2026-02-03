import os
import requests

# ✅ Read from ENV (PROD safe)
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_TOKEN = os.getenv("JIRA_TOKEN")

# Optional defaults
DEFAULT_JQL = os.getenv("JIRA_JQL", "")
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "100"))


def fetch_bugs(jql=None):
    """
    Fetch Jira issues using Jira Cloud REST API v3

    - Uses ENV credentials (required for PROD)
    - Uses UI-provided JQL if passed
    """

    final_jql = jql if jql else DEFAULT_JQL

    if not JIRA_BASE_URL or not JIRA_EMAIL or not JIRA_TOKEN:
        raise Exception(
            "❌ Jira credentials missing. "
            "Ensure JIRA_BASE_URL, JIRA_EMAIL, JIRA_TOKEN are set."
        )

    # ✅ CORRECT Jira endpoint
    url = f"{JIRA_BASE_URL}/rest/api/3/search/jql"

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    payload = {
        "jql": final_jql,
        "maxResults": MAX_RESULTS,
        "fields": [
            "summary",
            "status",
            "priority",
            "environment",
            "reporter",
            "created",
            "attachment",
            "customfield_11010"  # Severity
        ]
    }

    print("──────────────── Jira API Call ────────────────")
    print("JIRA BASE URL:", JIRA_BASE_URL)
    print("JIRA USER:", JIRA_EMAIL)
    print("JQL USED:", final_jql)

    response = requests.post(
        url,
        headers=headers,
        auth=(JIRA_EMAIL, JIRA_TOKEN),
        json=payload,
        timeout=30
    )

    print("Status Code:", response.status_code)

    if response.status_code != 200:
        print("❌ Jira API Error Response:", response.text)
        raise Exception(
            f"Jira API failed: {response.status_code}\n{response.text}"
        )

    data = response.json()
    issues = data.get("issues", [])

    print("TOTAL BUGS FROM JIRA:", len(issues))
    print("──────────────────────────────────────────────")

    return issues
