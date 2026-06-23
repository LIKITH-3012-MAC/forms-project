import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Enum, LargeBinary, Float
from sqlalchemy.orm import deferred
from database import Base
from utils import get_ist_time

class EventRegistration(Base):
    __tablename__ = "event_registrations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    registration_id = Column(String(50), unique=True, index=True, nullable=False)
    response_number = Column(Integer, nullable=False)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), index=True, nullable=False)
    phone = Column(String(30), index=True, nullable=False)
    college = Column(String(200), index=True, nullable=False)
    department = Column(String(120), index=True, nullable=False)
    year = Column(String(20), index=True, nullable=False)
    roll_number = Column(String(50), nullable=True)
    
    event_name = Column(String(150), nullable=False)
    amount = Column(Integer, nullable=False)
    upi_id = Column(String(100), nullable=False)
    upi_reference_id = Column(String(120), unique=True, index=True, nullable=False)
    payment_screenshot_blob = deferred(Column(LargeBinary(length=4294967295), nullable=True))
    payment_screenshot_filename = Column(String(255), nullable=True)
    payment_screenshot_mime = Column(String(100), nullable=True)
    payment_screenshot_size = Column(Integer, nullable=True)
    
    payment_status = Column(String(50), default="PENDING_REVIEW", index=True) # PENDING_REVIEW, APPROVED, REJECTED, NEEDS_CORRECTION
    registration_status = Column(String(50), default="SUBMITTED", index=True) # SUBMITTED, UPDATED, CONFIRMED, REJECTED, CANCELLED
    email_status = Column(String(50), default="NOT_SENT") # NOT_SENT, SENT, FAILED
    
    edit_token = Column(String(100), unique=True, index=True, nullable=False)
    view_token = Column(String(100), unique=True, index=True, nullable=False)
    status_token = Column(String(100), unique=True, index=True, nullable=False)
    
    edit_token_expires_at = Column(DateTime, nullable=True)
    is_edit_locked = Column(Boolean, default=False)
    edit_count = Column(Integer, default=0)
    
    last_edited_at = Column(DateTime, nullable=True)
    admin_note = Column(Text, nullable=True)
    internal_note = Column(Text, nullable=True)
    
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True) # IPv6 can be 45 chars
    
    ai_receipt_match_score = Column(Float, nullable=True)
    ai_receipt_label = Column(String(100), nullable=True)
    ai_receipt_provider = Column(String(100), nullable=True)
    ai_receipt_model_version = Column(String(100), nullable=True)
    ai_receipt_checked_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=get_ist_time, index=True)
    updated_at = Column(DateTime, default=get_ist_time, onupdate=get_ist_time)
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    
    # Participant Attendance & Certificate
    attended = Column(Boolean, default=False)
    attended_at = Column(DateTime, nullable=True)
    certificate_sent = Column(Boolean, default=False)
    certificate_sent_at = Column(DateTime, nullable=True)
    certificate_token = Column(String(255), unique=True, nullable=True)
    certificate_download_count = Column(Integer, default=0)
    certificate_last_downloaded_at = Column(DateTime, nullable=True)

class RegistrationAuditLog(Base):
    __tablename__ = "registration_audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    registration_id = Column(String(50), index=True, nullable=False)
    action = Column(String(100), nullable=False)
    old_data = Column(Text, nullable=True) # JSON dump
    new_data = Column(Text, nullable=True) # JSON dump
    performed_by = Column(String(100), nullable=False) # e.g. "user", "admin"
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=get_ist_time)

    # Rich fields for multi-admin action tracking
    actor_user_id = Column(Integer, nullable=True)
    actor_email = Column(String(150), nullable=True)
    actor_role = Column(String(50), nullable=True)
    action_type = Column(String(100), nullable=True)
    action_message = Column(Text, nullable=True)
    changes_json = Column(Text, nullable=True)
    user_agent = Column(Text, nullable=True)


class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    registration_id = Column(String(50), index=True, nullable=False)
    email_to = Column(String(150), nullable=False)
    email_type = Column(String(100), nullable=False) # e.g. "submission", "approved", "rejected", "correction", "updated"
    subject = Column(String(255), nullable=False)
    resend_message_id = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False) # SENT, FAILED
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_ist_time)


class ProblemLog(Base):
    __tablename__ = "problem_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    path = Column(String(255), nullable=False)
    reason = Column(String(255), nullable=True)
    details = Column(Text, nullable=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    exception_type = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=get_ist_time)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(150), unique=True, index=True, nullable=False)
    passwordHash = Column(String(255), nullable=False)
    role = Column(String(50), default="USER_WITH_FULL_ACCESS", nullable=False) # ADMIN, USER_WITH_FULL_ACCESS
    enabled = Column(Boolean, default=True, nullable=False)
    createdByAdmin = Column(Boolean, default=True, nullable=False)
    mustChangePassword = Column(Boolean, default=True, nullable=False)
    createdAt = Column(DateTime, default=get_ist_time)
    updatedAt = Column(DateTime, default=get_ist_time, onupdate=get_ist_time)
