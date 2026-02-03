def check_bug_quality(data):
    missing = []

    description = data.get("description", "") or ""
    environment = data.get("environment", "")
    attachments = int(data.get("attachments", 0))

    if not environment:
        missing.append("Environment not specified")

    if "Steps" not in description:
        missing.append("Steps to Reproduce missing")

    if "Expected" not in description:
        missing.append("Expected Result missing")

    if "Actual" not in description:
        missing.append("Actual Result missing")

    if attachments == 0:
        missing.append("No screenshots or logs attached")

    return {"missing": missing}
