import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Enum, LargeBinary
from database import Base
from utils import get_ist_time

class EventRegistration(Base):
    __tablename__ = "event_registrations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    registration_id = Column(String(50), unique=True, index=True, nullable=False)
    response_number = Column(Integer, nullable=False)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), index=True, nullable=False)
    phone = Column(String(30), nullable=False)
    college = Column(String(200), nullable=False)
    department = Column(String(120), nullable=False)
    year = Column(String(20), nullable=False)
    roll_number = Column(String(50), nullable=True)
    
    event_name = Column(String(150), nullable=False)
    amount = Column(Integer, nullable=False)
    upi_id = Column(String(100), nullable=False)
    upi_reference_id = Column(String(120), unique=True, index=True, nullable=False)
    payment_screenshot_blob = Column(LargeBinary(length=4294967295), nullable=True)
    payment_screenshot_filename = Column(String(255), nullable=True)
    payment_screenshot_mime = Column(String(100), nullable=True)
    payment_screenshot_size = Column(Integer, nullable=True)
    
    payment_status = Column(String(50), default="PENDING_REVIEW") # PENDING_REVIEW, APPROVED, REJECTED, NEEDS_CORRECTION
    registration_status = Column(String(50), default="SUBMITTED") # SUBMITTED, UPDATED, CONFIRMED, REJECTED, CANCELLED
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
    
    created_at = Column(DateTime, default=get_ist_time)
    updated_at = Column(DateTime, default=get_ist_time, onupdate=get_ist_time)
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)


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
