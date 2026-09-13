"""Email service — send verification emails via Resend."""

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Send emails via Resend."""

    async def send_verification(self, email: str, token: str) -> bool:
        """Send verification email.

        Args:
            email: Recipient email
            token: Verification token

        Returns:
            True if sent successfully
        """
        if not settings.RESEND_API_KEY:
            logger.warning("RESEND_API_KEY not configured")
            return False

        verification_url = f"{settings.FRONTEND_URL}/auth/verify?token={token}"

        try:
            import httpx

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "from": f"Forcecast <{settings.EMAIL_FROM}>",
                        "to": [email],
                        "subject": "Verify your Forcecast account",
                        "html": self._verification_template(verification_url),
                    },
                )

                if resp.status_code == 200:
                    logger.info(f"Verification email sent to {email}")
                    return True
                else:
                    logger.error(f"Failed to send email: {resp.status_code} {resp.text}")
                    return False

        except Exception as e:
            logger.error(f"Email send error: {e}")
            return False

    def _verification_template(self, url: str) -> str:
        """Generate verification email HTML."""
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h1 style="color: #1a1a1a;">Welcome to Forcecast!</h1>
    <p style="color: #4a4a4a; line-height: 1.6;">
        Thank you for signing up. Please verify your email address to start voting.
    </p>
    <a href="{url}" style="display: inline-block; background-color: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: 500; margin: 20px 0;">
        Verify Email
    </a>
    <p style="color: #6a6a6a; font-size: 14px;">
        This link expires in 24 hours. If you didn't create an account, you can safely ignore this email.
    </p>
</body>
</html>
"""
