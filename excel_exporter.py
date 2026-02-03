from openpyxl import Workbook


def adf_to_text(adf):
    """
    Converts Jira ADF (Atlassian Document Format) to plain text
    """
    if not adf or not isinstance(adf, dict):
        return ""

    texts = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("type") == "text":
                texts.append(node.get("text", ""))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(adf)
    return " ".join(texts).strip()


def export_bugs_to_excel(issues, file_name="jira_bugs.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.title = "Jira Bugs"

    # Header row
    ws.append([
        "Issue Key",
        "Summary",
        "Status",
        "Priority",
        "Severity",
        "Environment",
        "Reporter",
        "Created Date",
        "Attachments Count"
    ])

    for issue in issues:
        fields = issue.get("fields", {})

        issue_key = issue.get("key")
        summary = fields.get("summary")
        status = fields.get("status", {}).get("name")

        # ✅ Priority FIX: treat "None" as missing
        priority_obj = fields.get("priority")
        priority = (
            priority_obj.get("name")
            if priority_obj and priority_obj.get("name") != "None"
            else ""
        )

        # ✅ Severity FIX: correct custom field
        severity_field = fields.get("customfield_11010")
        severity = (
            severity_field.get("value")
            if isinstance(severity_field, dict)
            else ""
        )

        created = fields.get("created")
        attachments_count = len(fields.get("attachment", []))

        reporter = fields.get("reporter", {})
        reporter_name = reporter.get("displayName", "")

        # Environment (ADF → text)
        environment = adf_to_text(fields.get("environment"))

        # Optional preview log (SAFE)
        if not environment:
            print(f"[PREVIEW] Missing Environment → {issue_key} | {reporter_name}")

        # 📊 Excel row
        ws.append([
            issue_key,
            summary,
            status,
            priority,
            severity,
            environment,
            reporter_name,
            created,
            attachments_count
        ])

    wb.save(file_name)
    print(f"Excel file created: {file_name}")
