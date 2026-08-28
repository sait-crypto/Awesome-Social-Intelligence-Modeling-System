"""Send a clear maintainer notification for the paper-processing workflow."""

from __future__ import annotations

import html
import os
import smtplib
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


MAX_LOG_CHARACTERS = 60_000


def _read_log(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        return f"Unable to read {path.name}: {exc}"


def collect_logs() -> str:
    """Collect bounded validation/update logs copied into the notification job."""
    candidates: list[Path] = []
    for name in ("update_log.txt", "validation_log.txt"):
        direct = Path(name)
        if direct.is_file():
            candidates.append(direct)

    configured_log_dir = Path(os.environ.get("NOTIFICATION_LOG_DIR", "notification-logs"))
    if configured_log_dir.is_dir():
        for pattern in ("*.txt", "*.log"):
            candidates.extend(sorted(configured_log_dir.rglob(pattern)))

    unique_paths: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved not in seen:
            unique_paths.append(path)
            seen.add(resolved)

    if not unique_paths:
        return "No processing log files were available. Open the workflow run for full details."

    sections = [f"==== {path.name} ====\n{_read_log(path)}" for path in unique_paths]
    combined = "\n\n".join(sections)
    if len(combined) > MAX_LOG_CHARACTERS:
        return combined[:MAX_LOG_CHARACTERS] + "\n\n[Logs truncated; open the workflow run for the remainder.]"
    return combined


def _status_details(status: str) -> tuple[str, str, str, str]:
    normalized = status.strip().casefold()
    if normalized == "success":
        return (
            "✅ [SIM AUTO UPDATE SUCCEEDED]",
            "Automatic paper update completed",
            "#216e4b",
            "The accepted paper data was written to the main repository. The public website rebuild is queued separately.",
        )
    if normalized == "cancelled":
        return (
            "⚠️ [SIM AUTO UPDATE CANCELLED]",
            "Automatic paper update was cancelled",
            "#9a6700",
            "The run did not complete. Check the workflow before assuming the paper is public.",
        )
    return (
        "🚨 [SIM AUTO UPDATE FAILED]",
        "Automatic paper update failed",
        "#b42318",
        "The submission was not published by this run. Review the failure and retry after correcting it.",
    )


def _receivers(value: str) -> list[str]:
    return [part.strip() for part in value.replace(";", ",").split(",") if part.strip()]


def send_email() -> bool:
    sender = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "")
    receivers = _receivers(os.environ.get("NOTIFICATION_EMAIL", ""))
    smtp_server = os.environ.get("SMTP_SERVER", "").strip()
    smtp_port = os.environ.get("SMTP_PORT", "").strip()

    status = os.environ.get("WORKFLOW_STATUS") or os.environ.get("workflow_status") or "unknown"
    pr_branch = os.environ.get("PR_BRANCH", "unknown")
    pr_user = os.environ.get("PR_USER", "unknown")
    pr_number = os.environ.get("PR_NUMBER", "unknown")
    pr_title = os.environ.get("PR_TITLE", "Paper submission")
    context_label = os.environ.get("CONTEXT_LABEL", "").strip() or f"PR #{pr_number}"
    pr_url = os.environ.get("PR_URL", "")
    run_url = os.environ.get("RUN_URL", "")
    automation_kind = os.environ.get("AUTOMATION_KIND", "Paper database update")

    if not all([sender, password, receivers, smtp_server, smtp_port]):
        print("Skipping email: SMTP notification configuration is incomplete.")
        return False

    prefix, heading, accent, outcome = _status_details(status)
    heading = os.environ.get("NOTIFICATION_HEADING", "").strip() or heading
    outcome = os.environ.get("OUTCOME_MESSAGE", "").strip() or outcome
    subject = f"{prefix} {context_label} by @{pr_user}"
    logs = collect_logs()
    details_url = run_url or pr_url

    plain_body = f"""{heading.upper()}

Status: {status.upper()}
Automation: {automation_kind}
Context: {context_label} — {pr_title}
Submitter: @{pr_user}
Branch: {pr_branch}

{outcome}

Pull request: {pr_url or 'Unavailable'}
Workflow run: {run_url or 'Unavailable'}

=== Processing logs ===
{logs}
"""

    escaped_logs = html.escape(logs)
    action_link = (
        f'<a href="{html.escape(details_url, quote=True)}" style="color:{accent};font-weight:700">Open the workflow details</a>'
        if details_url
        else "Open the GitHub Actions page for details."
    )
    html_body = f"""<!doctype html>
<html>
  <body style="margin:0;background:#f4f1ea;color:#17202a;font-family:Arial,sans-serif">
    <div style="max-width:760px;margin:0 auto;padding:28px 18px">
      <div style="border-top:10px solid {accent};background:#ffffff;padding:28px;border-radius:8px">
        <p style="margin:0 0 8px;color:{accent};font-size:12px;font-weight:800;letter-spacing:.08em;text-transform:uppercase">{html.escape(prefix)}</p>
        <h1 style="margin:0 0 12px;font-size:28px;line-height:1.2">{html.escape(heading)}</h1>
        <p style="margin:0 0 22px;font-size:16px;line-height:1.55"><strong>{html.escape(outcome)}</strong></p>
        <table style="width:100%;border-collapse:collapse;font-size:14px">
          <tr><td style="padding:8px;border-top:1px solid #ddd6c8;color:#6b6f76">Status</td><td style="padding:8px;border-top:1px solid #ddd6c8;font-weight:800;color:{accent}">{html.escape(status.upper())}</td></tr>
          <tr><td style="padding:8px;border-top:1px solid #ddd6c8;color:#6b6f76">Automation</td><td style="padding:8px;border-top:1px solid #ddd6c8">{html.escape(automation_kind)}</td></tr>
          <tr><td style="padding:8px;border-top:1px solid #ddd6c8;color:#6b6f76">Context</td><td style="padding:8px;border-top:1px solid #ddd6c8">{html.escape(context_label)} — {html.escape(pr_title)}</td></tr>
          <tr><td style="padding:8px;border-top:1px solid #ddd6c8;color:#6b6f76">Submitter</td><td style="padding:8px;border-top:1px solid #ddd6c8">@{html.escape(pr_user)}</td></tr>
          <tr><td style="padding:8px;border-top:1px solid #ddd6c8;color:#6b6f76">Branch</td><td style="padding:8px;border-top:1px solid #ddd6c8">{html.escape(pr_branch)}</td></tr>
        </table>
        <p style="margin:22px 0 0">{action_link}</p>
      </div>
      <div style="margin-top:18px;background:#17202a;color:#e8edf2;padding:20px;border-radius:8px">
        <h2 style="margin:0 0 12px;font-size:15px">Processing logs</h2>
        <pre style="margin:0;white-space:pre-wrap;word-break:break-word;font:12px/1.5 Consolas,monospace">{escaped_logs}</pre>
      </div>
    </div>
  </body>
</html>"""

    message = MIMEMultipart("alternative")
    message["From"] = f"Awesome SIM Bot <{sender}>"
    message["To"] = ", ".join(receivers)
    message["Subject"] = Header(subject, "utf-8")
    message.attach(MIMEText(plain_body, "plain", "utf-8"))
    message.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        port = int(smtp_port)
        if port == 465:
            with smtplib.SMTP_SSL(smtp_server, port, timeout=30) as server:
                server.login(sender, password)
                server.sendmail(sender, receivers, message.as_string())
        else:
            with smtplib.SMTP(smtp_server, port, timeout=30) as server:
                server.starttls()
                server.login(sender, password)
                server.sendmail(sender, receivers, message.as_string())
    except Exception as exc:
        print(f"Failed to send notification email: {exc}")
        raise

    print(f"Notification email sent to {len(receivers)} recipient(s): {subject}")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if send_email() else 1)
