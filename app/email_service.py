"""
Email service for sending notifications
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from string import Template
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
EMAIL_FROM = os.environ.get("EMAIL_FROM", SMTP_USERNAME)


def format_time_remaining(seconds):
    """Format seconds into human-readable time"""
    if seconds < 60:
        return f"{seconds} second{'s' if seconds != 1 else ''}"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''}"
    else:
        days = seconds // 86400
        return f"{days} day{'s' if days != 1 else ''}"


TRIGGER_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #ef4444, #dc2626); color: white; padding: 20px; border-radius: 8px 8px 0 0; }
        .content { background: #f8fafc; padding: 30px; border-radius: 0 0 8px 8px; }
        .button { display: inline-block; background: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; margin-top: 20px; }
        .alert { background: #fee2e2; border-left: 4px solid #ef4444; padding: 15px; margin: 20px 0; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Deadman Switch TRIGGERED</h1>
        </div>
        <div class="content">
            <div class="alert">
                <strong>Your deadman switch has been triggered!</strong>
            </div>
            <p>Hello,</p>
            <p>This is an automated notification that your deadman switch was triggered because you did not check in before the timeout period expired.</p>
            <p><strong>Trigger Details:</strong></p>
            <ul>
                <li><strong>Last Check-in:</strong> $last_checkin</li>
                <li><strong>Timeout Period:</strong> $timeout_period</li>
                <li><strong>Triggered At:</strong> $triggered_at</li>
            </ul>
            <p>Please log in to your account to reactivate your switch.</p>
            <a href="$dashboard_url" class="button">Go to Dashboard</a>
            <p style="margin-top: 30px; font-size: 0.9em; color: #64748b;">
                If you did not expect this email, please log in and check your switch settings.
            </p>
        </div>
    </div>
</body>
</html>
"""

PASSWORD_RESET_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #6366f1, #4f46e5); color: white; padding: 20px; border-radius: 8px 8px 0 0; }
        .content { background: #f8fafc; padding: 30px; border-radius: 0 0 8px 8px; }
        .button { display: inline-block; background: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; margin-top: 20px; }
        .info { background: #e0e7ff; border-left: 4px solid #6366f1; padding: 15px; margin: 20px 0; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Password Reset Request</h1>
        </div>
        <div class="content">
            <p>Hello,</p>
            <p>We received a request to reset your password for your Deadman Switch account.</p>
            <div class="info">
                <strong>Click the button below to reset your password:</strong>
            </div>
            <a href="$reset_url" class="button">Reset Password</a>
            <p style="margin-top: 30px; font-size: 0.9em; color: #64748b;">
                If you didn't request this password reset, you can safely ignore this email. Your password will not be changed.
            </p>
            <p style="font-size: 0.9em; color: #64748b;">
                This link will expire in 1 hour for security reasons.
            </p>
        </div>
    </div>
</body>
</html>
"""

REMINDER_EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #f59e0b, #d97706); color: white; padding: 20px; border-radius: 8px 8px 0 0; }
        .content { background: #f8fafc; padding: 30px; border-radius: 0 0 8px 8px; }
        .button { display: inline-block; background: #6366f1; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; margin-top: 20px; }
        .warning { background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; border-radius: 4px; }
        .countdown { font-size: 1.5em; font-weight: bold; color: #f59e0b; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Reminder: Check-In Required</h1>
        </div>
        <div class="content">
            <div class="warning">
                <strong>Don't forget to check in!</strong>
            </div>
            <p>Hello,</p>
            <p>This is a reminder that your deadman switch will trigger soon if you don't check in.</p>
            <div class="countdown">
                Time Remaining: $time_remaining
            </div>
            <p><strong>Switch Details:</strong></p>
            <ul>
                <li><strong>Last Check-in:</strong> $last_checkin</li>
                <li><strong>Timeout Period:</strong> $timeout_period</li>
                <li><strong>Next Trigger Time:</strong> $next_trigger_time</li>
            </ul>
            <p>Please check in soon to keep your switch active.</p>
            <a href="$dashboard_url" class="button">Check In Now</a>
            <p style="margin-top: 30px; font-size: 0.9em; color: #64748b;">
                This is an automated reminder. You will receive a notification when your switch is triggered.
            </p>
        </div>
    </div>
</body>
</html>
"""


def send_email(to_email, subject, html_body):
    """Send an email using SMTP"""
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print(f"[EMAIL] Email not configured. Would send to {to_email}: {subject}")
        return False

    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = EMAIL_FROM
        msg['To'] = to_email
        msg['Subject'] = subject

        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)

        print(f"[EMAIL] Successfully sent email to {to_email}: {subject}")
        return True

    except Exception as e:
        print(f"[EMAIL] Error sending email to {to_email}: {str(e)}")
        return False


def send_trigger_notification(user_email, switch, dashboard_url):
    """Send email when switch is triggered"""
    last_checkin_str = switch.last_checkin.strftime('%Y-%m-%d %H:%M:%S UTC')
    triggered_at_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    timeout_period_str = format_time_remaining(switch.timeout_period)

    template = Template(TRIGGER_EMAIL_TEMPLATE)
    html_body = template.safe_substitute(
        last_checkin=last_checkin_str,
        timeout_period=timeout_period_str,
        triggered_at=triggered_at_str,
        dashboard_url=dashboard_url
    )

    subject = "Deadman Switch TRIGGERED"
    return send_email(user_email, subject, html_body)


def send_reminder_notification(user_email, switch, time_remaining_seconds, dashboard_url):
    """Send reminder email before switch triggers"""
    last_checkin_str = switch.last_checkin.strftime('%Y-%m-%d %H:%M:%S UTC')
    next_trigger_time = switch.last_checkin + timedelta(seconds=switch.timeout_period)
    next_trigger_str = next_trigger_time.strftime('%Y-%m-%d %H:%M:%S UTC')
    timeout_period_str = format_time_remaining(switch.timeout_period)
    time_remaining_str = format_time_remaining(time_remaining_seconds)

    template = Template(REMINDER_EMAIL_TEMPLATE)
    html_body = template.safe_substitute(
        time_remaining=time_remaining_str,
        last_checkin=last_checkin_str,
        timeout_period=timeout_period_str,
        next_trigger_time=next_trigger_str,
        dashboard_url=dashboard_url
    )

    subject = "Reminder: Check-In Required Soon"
    return send_email(user_email, subject, html_body)


def send_password_reset_email(user_email, reset_url):
    """Send password reset email"""
    template = Template(PASSWORD_RESET_EMAIL_TEMPLATE)
    html_body = template.safe_substitute(reset_url=reset_url)

    subject = "Password Reset Request"
    return send_email(user_email, subject, html_body)
