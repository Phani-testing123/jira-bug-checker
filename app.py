import sys
import os
from datetime import datetime

# 🔧 Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, request, send_file
from services import get_bugs, preview_missing_fields, trigger_slack
from excel_exporter import export_bugs_to_excel, adf_to_text

app = Flask(__name__)

# 🔹 Default JQL
DEFAULT_JQL = (
    'project = BKPE AND issuetype = Bug '
    'AND created >= startOfDay(-7d) '
    'AND ('
    '"Environment[Checkboxes]" IS EMPTY '
    'OR priority IS EMPTY '
    'OR "Severity" IS EMPTY'
    ') '
    'ORDER BY created DESC'
)


cached_bugs = []


@app.route("/", methods=["GET", "POST"])
def index():
    global cached_bugs

    jql = request.form.get("jql", DEFAULT_JQL)
    action = request.form.get("action")
    result_message = None

    # ---------------- FETCH ----------------
    if action == "fetch":
        cached_bugs = get_bugs(jql)

        for bug in cached_bugs:
            fields = bug.get("fields", {})

            # Severity
            severity_field = fields.get("customfield_11010")
            bug["severity"] = (
                severity_field.get("value")
                if isinstance(severity_field, dict)
                else None
            )

            # Environment
            bug["environment"] = adf_to_text(fields.get("environment"))

            # Priority fix
            priority_obj = fields.get("priority")
            if isinstance(priority_obj, dict) and priority_obj.get("name") == "None":
                fields["priority"] = None

        missing, stats = preview_missing_fields(cached_bugs)

        parts = []
        if stats["environment"]:
            parts.append(f'Environment ({stats["environment"]})')
        if stats["priority"]:
            parts.append(f'Priority ({stats["priority"]})')
        if stats["severity"]:
            parts.append(f'Severity ({stats["severity"]})')

        result_message = (
            f"Fetched {len(missing)} bug(s) missing: {', '.join(parts)}"
            if parts else
            "Fetched bugs with no missing fields"
        )

    # ---------------- SLACK DRY RUN (NO SEND) ----------------
    elif action == "slack_preview":
        # ✅ dry_run=True → NO Slack messages
        sent = trigger_slack(cached_bugs, dry_run=True)
        result_message = (
            f"Slack Dry-Run: {len(sent)} bug(s) would be notified → {', '.join(sent)}"
            if sent else
            "Slack Dry-Run: No bugs to notify"
        )

    # ---------------- SLACK SEND (ALL, ONCE) ----------------
    elif action == "slack_send":
        sent = trigger_slack(cached_bugs, dry_run=False)
        result_message = (
            f"Slack Sent: {len(sent)} bug(s) → {', '.join(sent)}"
            if sent else
            "Slack Sent: No new bugs (already notified)"
        )

    # ---------------- SLACK RE-SEND (SELECTED ONLY) ----------------
    elif action == "slack_resend":
        selected_keys = request.form.getlist("selected_keys")

        if not selected_keys:
            result_message = "⚠️ No bugs selected for re-send"
        else:
            selected_bugs = [
                bug for bug in cached_bugs
                if bug.get("key") in selected_keys
            ]

            # ✅ force=True bypasses dedupe
            sent = trigger_slack(selected_bugs, dry_run=False, force=True)
            result_message = (
                f"Re-Sent Slack: {len(sent)} bug(s) → {', '.join(sent)}"
                if sent else
                "No Slack messages sent"
            )

    # ---------------- EXCEL EXPORT ----------------
    elif action == "export":
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"jira_bugs_{timestamp}.xlsx"
        file_path = os.path.join("/tmp", file_name)

        export_bugs_to_excel(cached_bugs, file_path)

        return send_file(
            file_path,
            as_attachment=True,
            download_name=file_name
        )

    return render_template(
        "index.html",
        bugs=cached_bugs,
        jql=jql,
        result_message=result_message
    )


if __name__ == "__main__":
    app.run(debug=False)
