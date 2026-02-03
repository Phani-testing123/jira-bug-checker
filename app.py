import sys
import os
from datetime import datetime

# 🔧 Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, send_file
from services import (
    get_bugs,
    preview_missing_fields,
    trigger_slack,
    load_notified          # ✅ CORRECT SOURCE
)
from excel_exporter import export_bugs_to_excel, adf_to_text

app = Flask(__name__)

# 🔹 Default JQL (last 7 days)
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

# Cache between actions
cached_bugs = []


@app.route("/", methods=["GET", "POST"])
def index():
    global cached_bugs

    jql = request.form.get("jql", DEFAULT_JQL)
    action = request.form.get("action")
    result_message = None

    # ───────────── DEBUG (SAFE) ─────────────
    print("ACTION:", action)
    print("JQL USED:", jql)
    # ───────────────────────────────────────

    # ───────────────── FETCH ─────────────────
    if action == "fetch":
        all_bugs = get_bugs(jql)
        print("TOTAL BUGS FROM JIRA:", len(all_bugs))

        # 🔔 Load notification map ONCE
        notified_map = load_notified()

        for bug in all_bugs:
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

            # Priority fix (Jira returns name="None")
            priority_obj = fields.get("priority")
            if isinstance(priority_obj, dict) and priority_obj.get("name") == "None":
                fields["priority"] = None

            # ✅ Notification status for UI
            key = bug.get("key")
            notify_info = notified_map.get(key)

            if notify_info:
                bug["notify_status"] = notify_info.get("status")        # sent / reminder
                bug["last_notified"] = notify_info.get("last_sent")
            else:
                bug["notify_status"] = None
                bug["last_notified"] = None

        # Filter only missing-field bugs
        missing_bugs, stats = preview_missing_fields(all_bugs)

        print("MISSING BUGS COUNT:", len(missing_bugs))
        print("MISSING STATS:", stats)

        if missing_bugs:
            cached_bugs = missing_bugs
            result_message = (
                f"Fetched {len(missing_bugs)} bug(s) missing: "
                f"Env({stats['environment']}), "
                f"Priority({stats['priority']}), "
                f"Severity({stats['severity']})"
            )
        else:
            cached_bugs = []
            result_message = "🎉 No bugs with missing fields found"

    # ───────────────── SLACK DRY-RUN ─────────────────
    elif action == "slack_preview":
        sent = trigger_slack(cached_bugs, dry_run=True)
        result_message = (
            f"Slack Dry-Run: {len(sent)} bug(s) would be notified"
            if sent else
            "Slack Dry-Run: No bugs to notify"
        )

    # ───────────────── SLACK SEND (ALL) ─────────────────
    elif action == "slack_send":
        sent = trigger_slack(cached_bugs, dry_run=False)
        result_message = (
            f"Slack Sent: {len(sent)} bug(s)"
            if sent else
            "Slack Sent: No new bugs (already notified)"
        )

    # ───────────────── SLACK RE-SEND (SELECTED) ─────────────────
    elif action == "slack_resend":
        selected_keys = request.form.getlist("selected_keys")
        print("SELECTED KEYS:", selected_keys)

        if not selected_keys:
            result_message = "⚠️ No bugs selected for re-send"
        else:
            selected_bugs = [
                bug for bug in cached_bugs
                if bug.get("key") in selected_keys
            ]

            sent = trigger_slack(
                selected_bugs,
                dry_run=False,
                force=True,
                message_type="reminder"   # ✅ REMINDER MESSAGE
            )

            result_message = (
                f"Reminder sent to {len(sent)} bug(s)"
                if sent else
                "No reminders sent"
            )

    # ───────────────── EXCEL EXPORT ─────────────────
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
    # 🔒 PROD SAFE
    app.run(debug=False)
