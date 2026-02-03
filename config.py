import os

# ─────────────────────────────────────────────
# Jira Configuration (PROD SAFE)
# Values come from Environment Variables
# ─────────────────────────────────────────────

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_TOKEN = os.getenv("JIRA_API_TOKEN")

# Default JQL (can be overridden from UI)
JIRA_JQL = os.getenv(
    "JIRA_JQL",
    'project = BKPE AND issuetype = Bug '
    'AND created >= startOfDay(-7d) '
    'AND ('
    '"Environment[Checkboxes]" IS EMPTY '
    'OR priority IS EMPTY '
    'OR "Severity" IS EMPTY'
    ') '
    'ORDER BY created DESC'
)

MAX_RESULTS = int(os.getenv("MAX_RESULTS", 100))
