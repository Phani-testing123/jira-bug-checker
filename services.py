import json
import os
from jira_client import fetch_bugs
from excel_exporter import adf_to_text
from slack_client import get_user_id_by_email, send_dm

NOTIFIED_FILE = "notified.json"


# ─────────────────────────────────────────────
# Notified tracking (dedupe Slack messages)
# ─────────────────────────────────────────────
def load_notified():
    if not os.path.exists(NOTIFIED_FILE):
        return set()
    with open(NOTIFIED_FILE, "r") as f:
        return set(json.load(f))


def save_notified(notified):
    with open(NOTIFIED_FILE, "w") as f:
        json.dump(list(notified), f)


# ─────────────────────────────────────────────
# Jira fetch
# ─────────────────────────────────────────────
def get_bugs(jql):
    return fetch_bugs(jql)


# ─────────────────────────────────────────────
# Missing field detection
# ─────────────────────────────────────────────
def preview_missing_fields(issues):
    results = []
    stats = {"environment": 0, "priority": 0, "severity": 0}

    for issue in issues:
        fields = issue.get("fields", {})

        environment = adf_to_text(fields.get("environment"))

        priority_obj = fields.get("priority")
        priority = (
            priority_obj
            if priority_obj and priority_obj.get("name") != "None"
            else None
        )

        severity_field = fields.get("customfield_11010")
        severity = (
            severity_field.get("value")
            if isinstance(severity_field, dict)
            else None
        )

        missing_any = False

        if not environment:
            stats["environment"] += 1
            missing_any = True
        if not priority:
            stats["priority"] += 1
            missing_any = True
        if not severity:
            stats["severity"] += 1
            missing_any = True

        if missing_any:
            results.append(issue)

    return results, stats


# ─────────────────────────────────────────────
# Slack notification (ENHANCED, SAFE)
# ─────────────────────────────────────────────
def trigger_slack(issues, dry_run=True, force=False, message_type="initial"):
    """
    dry_run=True   → preview only (NO Slack, NO dedupe)
    force=True     → resend even if already notified
    message_type:
        - "initial"  → first-time message
        - "reminder" → follow-up reminder
    """

    notified = load_notified()
    sent = []

    for issue in issues:
        issue_key = issue.get("key")

        # 🔒 DEDUPE ONLY FOR REAL SEND (NOT dry-run, NOT force)
        if not dry_run and not force and issue_key in notified:
            continue

        fields = issue.get("fields", {})
        reporter = fields.get("reporter", {})
        email = reporter.get("emailAddress")
        name = reporter.get("displayName", "there")

        environment = adf_to_text(fields.get("environment"))

        priority_obj = fields.get("priority")
        priority = (
            priority_obj
            if priority_obj and priority_obj.get("name") != "None"
            else None
        )

        severity_field = fields.get("customfield_11010")
        severity = (
            severity_field.get("value")
            if isinstance(severity_field, dict)
            else None
        )

        missing_fields = []
        if not environment:
            missing_fields.append("Environment")
        if not priority:
            missing_fields.append("Priority")
        if not severity:
            missing_fields.append("Severity")

        if not email or not missing_fields:
            continue

        # ── DRY RUN ───────────────────────────
        if dry_run:
            sent.append(issue_key)
            continue

        # ── REAL SEND ─────────────────────────
        user_id = get_user_id_by_email(email)
        if not user_id:
            continue

        # ✉️ Message selection
        if message_type == "reminder":
            message = (
                f"⏰ Hi {name},\n"
                f"Friendly reminder about Jira bug *{issue_key}* — it’s still missing:\n"
                + "\n".join(f"- {f}" for f in missing_fields) +
                "\n\nPlease update this when you get time 🙏\n"
                "Thanks!"
            )
        else:
            message = (
                f"👋 Hi {name},\n"
                f"Your Jira bug *{issue_key}* is missing required field(s):\n"
                + "\n".join(f"- {f}" for f in missing_fields) +
                "\n\nPlease update it.Thanks🙏"
            )

        send_dm(user_id, message)
        notified.add(issue_key)
        sent.append(issue_key)

    # Save ONLY after real sends
    if not dry_run:
        save_notified(notified)

    return sent
