from jira_client import fetch_bugs
from excel_exporter import export_bugs_to_excel

def main():
    print("Fetching Jira bugs...")
    issues = fetch_bugs()
    print(f"Fetched {len(issues)} bugs")

    print("Exporting to Excel...")
    export_bugs_to_excel(issues)

    print("Excel file created: jira_bugs.xlsx ✅")

if __name__ == "__main__":
    main()
