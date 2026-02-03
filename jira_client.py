import requests
from config import JIRA_BASE_URL, JIRA_EMAIL, JIRA_TOKEN, JIRA_JQL, MAX_RESULTS


def fetch_bugs(jql=None):
    """
    Fetch Jira bugs.
    - If jql is provided → use it (UI mode)
    - Else → use JIRA_JQL from config (CLI / cron mode)
    """

    final_jql = jql if jql else JIRA_JQL

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
            "customfield_11010"  # ✅ Severity field (replace ID if different)
        ]
    }

    response = requests.post(
        url,
        headers=headers,
        auth=(JIRA_EMAIL, JIRA_TOKEN),
        json=payload
    )

    print("Status Code:", response.status_code)

    if response.status_code != 200:
        raise Exception(
            f"Jira API failed: {response.status_code}\n{response.text}"
        )

    return response.json().get("issues", [])
