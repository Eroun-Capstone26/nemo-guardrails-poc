from typing import Dict, Any


def send_email(to: str, subject: str, body: str) -> Dict[str, Any]:
    return {
        "tool_name": "send_email",
        "status": "mock_executed",
        "arguments": {
            "to": to,
            "subject": subject,
            "body": body,
        },
    }


def grant_permission(user: str, permission: str, reason: str) -> Dict[str, Any]:
    return {
        "tool_name": "grant_permission",
        "status": "mock_executed",
        "arguments": {
            "user": user,
            "permission": permission,
            "reason": reason,
        },
    }
