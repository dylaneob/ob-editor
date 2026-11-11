#!/usr/bin/env python3
"""
yt_auth.py — one-time Google OAuth for YouTube Analytics (your own channel data).

You do this ONCE. It opens your browser, you approve, and a refresh token is stored
locally so the tool can pull your retention curves forever without asking again.

Prereqs (one-time):
  pip3 install --user google-auth-oauthlib google-api-python-client
  Put your downloaded OAuth client file at ~/ob-moments/.secrets/client_secret.json
    (Google Cloud console → APIs & Services → Credentials → OAuth client ID → Desktop app)

Run:  python3 bin/yt_auth.py   → browser opens, you click Allow, done.

Scopes: yt-analytics.readonly is the one that matters (retention). youtube.readonly
is included so the tool can also read your video list / comments if wanted.
"""
import os, sys

SEC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".secrets")
CLIENT = os.path.join(SEC, "client_secret.json")
TOKEN = os.path.join(SEC, "token.json")
SCOPES = [
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def get_creds():
    """Return valid credentials, refreshing or running the browser flow as needed."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    creds = None
    if os.path.exists(TOKEN):
        creds = Credentials.from_authorized_user_file(TOKEN, SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        from google_auth_oauthlib.flow import InstalledAppFlow
        if not os.path.exists(CLIENT):
            sys.exit(f"Missing {CLIENT}\nDownload your OAuth 'Desktop app' client JSON "
                     f"from Google Cloud console and save it there.")
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT, SCOPES)
        creds = flow.run_local_server(port=0, prompt="consent")
    os.makedirs(SEC, exist_ok=True)
    with open(TOKEN, "w") as f:
        f.write(creds.to_json())
    return creds


if __name__ == "__main__":
    try:
        get_creds()
    except ImportError:
        sys.exit("Missing libs. Run:\n  pip3 install --user google-auth-oauthlib "
                 "google-api-python-client")
    print(f"✓ Authorized. Token saved to {TOKEN}. You won't need to do this again.")
