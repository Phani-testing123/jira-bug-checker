import json
import os
from datetime import datetime
from jira_client import fetch_bugs
from excel_exporter import adf_to_text
from slack_client import get_user_id_by_email, send_dm

NOTIFIED_FILE = "notified.json"

# ─────────────────────────────────────────────
# Helper: Extract Jira Fields Consistently
# ─────────────────────────────────────────────
def _extract_issue_details(issue):
    """
    Internal helper to parse fields consistently across all functions.
    Ensures that logic for 'Missing' fields is synchronized.
    """
    fields = issue.get("fields", {})
    
    # 1. Environment
    env = adf_to_text(fields.get("environment"))
    
    # 2. Priority
    prio_obj = fields.get("priority")
    prio = prio_obj.get("name") if prio_obj and prio_obj.get("name") != "None" else None
    
    # 3. Severity (Checks custom field or direct attribute)
    sev_field = fields.get("customfield_11010")
    sev = sev_field.get("value") if isinstance(sev_field, dict) else issue.get("severity")

    # Determine which are missing
    missing = []
    if not env: missing.append("Environment")
    if not prio: missing.append("Priority")
    if not sev: missing.append("Severity")

    return {
        "env": env,
        "prio": prio,
        "sev": sev,
        "missing_fields": missing,
        "reporter_email": fields.get("reporter", {}).get("emailAddress"),
        "reporter_name": fields.get("reporter", {}).get("displayName", "there")
    }

# ─────────────────────────────────────────────
# Notified tracking
# ─────────────────────────────────────────────
def load_notified():
    if not os.path.exists(NOTIFIED_FILE):
        return {}

    try:
        with open(NOTIFIED_FILE, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

    # 🔄 Backward compatibility
    if isinstance(data, list):
        return {k: {"status": "sent", "last_sent": None} for k in data}

    return data

def save_notified(notified):
    with open(NOTIFIED_FILE, "w") as f:
        json.dump(notified, f, indent=2)

def get_notification_status(issue_key):
    notified = load_notified()
    info = notified.get(issue_key)
    return info.get("status", "sent") if info else "not_notified"

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
        details = _extract_issue_details(issue)
        
        if details["missing_fields"]:
            for field in details["missing_fields"]:
                stats[field.lower()] += 1
            results.append(issue)

    return results, stats

# ─────────────────────────────────────────────
# Slack notification (INITIAL + REMINDER)
# ─────────────────────────────────────────────
def trigger_slack(issues, dry_run=True, force=False, message_type="initial"):
    """
    dry_run=True   → preview only (NO Slack, NO dedupe)
    force=True     → resend even if already notified
    message_type: 'initial' or 'reminder'
    """
    notified = load_notified()
    sent_keys = []

    for issue in issues:
        issue_key = issue.get("key")
        
        # 🔒 DEDUPE: Skip if already notified (unless force or dry_run)
        if not dry_run and not force and issue_key in notified:
            continue

        details = _extract_issue_details(issue)
        
        # Skip if no email found or if the bug is actually complete
        if not details["reporter_email"] or not details["missing_fields"]:
            continue

        # ── DRY RUN LOGIC ─────────────────────
        if dry_run: 
            if issue_key not in notified:
                sent_keys.append(issue_key)
            continue

        # ── REAL SEND LOGIC ───────────────────
        user_id = get_user_id_by_email(details["reporter_email"])
        if not user_id:
            continue

        jira_url = f"https://rbictg.atlassian.net/browse/{issue_key}"

        # Polite & Professional Messaging
        if message_type == "reminder":
            status = "reminder"
            message = (
                f"👋 *Quick follow-up regarding {issue_key}*\n"
                f"Hi {details['reporter_name']}, hope you're having a good day. "
                f"Just a gentle reminder that some details are still needed for your bug report: *<{jira_url}|{issue_key}>*.\n\n"
                f"*Pending items:*\n"
                + "\n".join(f"• _{f}_" for f in details["missing_fields"]) +
                "\n\nProviding these details helps team investigate and resolve the issue faster. "
                "Thank you for your help! 🙏"
            )
        else:
            status = "sent"
            message = (
                f"👋 *Hi {details['reporter_name']}, thanks for reporting {issue_key}!* \n"
                f"To help team triage and address this bug effectively, we noticed a few fields were left empty: *<{jira_url}|{issue_key}>*.\n\n"
                f"*Required details:*\n"
                + "\n".join(f"• _{f}_" for f in details["missing_fields"]) +
                "\n\nCould you please take a moment to add these whenever you have a chance? "
                "We appreciate your contribution to the project quality! ✨"
            )

        # Send the message
        send_dm(user_id, message)

        # Update tracking state
        notified[issue_key] = {
            "status": status,
            "last_sent": datetime.utcnow().isoformat()
        }
        sent_keys.append(issue_key)

    # Save tracking file ONLY after real sends
    if not dry_run:
        save_notified(notified)

    return sent_keys