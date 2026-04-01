from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String(150), unique=True, nullable=False)
    password = Column(String(512), nullable=False)


class PasswordResetToken(Base):
    __tablename__ = 'password_reset_tokens'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    token = Column(String(64), unique=True, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, nullable=False, default=False)

    user = relationship('User', backref='reset_tokens')

    __table_args__ = (
        Index('idx_password_reset_tokens_token', 'token'),
        Index('idx_password_reset_tokens_user_id', 'user_id'),
    )


class Switch(Base):
    __tablename__ = 'switches'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)
    last_checkin = Column(DateTime, nullable=False, default=datetime.utcnow)
    timeout_period = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default='active')
    reminder_sent = Column(Boolean, nullable=False, default=False)
    trigger_email_sent = Column(Boolean, nullable=False, default=False)

    user = relationship('User', backref='switch')

    __table_args__ = (
        Index('idx_switches_status', 'status'),
        Index('idx_switches_last_checkin', 'last_checkin'),
    )
