import os
import secrets
from datetime import datetime, timedelta

from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

from app.database import engine, get_db, Base
from app.models import User, PasswordResetToken, Switch
from app.email_service import send_password_reset_email

load_dotenv()

app = FastAPI(title="Deadman Switch")
app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SECRET_KEY", "change-me"))
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# Create tables on startup
Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# Flash message helpers (replicate Flask's flash/get_flashed_messages)
# ---------------------------------------------------------------------------

def flash(request: Request, message: str, category: str = "message"):
    if "_flashes" not in request.session:
        request.session["_flashes"] = []
    request.session["_flashes"].append({"category": category, "message": message})


def render(request: Request, template: str, **kwargs):
    """Render a Jinja2 template with flash message support."""
    flashes = request.session.pop("_flashes", [])

    def get_flashed_messages(with_categories=False):
        if with_categories:
            return [(m["category"], m["message"]) for m in flashes]
        return [m["message"] for m in flashes]

    return templates.TemplateResponse(
        request=request,
        name=template,
        context={"get_flashed_messages": get_flashed_messages, **kwargs},
    )


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.get("/")
@app.get("/login")
async def login_page(request: Request):
    return render(request, "login.html")


@app.post("/login")
async def login(
    request: Request,
    email: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    email = email.strip()
    if not email or not password:
        flash(request, "Please enter both email and password", "error")
        return render(request, "login.html", email=email)

    user = db.query(User).filter_by(email=email).first()

    if user and check_password_hash(user.password, password):
        request.session["user_id"] = user.id
        flash(request, "Successfully logged in!", "success")
        return RedirectResponse("/dashboard", status_code=303)
    elif user:
        flash(request, "Incorrect password. Please try again.", "error")
    else:
        flash(request, "No account found with this email address. Please check your email or sign up.", "error")
    return render(request, "login.html", email=email)


@app.get("/log_out")
async def log_out(request: Request):
    request.session.clear()
    flash(request, "You have been logged out successfully", "success")
    return RedirectResponse("/login", status_code=303)


@app.get("/register")
async def register_page(request: Request):
    return render(request, "register.html")


@app.post("/register")
async def register(
    request: Request,
    email: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    email = email.strip()
    if not email or not password:
        flash(request, "Please fill in all fields", "error")
        return render(request, "register.html", email=email)

    if len(password) < 8:
        flash(request, "Password must be at least 8 characters long", "error")
        return render(request, "register.html", email=email)

    existing_user = db.query(User).filter_by(email=email).first()
    if existing_user:
        flash(request, "An account with this email already exists. Please sign in instead.", "error")
        return render(request, "register.html", email=email)

    try:
        new_user = User(email=email, password=generate_password_hash(password))
        db.add(new_user)
        db.commit()
        flash(request, "Account created successfully! Please sign in.", "success")
        return RedirectResponse("/login", status_code=303)
    except Exception as e:
        db.rollback()
        flash(request, f"Error creating account: {str(e)}", "error")
        return render(request, "register.html", email=email)


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

@app.get("/forgot-password")
async def forgot_password_page(request: Request):
    return render(request, "forgot_password.html")


@app.post("/forgot-password")
async def forgot_password(
    request: Request,
    email: str = Form(""),
    db: Session = Depends(get_db),
):
    email = email.strip()
    if not email:
        flash(request, "Please enter your email address", "error")
        return render(request, "forgot_password.html")

    user = db.query(User).filter_by(email=email).first()

    if user:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)
        db.query(PasswordResetToken).filter_by(user_id=user.id, used=False).update({"used": True})
        reset_token = PasswordResetToken(user_id=user.id, token=token, expires_at=expires_at, used=False)
        db.add(reset_token)
        db.commit()
        base_url = os.environ.get("BASE_URL", str(request.base_url).rstrip("/"))
        reset_url = f"{base_url}/reset-password/{token}"
        send_password_reset_email(user.email, reset_url)
        flash(request, "Password reset link has been sent to your email address", "success")
    else:
        flash(request, "If an account exists with this email, a password reset link has been sent", "success")

    return RedirectResponse("/login", status_code=303)


@app.get("/reset-password/{token}")
async def reset_password_page(request: Request, token: str, db: Session = Depends(get_db)):
    reset_token = db.query(PasswordResetToken).filter_by(token=token, used=False).first()
    if not reset_token:
        flash(request, "Invalid or expired reset token. Please request a new password reset.", "error")
        return RedirectResponse("/forgot-password", status_code=303)
    if datetime.utcnow() > reset_token.expires_at:
        flash(request, "This reset link has expired. Please request a new password reset.", "error")
        return RedirectResponse("/forgot-password", status_code=303)
    return render(request, "reset_password.html", token=token)


@app.post("/reset-password/{token}")
async def reset_password(
    request: Request,
    token: str,
    password: str = Form(""),
    confirm_password: str = Form(""),
    db: Session = Depends(get_db),
):
    reset_token = db.query(PasswordResetToken).filter_by(token=token, used=False).first()
    if not reset_token:
        flash(request, "Invalid or expired reset token. Please request a new password reset.", "error")
        return RedirectResponse("/forgot-password", status_code=303)
    if datetime.utcnow() > reset_token.expires_at:
        flash(request, "This reset link has expired. Please request a new password reset.", "error")
        return RedirectResponse("/forgot-password", status_code=303)

    if not password or not confirm_password:
        flash(request, "Please fill in all fields", "error")
        return render(request, "reset_password.html", token=token)
    if len(password) < 8:
        flash(request, "Password must be at least 8 characters long", "error")
        return render(request, "reset_password.html", token=token)
    if password != confirm_password:
        flash(request, "Passwords do not match", "error")
        return render(request, "reset_password.html", token=token)

    user = reset_token.user
    user.password = generate_password_hash(password)
    reset_token.used = True
    db.commit()
    flash(request, "Password reset successfully! Please sign in with your new password.", "success")
    return RedirectResponse("/login", status_code=303)


# ---------------------------------------------------------------------------
# Switch routes
# ---------------------------------------------------------------------------

@app.get("/dashboard")
async def dashboard(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=303)

    switch = db.query(Switch).filter_by(user_id=user_id).first()
    next_trigger_time = None

    if switch:
        now = datetime.utcnow()
        next_trigger_time = switch.last_checkin + timedelta(seconds=switch.timeout_period)
        if now > next_trigger_time and switch.status != "triggered":
            switch.status = "triggered"
            db.commit()

    return render(request, "dashboard.html", switch=switch, next_trigger_time=next_trigger_time)


@app.get("/switch/create")
async def create_switch_page(request: Request):
    if "user_id" not in request.session:
        return RedirectResponse("/login", status_code=303)
    return render(request, "create_switch.html")


@app.post("/switch/create")
async def create_switch(
    request: Request,
    timeout_period: int = Form(0),
    db: Session = Depends(get_db),
):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=303)

    if not timeout_period or timeout_period <= 0:
        flash(request, "Please enter a valid timeout period (in seconds)")
        return render(request, "create_switch.html")

    existing_switch = db.query(Switch).filter_by(user_id=user_id).first()

    try:
        if existing_switch:
            existing_switch.timeout_period = timeout_period
            existing_switch.last_checkin = datetime.utcnow()
            existing_switch.status = "active"
            existing_switch.reminder_sent = False
            existing_switch.trigger_email_sent = False
        else:
            new_switch = Switch(
                user_id=user_id,
                timeout_period=timeout_period,
                last_checkin=datetime.utcnow(),
                status="active",
                reminder_sent=False,
                trigger_email_sent=False,
            )
            db.add(new_switch)
        db.commit()
    except Exception as e:
        db.rollback()
        flash(request, f"Error creating switch: {str(e)}")
        return render(request, "create_switch.html")

    return RedirectResponse("/dashboard", status_code=303)


@app.post("/switch/{switch_id}/checkin")
async def checkin(request: Request, switch_id: int, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login", status_code=303)

    switch = db.query(Switch).filter_by(id=switch_id, user_id=user_id).first()
    if not switch:
        flash(request, "Switch not found or you don't have permission to access it")
        return RedirectResponse("/dashboard", status_code=303)

    switch.last_checkin = datetime.utcnow()
    switch.status = "active"
    switch.reminder_sent = False
    switch.trigger_email_sent = False
    db.commit()

    return RedirectResponse("/dashboard", status_code=303)
