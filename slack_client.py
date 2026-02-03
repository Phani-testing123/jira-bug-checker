import os
import requests

SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_API = "https://slack.com/api"

def get_user_id_by_email(email):
    response = requests.get(
        f"{SLACK_API}/users.lookupByEmail",
        headers={
            "Authorization": f"Bearer {SLACK_TOKEN}"
        },
        params={"email": email}
    )

    data = response.json()
    if not data.get("ok"):
        return None

    return data["user"]["id"]

def send_dm(user_id, message):
    response = requests.post(
        f"{SLACK_API}/chat.postMessage",
        headers={
            "Authorization": f"Bearer {SLACK_TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "channel": user_id,
            "text": message
        }
    )

    return response.json()
