import os
import requests

SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_API = "https://slack.com/api"

HEADERS = {
    "Authorization": f"Bearer {SLACK_TOKEN}",
    "Content-Type": "application/json"
}

def get_user_id_by_email(email):
    if not SLACK_TOKEN:
        print("❌ SLACK_BOT_TOKEN not set")
        return None

    response = requests.get(
        f"{SLACK_API}/users.lookupByEmail",
        headers=HEADERS,
        params={"email": email},
        timeout=10
    )

    data = response.json()
    if not data.get("ok"):
        print(f"⚠️ Slack lookup failed for {email}: {data.get('error')}")
        return None

    return data["user"]["id"]


def send_dm(user_id, message):
    if not SLACK_TOKEN:
        print("❌ SLACK_BOT_TOKEN not set")
        return None

    response = requests.post(
        f"{SLACK_API}/chat.postMessage",
        headers=HEADERS,
        json={
            "channel": user_id,
            "text": message
        },
        timeout=10
    )

    data = response.json()
    if not data.get("ok"):
        print(f"⚠️ Slack DM failed for {user_id}: {data.get('error')}")

    return data
