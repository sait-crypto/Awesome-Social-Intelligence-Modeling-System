import os
import smtplib
from email.mime.text import MIMEText
from email.header import Header

def collect_logs():
    logs = []
    # 收集常见的日志文件
    for fname in ['update_log.txt', 'validation_log.txt']:
        if os.path.exists(fname):
            with open(fname, 'r', encoding='utf-8', errors='ignore') as f:
                logs.append(f"\n==== {fname} ====\n{f.read()}")
    # 收集 GitHub Actions 运行时的错误日志（如有）
    gha_log_dir = os.path.join(os.environ.get('GITHUB_WORKSPACE', '.'), 'logs')
    if os.path.isdir(gha_log_dir):
        for root, _, files in os.walk(gha_log_dir):
            for file in files:
                if file.endswith('.log'):
                    path = os.path.join(root, file)
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        logs.append(f"\n==== {file} ====\n{f.read()}")
    # 也可收集 runner 的 _temp 目录下的命令日志（如有权限）
    return "\n".join(logs) if logs else "No log files found."

def send_email():
    sender = os.environ.get('SMTP_USER')
    password = os.environ.get('SMTP_PASSWORD')
    receiver = os.environ.get('NOTIFICATION_EMAIL')
    smtp_server = os.environ.get('SMTP_SERVER')
    smtp_port = os.environ.get('SMTP_PORT')
    
    status = os.environ.get('workflow_status', 'Unknown')
    pr_branch = os.environ.get('PR_BRANCH', 'Unknown')
    pr_user = os.environ.get('PR_USER', 'Unknown User')
    
    if not all([sender, password, receiver, smtp_server]):
        print("Skipping email: Missing SMTP configuration.")
        return

    # 收集所有日志
    log_content = collect_logs()

    subject = f"[{pr_branch}] PR by @{pr_user}: {status}"
    body = f"""
PR Submitter: {pr_user}
PR Branch: {pr_branch}
Workflow Status: {status}

=== Execution & Error Logs ===
{log_content}

==========================
"""

    message = MIMEText(body, 'plain', 'utf-8')
    message['From'] = f"Awesome Bot <{sender}>"
    message['To'] = receiver
    message['Subject'] = subject

    try:
        if smtp_port == '465':
            server = smtplib.SMTP_SSL(smtp_server, int(smtp_port))
        else:
            server = smtplib.SMTP(smtp_server, int(smtp_port))
            server.starttls()
        server.login(sender, password)
        server.sendmail(sender, [receiver], message.as_string())
        server.quit()
        print("Notification email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")

if __name__ == "__main__":
    send_email()