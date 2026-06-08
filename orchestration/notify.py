"""
Slack notification helpers.
Sends a message to a webhook URL when the pipeline fails.
Set SLACK_WEBHOOK_URL in .env to enable.
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime

logger = logging.getLogger(__name__)


def send_slack(message: str, color: str = "#EF4444") -> bool:
    """
    Post a message to Slack via an Incoming Webhook.

    Parameters
    ----------
    message : plain text or mrkdwn message body
    color   : sidebar colour ('#EF4444' = red for errors, '#10B981' = green)

    Returns
    -------
    bool : True if delivered, False if webhook not configured or request failed
    """
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        logger.debug("SLACK_WEBHOOK_URL not set — notification skipped.")
        return False

    payload = {
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": message},
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"TheLook pipeline  |  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
                            }
                        ],
                    },
                ],
            }
        ]
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req  = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                logger.info("Slack notification sent.")
                return True
            logger.warning("Slack returned status %d", resp.status)
            return False
    except urllib.error.URLError as e:
        logger.warning("Slack notification failed: %s", e)
        return False


def notify_failure(step: str, error: Exception) -> None:
    """Send a formatted failure alert."""
    msg = (
        f":rotating_light: *Pipeline failed at step: `{step}`*\n"
        f"```{type(error).__name__}: {error}```"
    )
    send_slack(msg, color="#EF4444")


def notify_success(duration_seconds: float) -> None:
    """Send a success notification with run duration."""
    mins, secs = divmod(int(duration_seconds), 60)
    msg = (
        f":white_check_mark: *Pipeline completed successfully*\n"
        f"Duration: `{mins}m {secs}s`"
    )
    send_slack(msg, color="#10B981")
