"""Render the §5.14 weekly opportunity email body.

One opportunity per recipient. Plain string interpolation — no Jinja —
because the structure is fixed and the inputs are heavily validated
upstream. HTML is whitespace-tolerant and uses inline styles so it
renders the same way in Gmail / Outlook / Apple Mail without a CSS
loader.

The unsubscribe link is the recipient's own — pass the per-recipient
token in. Header values for `List-Unsubscribe` and `List-Unsubscribe-Post`
are produced by the same helper so mailbox providers see them in lock-step.
"""
from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Any

from api.config import settings


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    html: str
    text: str
    headers: dict[str, str]


def _truncate(value: str, length: int) -> str:
    value = value.strip()
    return value if len(value) <= length else value[: length - 1] + "…"


def _unsubscribe_url(token: str) -> str:
    base = settings.email_public_base_url.rstrip("/")
    return f"{base}/email-subscriptions/unsubscribe?token={token}"


def render_weekly_opportunity(
    *,
    opportunity: dict[str, Any],
    unsubscribe_token: str,
    week_key: str,
) -> RenderedEmail:
    title = opportunity.get("title") or "(untitled opportunity)"
    agency = opportunity.get("agency") or ""
    due_date = opportunity.get("due_date") or "TBD"
    naics = opportunity.get("naics") or ""
    set_aside = opportunity.get("set_aside") or "open"
    description = (opportunity.get("description") or "").strip()
    source_url = opportunity.get("source_url") or ""
    footer_address = settings.email_legal_footer_address

    subject = f"This week's federal opportunity: {_truncate(title, 60)}"
    unsub_url = _unsubscribe_url(unsubscribe_token)

    short_description = _truncate(description, 600)
    safe_title = html.escape(title)
    safe_agency = html.escape(agency)
    safe_set_aside = html.escape(set_aside)
    safe_naics = html.escape(naics)
    safe_due = html.escape(str(due_date))
    safe_description = html.escape(short_description).replace("\n", "<br>")
    safe_source = html.escape(source_url)
    safe_footer = html.escape(footer_address) if footer_address else ""
    safe_unsub = html.escape(unsub_url)

    html_body = f"""<!doctype html>
<html lang="en">
<body style="margin:0;padding:0;background:#f6f6f6;font-family:-apple-system,Segoe UI,Roboto,sans-serif;color:#1a1a1a;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="padding:24px 0;">
    <tr><td align="center">
      <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="max-width:600px;background:#ffffff;border-radius:8px;overflow:hidden;">
        <tr><td style="padding:24px 32px 8px 32px;">
          <p style="margin:0;font-size:12px;letter-spacing:1px;color:#666;text-transform:uppercase;">SamRail · Week {week_key}</p>
          <h1 style="margin:8px 0 0 0;font-size:22px;line-height:1.3;">{safe_title}</h1>
        </td></tr>
        <tr><td style="padding:8px 32px 0 32px;font-size:14px;color:#444;">
          <p style="margin:0 0 4px 0;"><strong>Agency:</strong> {safe_agency or "—"}</p>
          <p style="margin:0 0 4px 0;"><strong>Due:</strong> {safe_due}</p>
          <p style="margin:0 0 4px 0;"><strong>Set-aside:</strong> {safe_set_aside}</p>
          <p style="margin:0 0 4px 0;"><strong>NAICS:</strong> {safe_naics or "—"}</p>
        </td></tr>
        <tr><td style="padding:16px 32px 0 32px;font-size:15px;line-height:1.5;color:#1a1a1a;">
          <p style="margin:0;">{safe_description or "(no description provided in SAM.gov listing)"}</p>
        </td></tr>
        <tr><td style="padding:24px 32px 32px 32px;">
          <a href="{safe_source}" style="display:inline-block;padding:10px 18px;background:#0b5fff;color:#fff;text-decoration:none;border-radius:6px;font-size:14px;">View on SAM.gov</a>
        </td></tr>
        <tr><td style="padding:0 32px 24px 32px;font-size:12px;color:#888;line-height:1.5;border-top:1px solid #eee;">
          <p style="margin:12px 0 0 0;">You're getting this because you joined the SamRail waitlist. One curated federal opportunity per week — no other email.</p>
          {f'<p style="margin:8px 0 0 0;">{safe_footer}</p>' if safe_footer else ""}
          <p style="margin:8px 0 0 0;"><a href="{safe_unsub}" style="color:#666;">Unsubscribe</a></p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""

    text_lines = [
        f"SamRail — Week {week_key}",
        "",
        title,
        "",
        f"Agency: {agency or '—'}",
        f"Due: {due_date}",
        f"Set-aside: {set_aside}",
        f"NAICS: {naics or '—'}",
        "",
        short_description or "(no description provided in SAM.gov listing)",
        "",
        f"View on SAM.gov: {source_url}" if source_url else "",
        "",
        "—",
        "You're getting this because you joined the SamRail waitlist.",
    ]
    if footer_address:
        text_lines.append(footer_address)
    text_lines.append(f"Unsubscribe: {unsub_url}")
    text_body = "\n".join(line for line in text_lines if line is not None)

    headers = {
        "List-Unsubscribe": f"<{unsub_url}>",
        "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
    }
    return RenderedEmail(subject=subject, html=html_body, text=text_body, headers=headers)
