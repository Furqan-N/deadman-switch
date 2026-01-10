# Email Notification Setup Guide

This guide explains how to configure email notifications for the Deadman Switch application.

## Environment Variables

Add these variables to your `.env` file:

```env
# Email Configuration (SMTP)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com
```

## Gmail Setup (Recommended)

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Generate an App Password**:
   - Go to Google Account settings
   - Security → 2-Step Verification → App passwords
   - Generate a new app password for "Mail"
   - Use this password (not your regular Gmail password) in `SMTP_PASSWORD`

3. **Configure in .env**:
   ```env
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=your-16-char-app-password
   EMAIL_FROM=your-email@gmail.com
   ```

## Other Email Providers

### Outlook/Office365
```env
SMTP_SERVER=smtp.office365.com
SMTP_PORT=587
SMTP_USERNAME=your-email@outlook.com
SMTP_PASSWORD=your-password
EMAIL_FROM=your-email@outlook.com
```

### SendGrid
```env
SMTP_SERVER=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-sendgrid-api-key
EMAIL_FROM=your-verified-email@example.com
```

### Mailgun
```env
SMTP_SERVER=smtp.mailgun.org
SMTP_PORT=587
SMTP_USERNAME=your-mailgun-username
SMTP_PASSWORD=your-mailgun-password
EMAIL_FROM=your-verified-email@yourdomain.com
```

## Features

### Reminder Emails
- Sent when 25% of timeout period remains
- For short timeouts (< 1 hour), sent when less than 1 hour remains
- Includes countdown timer and direct link to check in

### Trigger Emails
- Sent immediately when switch expires
- Contains details about when it was triggered
- Includes link to dashboard to reactivate

## Testing

If email is not configured, the system will log messages to console instead of sending emails. Check your terminal/logs for:
- `[EMAIL] Email not configured. Would send to...`
- `[EMAIL] Successfully sent email to...`
- `[EMAIL] Error sending email to...`

## Background Scheduler

The app uses APScheduler to check switches every minute and send appropriate emails. The scheduler runs automatically when the Flask app starts.

## Troubleshooting

1. **Emails not sending**: Check SMTP credentials in `.env`
2. **Authentication errors**: Verify username/password are correct
3. **Connection errors**: Check firewall/network allows SMTP connections
4. **Gmail blocking**: Make sure you're using an App Password, not regular password





