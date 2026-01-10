import os
import secrets
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask import Flask, flash, render_template, url_for, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from email_service import send_trigger_notification, send_reminder_notification, send_password_reset_email

load_dotenv()

user = os.environ.get("DB_USER")
password = os.environ.get("DB_PASSWORD")
host = os.environ.get("DB_HOST")
port = os.environ.get("DB_PORT")
database = os.environ.get("DB_NAME")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")
app.config['SQLALCHEMY_DATABASE_URI'] = f"postgresql://{user}:{password}@{host}:{port}/{database}?sslmode=require"
db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique = True, nullable = False)
    password = db.Column(db.String(512), nullable = False)


class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, nullable=False, default=False)
    
    user = db.relationship('User', backref='reset_tokens')


class Switch(db.Model):
    __tablename__ = 'switches'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    last_checkin = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    timeout_period = db.Column(db.Integer, nullable=False)  # in seconds
    status = db.Column(db.String(20), nullable=False, default='active')
    reminder_sent = db.Column(db.Boolean, nullable=False, default=False)  # Track if reminder email was sent
    trigger_email_sent = db.Column(db.Boolean, nullable=False, default=False)  # Track if trigger email was sent
    
    user = db.relationship('User', backref='switch')


def check_switches_and_send_emails():
    """Background task to check switches and send reminder/trigger emails"""
    with app.app_context():
        now = datetime.utcnow()
        active_switches = Switch.query.filter_by(status='active').all()
        base_url = os.environ.get('BASE_URL', 'http://localhost:5000')
        dashboard_url = f"{base_url}/dashboard"
        
        for switch in active_switches:
            next_trigger_time = switch.last_checkin + timedelta(seconds=switch.timeout_period)
            time_remaining = (next_trigger_time - now).total_seconds()
            
            # Check if switch has expired
            if time_remaining <= 0 and not switch.trigger_email_sent:
                switch.status = "triggered"
                switch.trigger_email_sent = True
                db.session.commit()
                
                # Send trigger email
                send_trigger_notification(switch.user.email, switch, dashboard_url)
                print(f"[SCHEDULER] Trigger email sent for switch {switch.id}")
            
            # Send reminder if 25% time remaining and reminder not sent
            elif time_remaining > 0 and not switch.reminder_sent:
                percent_remaining = (time_remaining / switch.timeout_period) * 100
                
                # Send reminder when 25% time remaining (or less than 1 hour for short timeouts)
                if percent_remaining <= 25 or (time_remaining <= 3600 and switch.timeout_period > 3600):
                    send_reminder_notification(switch.user.email, switch, int(time_remaining), dashboard_url)
                    switch.reminder_sent = True
                    db.session.commit()
                    print(f"[SCHEDULER] Reminder email sent for switch {switch.id}")


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")
    
    user_id = session["user_id"]
    switch = Switch.query.filter_by(user_id=user_id).first()
    
    next_trigger_time = None
    if switch:
        now = datetime.utcnow()
        next_trigger_time = switch.last_checkin + timedelta(seconds=switch.timeout_period)
        
        if now > next_trigger_time and switch.status != "triggered":
            switch.status = "triggered"
            db.session.commit()
    
    return render_template('dashboard.html', switch=switch, next_trigger_time=next_trigger_time)

@app.route("/")
@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        
        if not email or not password:
            flash("Please enter both email and password", "error")
            return render_template('login.html', email=email)
        
        user = User.query.filter_by(email=email).first()

        if user:
            if check_password_hash(user.password, password):
                session["user_id"] = user.id
                flash("Successfully logged in!", "success")
                return redirect('/dashboard')
            else:
                flash("Incorrect password. Please try again.", "error")
                return render_template('login.html', email=email)
        else:
            flash("No account found with this email address. Please check your email or sign up.", "error")
            return render_template('login.html', email=email)

    return render_template('login.html')

@app.route("/log_out")
def log_out():
    session.clear()
    flash("You have been logged out successfully", "success")
    return redirect("/login")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        
        if not email:
            flash("Please enter your email address", "error")
            return render_template('forgot_password.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate reset token
            token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(hours=1)
            
            # Invalidate any existing tokens for this user
            PasswordResetToken.query.filter_by(user_id=user.id, used=False).update({'used': True})
            
            reset_token = PasswordResetToken(
                user_id=user.id,
                token=token,
                expires_at=expires_at,
                used=False
            )
            db.session.add(reset_token)
            db.session.commit()
            
            # Send reset email
            base_url = os.environ.get('BASE_URL', request.url_root.rstrip('/'))
            reset_url = f"{base_url}/reset-password/{token}"
            send_password_reset_email(user.email, reset_url)
            
            flash("Password reset link has been sent to your email address", "success")
        else:
            # Don't reveal if email exists (security best practice)
            flash("If an account exists with this email, a password reset link has been sent", "success")
        
        return redirect('/login')
    
    return render_template('forgot_password.html')


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    reset_token = PasswordResetToken.query.filter_by(token=token, used=False).first()
    
    if not reset_token:
        flash("Invalid or expired reset token. Please request a new password reset.", "error")
        return redirect('/forgot-password')
    
    if datetime.utcnow() > reset_token.expires_at:
        flash("This reset link has expired. Please request a new password reset.", "error")
        return redirect('/forgot-password')
    
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        if not password or not confirm_password:
            flash("Please fill in all fields", "error")
            return render_template('reset_password.html', token=token)
        
        if len(password) < 8:
            flash("Password must be at least 8 characters long", "error")
            return render_template('reset_password.html', token=token)
        
        if password != confirm_password:
            flash("Passwords do not match", "error")
            return render_template('reset_password.html', token=token)
        
        # Update password
        user = reset_token.user
        user.password = generate_password_hash(password)
        reset_token.used = True
        db.session.commit()
        
        flash("Password reset successfully! Please sign in with your new password.", "success")
        return redirect('/login')
    
    return render_template('reset_password.html', token=token)


@app.route("/switch/create", methods=["GET", "POST"])
def create_switch():
    if "user_id" not in session:
        return redirect("/login")
    
    user_id = session["user_id"]
    
    if request.method == "POST":
        timeout_period = request.form.get("timeout_period", type=int)
        
        if not timeout_period or timeout_period <= 0:
            flash("Please enter a valid timeout period (in seconds)")
            return render_template('create_switch.html')
        
        # Check if user already has a switch
        existing_switch = Switch.query.filter_by(user_id=user_id).first()
        
        try:
            if existing_switch:
                # Update existing switch - reset email flags
                existing_switch.timeout_period = timeout_period
                existing_switch.last_checkin = datetime.utcnow()
                existing_switch.status = "active"
                existing_switch.reminder_sent = False
                existing_switch.trigger_email_sent = False
                db.session.commit()
            else:
                # Create new switch
                new_switch = Switch(
                    user_id=user_id,
                    timeout_period=timeout_period,
                    last_checkin=datetime.utcnow(),
                    status="active",
                    reminder_sent=False,
                    trigger_email_sent=False
                )
                db.session.add(new_switch)
                db.session.commit()
        
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating switch: {str(e)}")
            return render_template('create_switch.html')
        
        return redirect("/dashboard")
    
    return render_template('create_switch.html')


@app.route("/switch/<int:switch_id>/checkin", methods=["POST"])
def checkin(switch_id):
    if "user_id" not in session:
        return redirect("/login")
    
    user_id = session["user_id"]
    switch = Switch.query.filter_by(id=switch_id, user_id=user_id).first()
    
    if not switch:
        flash("Switch not found or you don't have permission to access it")
        return redirect("/dashboard")
    
    # Update check-in - reset email flags
    switch.last_checkin = datetime.utcnow()
    switch.status = "active"
    switch.reminder_sent = False
    switch.trigger_email_sent = False
    db.session.commit()
    
    return redirect("/dashboard")


@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        
        if not email or not password:
            flash("Please fill in all fields", "error")
            return render_template('register.html', email=email)
        
        if len(password) < 8:
            flash("Password must be at least 8 characters long", "error")
            return render_template('register.html', email=email)
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with this email already exists. Please sign in instead.", "error")
            return render_template('register.html', email=email)
        
        try:
            new_user = User(email=email, password=generate_password_hash(password))
            db.session.add(new_user)
            db.session.commit()
            flash("Account created successfully! Please sign in.", "success")
            return redirect('/login')
        
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating account: {str(e)}", "error")
            return render_template('register.html', email=email)

    return render_template('register.html')

@app.route("/db-test")
def db_test():
    try:
        db.session.execute(text('SELECT 1')).scalar()
        return "Database connected sucessfully"
    except Exception as e:
        return f"Database connection failed: {e}"

# Initialize scheduler for background tasks
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=check_switches_and_send_emails,
    trigger=IntervalTrigger(minutes=1),  # Check every minute
    id='check_switches_job',
    name='Check switches and send emails',
    replace_existing=True
)

# Initialize database and start scheduler
with app.app_context():
    db.create_all()

# Start scheduler for background email checks
scheduler.start()
print("[SCHEDULER] Started background task scheduler for email notifications")

if __name__ == '__main__':
    app.run(debug=True)