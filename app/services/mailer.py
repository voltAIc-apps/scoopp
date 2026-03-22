# Email dispatch service — MVP provider: Brevo
# Sends the structured briefing email per spec template

import os
import logging
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


# ── template rendering ───────────────────────────────────────

def _render_plain_text(
    mail_context: Optional[Dict],
    person_name: str,
    person_email: Optional[str],
    company: Dict,
    person: Dict,
    request_context: Optional[Dict],
) -> str:
    """Render the plain-text briefing email per spec template."""
    lines = []

    # greeting
    consultant = (mail_context or {}).get("consultant_name", "")
    if consultant:
        lines.append(f"Hi {consultant},")
    else:
        lines.append("Hi,")
    lines.append("")
    lines.append("You have a new 30-minute intro call booked.")
    lines.append("")

    # ── meeting details ──
    sep = "\u2501" * 40
    lines.append(sep)
    lines.append("MEETING DETAILS")
    lines.append(sep)
    if mail_context:
        mc = mail_context
        if mc.get("meeting_date") or mc.get("meeting_time"):
            when_parts = [mc.get("meeting_date", ""), mc.get("meeting_time", "")]
            lines.append(f"When:        {' \u00b7 '.join(p for p in when_parts if p)}")
        with_parts = [person_name]
        if person_email:
            with_parts.append(person_email)
        lines.append(f"With:        {' \u00b7 '.join(with_parts)}")
        lines.append(f"Company:     {company.get('name', '')}")
        if mc.get("topic"):
            lines.append(f"Topic:       {mc['topic']}")
        if mc.get("meet_link"):
            lines.append(f"Google Meet: {mc['meet_link']}")
    lines.append("")

    # ── about company ──
    cname = company.get("name", "")
    lines.append(sep)
    lines.append(f"ABOUT {cname.upper()}")
    lines.append(sep)
    if company.get("description"):
        lines.append(company["description"])
        lines.append("")
    if company.get("website"):
        lines.append(f"Website:     {company['website']}")
    if company.get("industry"):
        lines.append(f"Industry:    {company['industry']}")
    if company.get("size"):
        lines.append(f"Size:        {company['size']}")
    if company.get("recent_news"):
        lines.append(f"Recent news: {company['recent_news']}")
    lines.append("")

    # ── about person ──
    lines.append(sep)
    lines.append(f"ABOUT {person_name.upper()}")
    lines.append(sep)
    if person.get("linkedin_url"):
        lines.append(f"LinkedIn: {person['linkedin_url']}")
    else:
        lines.append("LinkedIn profile not found automatically.")
    lines.append("")

    # ── context (how they found you) ──
    if request_context:
        rc = request_context
        has_any = rc.get("page_url") or rc.get("utm_source") or rc.get("custom")
        if has_any:
            lines.append(sep)
            lines.append("HOW THEY FOUND YOU")
            lines.append(sep)
            if rc.get("page_title") or rc.get("page_url"):
                page = " \u2014 ".join(
                    p for p in [rc.get("page_title"), rc.get("page_url")] if p
                )
                lines.append(f"Page:      {page}")
            utm_parts = [
                rc.get("utm_source", ""),
                rc.get("utm_medium", ""),
                rc.get("utm_campaign", ""),
            ]
            utm_str = " / ".join(p for p in utm_parts if p)
            if utm_str:
                lines.append(f"Source:    {utm_str}")
            if rc.get("custom") and isinstance(rc["custom"], dict):
                for k, v in rc["custom"].items():
                    lines.append(f"{k}: {v}")
            lines.append("")

    # ── footer ──
    lines.append(sep)
    lines.append("")
    lines.append("The Google Calendar invite has been sent to your calendar.")
    lines.append("All other attendees have also been invited directly.")
    lines.append("")
    lines.append("\u2013 Booking system")

    return "\n".join(lines)


def _render_html(plain_text: str) -> str:
    """Wrap plain text in minimal HTML for email clients."""
    import html as html_mod
    escaped = html_mod.escape(plain_text)
    # convert URLs to clickable links
    import re
    escaped = re.sub(
        r'(https?://[^\s<]+)',
        r'<a href="\1">\1</a>',
        escaped,
    )
    return f"""\
<!DOCTYPE html>
<html lang="de">
<head><meta charset="utf-8"></head>
<body style="font-family: 'Segoe UI', Tahoma, sans-serif; font-size: 14px;
             color: #222; line-height: 1.5; max-width: 640px; margin: 0 auto;
             padding: 24px;">
<pre style="white-space: pre-wrap; font-family: inherit;">{escaped}</pre>
</body>
</html>"""


# ── send via Brevo ───────────────────────────────────────────

async def _send_brevo(
    to: str,
    subject: str,
    html_content: str,
    text_content: str,
    from_addr: str,
    api_key: str,
) -> dict:
    """Send email via Brevo (Sendinblue) transactional API."""
    payload = {
        "sender": {"email": from_addr},
        "to": [{"email": to}],
        "subject": subject,
        "htmlContent": html_content,
        "textContent": text_content,
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": api_key,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(BREVO_API_URL, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()


# ── public interface ─────────────────────────────────────────

async def send_briefing_email(
    mail_to: str,
    mail_subject: Optional[str],
    mail_context: Optional[Dict],
    company: Dict,
    person: Dict,
    person_name: str,
    person_email: Optional[str],
    request_context: Optional[Dict],
) -> Dict[str, Any]:
    """Compose and send the briefing email. Returns {sent: bool, error?: str}."""
    # resolve config from env
    mail_provider = os.environ.get("MAIL_PROVIDER", "brevo").lower()
    mail_api_key = os.environ.get("MAIL_API_KEY", "")
    mail_from = os.environ.get("MAIL_FROM", "noreply@example.com")

    if not mail_api_key:
        return {"sent": False, "error": "MAIL_API_KEY not configured"}

    # build subject
    subject = mail_subject or f"Recherche-Ergebnis: {company.get('name', '')}"

    # render body
    plain = _render_plain_text(
        mail_context, person_name, person_email,
        company, person, request_context,
    )
    html = _render_html(plain)

    try:
        if mail_provider == "brevo":
            await _send_brevo(mail_to, subject, html, plain, mail_from, mail_api_key)
        else:
            return {"sent": False, "error": f"Unsupported mail provider: {mail_provider}"}
        logger.info("Briefing email sent to %s", mail_to)
        return {"sent": True}
    except Exception as exc:
        logger.error("Email send failed: %s", exc)
        return {"sent": False, "error": str(exc)}
