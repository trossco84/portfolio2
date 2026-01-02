"""Email notifications for portfolio updates."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from portfolio.config import settings
from portfolio.utils.logging import logger


class EmailNotifier:
    """Send email notifications via SMTP or SendGrid."""

    def __init__(self):
        """Initialize email notifier."""
        self.sendgrid_api_key = getattr(settings, 'sendgrid_api_key', None)
        self.email_from = getattr(settings, 'email_from', None)
        self.email_to = getattr(settings, 'email_to', None)

    def send_email(
        self,
        subject: str,
        body: str,
        to_email: Optional[str] = None,
        html: bool = False
    ) -> bool:
        """
        Send email notification.

        Args:
            subject: Email subject
            body: Email body (text or HTML)
            to_email: Recipient email (defaults to settings.email_to)
            html: Whether body is HTML

        Returns:
            True if sent successfully
        """
        to_email = to_email or self.email_to

        if not to_email:
            logger.warning("No recipient email configured")
            return False

        if self.sendgrid_api_key:
            return self._send_via_sendgrid(subject, body, to_email, html)
        else:
            logger.info("No email service configured - email not sent")
            logger.info(f"Subject: {subject}")
            logger.info(f"To: {to_email}")
            logger.info(f"Body:\n{body}")
            return False

    def _send_via_sendgrid(
        self,
        subject: str,
        body: str,
        to_email: str,
        html: bool
    ) -> bool:
        """Send via SendGrid API."""
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, To, Content

            message = Mail(
                from_email=Email(self.email_from),
                to_emails=To(to_email),
                subject=subject,
                plain_text_content=Content("text/plain", body) if not html else None,
                html_content=Content("text/html", body) if html else None
            )

            sg = SendGridAPIClient(self.sendgrid_api_key)
            response = sg.send(message)

            if response.status_code in [200, 201, 202]:
                logger.info(f"Email sent successfully to {to_email}")
                return True
            else:
                logger.error(f"SendGrid error: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Failed to send email via SendGrid: {e}")
            return False


# Global instance
email_notifier = EmailNotifier()
