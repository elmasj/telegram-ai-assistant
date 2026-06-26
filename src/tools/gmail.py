import os
import base64
import json
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

_service = None


def is_authorized() -> bool:
    """Check if Gmail token exists without triggering auth flow."""
    token_path = os.environ.get("GMAIL_TOKEN_PATH", "data/gmail_token.json")
    return os.path.exists(token_path)


def get_service():
    global _service
    if _service:
        return _service

    creds = None
    token_path = os.environ.get("GMAIL_TOKEN_PATH", "data/gmail_token.json")
    creds_path = os.environ.get("GMAIL_CREDENTIALS_PATH", "credentials.json")

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    _service = build("gmail", "v1", credentials=creds)
    return _service


def list_emails(max_results: int = 10, query: str = "in:inbox") -> list[dict]:
    """List emails from Gmail matching a query."""
    svc = get_service()
    result = svc.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
    messages = result.get("messages", [])
    emails = []
    for msg in messages:
        detail = svc.users().messages().get(userId="me", id=msg["id"], format="metadata",
                                            metadataHeaders=["From", "Subject", "Date"]).execute()
        headers = {h["name"]: h["value"] for h in detail["payload"]["headers"]}
        emails.append({
            "id": msg["id"],
            "from": headers.get("From", ""),
            "subject": headers.get("Subject", ""),
            "date": headers.get("Date", ""),
            "snippet": detail.get("snippet", ""),
        })
    return emails


def read_email(message_id: str) -> dict:
    """Read the full content of a specific email by ID."""
    svc = get_service()
    msg = svc.users().messages().get(userId="me", id=message_id, format="full").execute()
    headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}

    body = ""
    payload = msg["payload"]
    if "parts" in payload:
        for part in payload["parts"]:
            if part["mimeType"] == "text/plain" and "data" in part.get("body", {}):
                body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                break
    elif "body" in payload and "data" in payload["body"]:
        body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

    return {
        "id": message_id,
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "subject": headers.get("Subject", ""),
        "date": headers.get("Date", ""),
        "body": body[:4000],  # Trim large emails
    }


def send_email(to: str, subject: str, body: str) -> str:
    """Send an email from the authenticated Gmail account."""
    svc = get_service()
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    svc.users().messages().send(userId="me", body={"raw": raw}).execute()
    return f"Email sent to {to} with subject '{subject}'."


def label_email(message_id: str, add_labels: list[str] = None, remove_labels: list[str] = None) -> str:
    """Add or remove labels on an email (e.g. INBOX, STARRED, TRASH, or custom labels)."""
    svc = get_service()
    body = {}
    if add_labels:
        body["addLabelIds"] = add_labels
    if remove_labels:
        body["removeLabelIds"] = remove_labels
    svc.users().messages().modify(userId="me", id=message_id, body=body).execute()
    return f"Labels updated on message {message_id}."


def search_emails(query: str, max_results: int = 10) -> list[dict]:
    """Search Gmail with a query string (supports Gmail search syntax)."""
    return list_emails(max_results=max_results, query=query)
