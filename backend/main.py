import os
import csv
import io
import json
import datetime
from typing import Optional
from fastapi import FastAPI, Depends, Request, HTTPException, status, Response, Form, File, UploadFile, BackgroundTasks
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import case, desc, func

import config
import models
import schemas
import security
import email_service
from database import engine, get_db, SessionLocal
from utils import generate_registration_id, generate_secure_token, escape_html, get_ist_time

def frontend_url(path: str) -> str:
    base = config.FRONTEND_URL.rstrip("/")
    clean_path = path.lstrip("/")
    return f"{base}/{clean_path}"

def send_email_background(registration_id: int, email_type: str):
    db = SessionLocal()
    registration = None
    try:
        registration = db.query(models.EventRegistration).filter(models.EventRegistration.id == registration_id).first()
        if not registration:
            return

        if email_type == "submission_received":
            email_sent = email_service.send_submission_received_email(registration, db)
        elif email_type == "details_updated":
            email_sent = email_service.send_details_updated_email(registration, db)
        elif email_type == "payment_approved":
            email_sent = email_service.send_payment_approved_email(registration, db)
        elif email_type == "payment_rejected":
            email_sent = email_service.send_payment_rejected_email(registration, db)
        elif email_type == "needs_correction":
            email_sent = email_service.send_needs_correction_email(registration, db)
        elif email_type == "resend_email":
            email_sent = email_service.send_latest_status_email(registration, db)
        else:
            email_sent = False

        registration.email_status = "SENT" if email_sent else "FAILED"
        db.commit()
    except Exception as e:
        print(f"Background email {email_type} failed:", repr(e))
        try:
            if registration:
                registration.email_status = "FAILED"
                db.commit()
        except Exception as db_err:
            print("Failed to rollback/commit email status in background:", repr(db_err))
            db.rollback()
    finally:
        db.close()

# Initialize tables
models.Base.metadata.create_all(bind=engine)

# Auto-migration: check columns for payment screenshot blobs
try:
    with engine.connect() as conn:
        from sqlalchemy import text
        result = conn.execute(text("SHOW COLUMNS FROM event_registrations"))
        existing_cols = [row[0].lower() for row in result.fetchall()]
        
        # Add columns if missing
        if "payment_screenshot_blob" not in existing_cols:
            conn.execute(text("ALTER TABLE event_registrations ADD COLUMN payment_screenshot_blob LONGBLOB"))
            print("✓ Migration: Added payment_screenshot_blob to event_registrations.")
            
        if "payment_screenshot_filename" not in existing_cols:
            conn.execute(text("ALTER TABLE event_registrations ADD COLUMN payment_screenshot_filename VARCHAR(255)"))
            print("✓ Migration: Added payment_screenshot_filename to event_registrations.")
            
        if "payment_screenshot_mime" not in existing_cols:
            conn.execute(text("ALTER TABLE event_registrations ADD COLUMN payment_screenshot_mime VARCHAR(100)"))
            print("✓ Migration: Added payment_screenshot_mime to event_registrations.")
            
        if "payment_screenshot_size" not in existing_cols:
            conn.execute(text("ALTER TABLE event_registrations ADD COLUMN payment_screenshot_size INT"))
            print("✓ Migration: Added payment_screenshot_size to event_registrations.")
            
        conn.commit()
except Exception as e:
    print(f"Skipping MySQL schema migrations: {e}")

app = FastAPI(title=config.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://forms-project-qcdc.onrender.com",
        "https://forms-project-f3sb.vercel.app",
        config.FRONTEND_URL
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper: Check deadline status
def is_deadline_passed() -> bool:
    try:
        deadline_dt = datetime.datetime.strptime(config.EVENT_DEADLINE, "%Y-%m-%d %H:%M:%S")
        return datetime.datetime.now() > deadline_dt
    except Exception as e:
        print(f"Deadline date parsing failed: {e}")
        return False

# Dependency: Verify admin token from Authorization header or cookie
def verify_admin_token(request: Request) -> str:
    auth_header = request.headers.get("authorization")
    token = None
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header[7:]
    
    if not token:
        token = request.headers.get("x-admin-token")
        
    if not token:
        token = request.cookies.get("admin_session")
        
    if not token:
        token = request.query_params.get("token")

    if not token:
        raise HTTPException(status_code=401, detail="Unauthorized: No admin token provided.")
        
    user_id = security.verify_session(token)
    if user_id != "admin_authenticated":
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid admin token.")
    return user_id

# Helper: Get client IP
def get_client_ip(request: Request) -> str:
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"

def log_problem_to_db(path: str, reason: str, details: str, user_agent: str, ip_address: str, exception_type: str = None):
    try:
        db = SessionLocal()
        try:
            log_entry = models.ProblemLog(
                path=path,
                reason=reason,
                details=details,
                user_agent=user_agent,
                ip_address=ip_address,
                exception_type=exception_type
            )
            db.add(log_entry)
            db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"Failed to log problem to DB: {e}", flush=True)

# Exception Handlers returning JSON
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    user_agent = request.headers.get("user-agent", "Unknown")
    ip_address = get_client_ip(request)
    log_problem_to_db(
        path=str(request.url.path),
        reason=f"HTTP Error {exc.status_code}",
        details=exc.detail,
        user_agent=user_agent,
        ip_address=ip_address,
        exception_type=f"HTTPException_{exc.status_code}"
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "code": f"HTTP_{exc.status_code}"
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print("GLOBAL ERROR:", repr(exc))
    user_agent = request.headers.get("user-agent", "Unknown")
    ip_address = get_client_ip(request)
    log_problem_to_db(
        path=str(request.url.path),
        reason="Server issue",
        details="An unexpected server error occurred.",
        user_agent=user_agent,
        ip_address=ip_address,
        exception_type=type(exc).__name__
    )
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Server error. Please try again or contact support.",
            "code": "SERVER_ERROR"
        }
    )

# --- USER ENDPOINTS ---

@app.api_route("/", methods=["GET", "HEAD"])
async def root_redirect(request: Request):
    """Redirect to the Vercel frontend landing page."""
    if request.method == "HEAD":
        return Response(status_code=status.HTTP_200_OK)
    return RedirectResponse(url=config.FRONTEND_URL)

@app.get("/api/health")
async def health_check():
    """Service health state endpoint."""
    return {
        "success": True,
        "status": "ok",
        "message": "Backend running"
    }

@app.get("/api/form-config")
async def get_form_config(db: Session = Depends(get_db)):
    """Return registration parameters and live seat info as JSON."""
    approved_count = db.query(models.EventRegistration).filter(
        models.EventRegistration.payment_status == "APPROVED"
    ).count()

    seats_available = max(0, config.EVENT_SEATS_TOTAL - approved_count)
    deadline_passed = is_deadline_passed()
    form_enabled = not deadline_passed and seats_available > 0

    return {
        "event_name": config.EVENT_NAME,
        "event_subtitle": config.EVENT_SUBTITLE,
        "event_amount": config.EVENT_AMOUNT,
        "upi_id": config.UPI_ID,
        "organizer_name": config.ORGANIZER_NAME,
        "deadline": config.EVENT_DEADLINE,
        "seats_total": config.EVENT_SEATS_TOTAL,
        "seats_available": seats_available,
        "form_enabled": form_enabled
    }

@app.get("/api/check-utr/{utr}")
async def check_utr(utr: str, db: Session = Depends(get_db)):
    """Checks if a UTR transaction reference already exists in database."""
    cleaned_utr = utr.strip().upper()
    exists = db.query(models.EventRegistration).filter(
        models.EventRegistration.upi_reference_id == cleaned_utr
    ).first() is not None

    if exists:
        return {"available": False, "message": "UTR Reference ID is already taken"}
    return {"available": True, "message": "UTR Reference ID is unique"}

@app.post("/api/register")
async def register_attendee(
    background_tasks: BackgroundTasks,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    college: str = Form(None),
    department: str = Form(None),
    year: str = Form(...),
    roll_number: str = Form(None),
    upi_reference_id: str = Form(...),
    agreement: bool = Form(...),
    payment_screenshot: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Processes new registration submission with payment screenshot upload."""
    try:
        # Debug logs
        print("📩 /api/register called")
        print("📧 email:", email)
        print("📱 phone:", phone)

        # Normalize UTR
        upi_reference_id = upi_reference_id.strip().upper()
        print("💳 UTR:", upi_reference_id)
        print("🖼 file:", payment_screenshot.filename, payment_screenshot.content_type)

        approved_count = db.query(models.EventRegistration).filter(
            models.EventRegistration.payment_status == "APPROVED"
        ).count()
        seats_available = config.EVENT_SEATS_TOTAL - approved_count
        if seats_available <= 0:
            return JSONResponse(status_code=400, content={"success": False, "message": "Registration seats are fully booked."})

        if is_deadline_passed():
            return JSONResponse(status_code=400, content={"success": False, "message": "Registration deadline has expired."})

        # Field validations
        import re
        full_name = full_name.strip()
        if len(full_name) < 2 or len(full_name) > 150:
            return JSONResponse(status_code=400, content={"success": False, "message": "Full Name must be between 2 and 150 characters."})

        email = email.strip().lower()
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
            return JSONResponse(status_code=400, content={"success": False, "message": "Please enter a valid email address."})

        phone = re.sub(r"\s+", "", phone)
        if not re.match(r"^(\+91)?[6789]\d{9}$", phone):
            return JSONResponse(status_code=400, content={"success": False, "message": "Phone number must be a valid 10-digit number, optionally prefixed with +91."})

        if len(upi_reference_id) < 8:
            return JSONResponse(status_code=400, content={"success": False, "message": "UPI/UTR reference ID must be at least 8 characters long."})

        if not agreement:
            return JSONResponse(status_code=400, content={"success": False, "message": "You must confirm that the details are correct."})

        college = (college or "").strip()
        department = (department or "").strip()
        if not college:
            return JSONResponse(status_code=400, content={"success": False, "message": "College name is required."})
        if not department:
            return JSONResponse(status_code=400, content={"success": False, "message": "Department is required."})

        # Duplicate UTR check
        duplicate_utr = db.query(models.EventRegistration).filter(
            models.EventRegistration.upi_reference_id == upi_reference_id
        ).first()
        if duplicate_utr:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message": "This UPI Reference ID / UTR is already used. Please check and enter the correct payment reference."
                }
            )

        # Validate payment screenshot file
        if not payment_screenshot or not payment_screenshot.filename:
            return JSONResponse(status_code=400, content={"success": False, "message": "Payment screenshot is required."})

        contents = await payment_screenshot.read()
        file_size = len(contents)
        if file_size == 0:
            return JSONResponse(status_code=400, content={"success": False, "message": "Payment screenshot is required."})

        filename = payment_screenshot.filename
        content_type = payment_screenshot.content_type

        allowed_types = ["image/jpeg", "image/png", "image/webp"]
        if content_type not in allowed_types:
            return JSONResponse(status_code=400, content={"success": False, "message": "Only JPG, PNG, WEBP screenshots are allowed."})

        max_size = 3 * 1024 * 1024
        if file_size > max_size:
            return JSONResponse(status_code=400, content={"success": False, "message": "Screenshot size must be below 3MB."})

        # Generate metadata
        reg_id = generate_registration_id()
        while db.query(models.EventRegistration).filter(models.EventRegistration.registration_id == reg_id).first():
            reg_id = generate_registration_id()

        total_submissions = db.query(models.EventRegistration).count()
        response_num = total_submissions + 1

        client_ip = get_client_ip(request)
        user_agent = request.headers.get("user-agent", "Unknown")

        registration = models.EventRegistration(
            registration_id=reg_id,
            response_number=response_num,
            full_name=full_name,
            email=email,
            phone=phone,
            college=college,
            department=department,
            year=year,
            roll_number=roll_number,
            event_name=config.EVENT_NAME,
            amount=config.EVENT_AMOUNT,
            upi_id=config.UPI_ID,
            upi_reference_id=upi_reference_id,
            payment_screenshot_blob=contents,
            payment_screenshot_filename=filename,
            payment_screenshot_mime=content_type,
            payment_screenshot_size=file_size,
            payment_status="PENDING_REVIEW",
            registration_status="SUBMITTED",
            edit_token=generate_secure_token(),
            view_token=generate_secure_token(),
            status_token=generate_secure_token(),
            user_agent=user_agent,
            ip_address=client_ip
        )

        db.add(registration)
        try:
            db.commit()
            db.refresh(registration)
            print("✅ DB insert success:", reg_id)
        except Exception as db_error:
            db.rollback()
            print("❌ Registration DB insert failed:", repr(db_error))
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Unable to save registration. Please try again.",
                    "code": "DB_INSERT_FAILED"
                }
            )

        # Audit log
        audit_data = {
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "college": college,
            "department": department,
            "year": year,
            "roll_number": roll_number,
            "upi_reference_id": upi_reference_id,
            "filename": filename,
            "size": file_size
        }
        audit_log = models.RegistrationAuditLog(
            registration_id=reg_id,
            action="SUBMITTED",
            new_data=json.dumps(audit_data),
            performed_by="user",
            ip_address=client_ip
        )
        db.add(audit_log)
        db.commit()

        # Trigger email in background task
        background_tasks.add_task(send_email_background, registration.id, "submission_received")


        return {
            "success": True,
            "message": "Registration submitted successfully",
            "registration_id": reg_id,
            "view_token": registration.view_token,
            "edit_token": registration.edit_token,
            "status_token": registration.status_token,
            "redirect_url": frontend_url(f"thank-you.html?rid={reg_id}&token={registration.status_token}")
        }
    except Exception as e:
        print("❌ Register error:", repr(e))
        raise e

@app.get("/api/response/{view_token}")
async def get_response_by_token(view_token: str, db: Session = Depends(get_db)):
    """Retrieve registration response by view token."""
    reg = db.query(models.EventRegistration).filter(
        models.EventRegistration.view_token == view_token
    ).first()

    if not reg:
        raise HTTPException(status_code=404, detail="Response not found or token invalid.")

    return {
        "success": True,
        "data": {
            "registration_id": reg.registration_id,
            "full_name": reg.full_name,
            "email": reg.email,
            "phone": reg.phone,
            "college": reg.college,
            "department": reg.department,
            "year": reg.year,
            "roll_number": reg.roll_number,
            "event_name": reg.event_name,
            "amount": reg.amount,
            "upi_reference_id": reg.upi_reference_id,
            "payment_screenshot_filename": reg.payment_screenshot_filename,
            "payment_screenshot_size": reg.payment_screenshot_size,
            "payment_screenshot_mime": reg.payment_screenshot_mime,
            "payment_status": reg.payment_status,
            "registration_status": reg.registration_status,
            "created_at": reg.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
    }

@app.get("/api/status/{status_token}")
async def get_status_by_token(status_token: str, db: Session = Depends(get_db)):
    """Retrieve timeline and payment status details."""
    reg = db.query(models.EventRegistration).filter(
        models.EventRegistration.status_token == status_token
    ).first()

    if not reg:
        raise HTTPException(status_code=404, detail="Status details not found or token invalid.")

    return {
        "success": True,
        "data": {
            "registration_id": reg.registration_id,
            "full_name": reg.full_name,
            "email": reg.email,
            "payment_status": reg.payment_status,
            "registration_status": reg.registration_status,
            "is_edit_locked": reg.is_edit_locked,
            "admin_note": reg.admin_note,
            "created_at": reg.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "approved_at": reg.approved_at.strftime("%Y-%m-%d %H:%M:%S") if reg.approved_at else None,
            "rejected_at": reg.rejected_at.strftime("%Y-%m-%d %H:%M:%S") if reg.rejected_at else None,
            "edit_token": reg.edit_token,
            "view_token": reg.view_token
        }
    }

@app.get("/api/edit/{edit_token}")
async def get_editable_fields(edit_token: str, db: Session = Depends(get_db)):
    """Retrieve editable registration details by edit token."""
    reg = db.query(models.EventRegistration).filter(
        models.EventRegistration.edit_token == edit_token
    ).first()

    if not reg:
        raise HTTPException(status_code=404, detail="Edit link invalid or not found.")

    if reg.edit_token_expires_at and reg.edit_token_expires_at < get_ist_time():
        raise HTTPException(status_code=400, detail="This edit token has expired.")

    if reg.is_edit_locked and config.LOCK_EDIT_AFTER_APPROVAL:
        raise HTTPException(status_code=400, detail="Editing has been locked since your registration is approved.")

    return {
        "success": True,
        "data": {
            "full_name": reg.full_name,
            "email": reg.email,
            "phone": reg.phone,
            "college": reg.college,
            "department": reg.department,
            "year": reg.year,
            "roll_number": reg.roll_number,
            "event_name": reg.event_name,
            "amount": reg.amount,
            "upi_reference_id": reg.upi_reference_id,
            "payment_screenshot_filename": reg.payment_screenshot_filename,
            "payment_screenshot_size": reg.payment_screenshot_size,
            "payment_screenshot_mime": reg.payment_screenshot_mime,
            "is_edit_locked": reg.is_edit_locked
        }
    }

@app.put("/api/edit/{edit_token}")
async def update_registration(
    edit_token: str,
    background_tasks: BackgroundTasks,
    full_name: str = Form(...),
    phone: str = Form(...),
    college: str = Form(...),
    department: str = Form(...),
    year: str = Form(...),
    roll_number: str = Form(None),
    upi_reference_id: str = Form(...),
    payment_screenshot: Optional[UploadFile] = File(None),
    request: Request = None,
    db: Session = Depends(get_db)
):
    """Processes edited responses."""
    reg = db.query(models.EventRegistration).filter(
        models.EventRegistration.edit_token == edit_token
    ).first()

    if not reg:
        return JSONResponse(status_code=404, content={"success": False, "message": "Edit link invalid."})

    if reg.is_edit_locked and config.LOCK_EDIT_AFTER_APPROVAL:
        return JSONResponse(status_code=400, content={"success": False, "message": "Editing is locked for this response."})

    # Field validations
    import re
    full_name = full_name.strip()
    if len(full_name) < 2 or len(full_name) > 150:
        return JSONResponse(status_code=400, content={"success": False, "message": "Full Name must be between 2 and 150 characters."})

    phone = re.sub(r"\s+", "", phone)
    if not re.match(r"^(\+91)?[6789]\d{9}$", phone):
        return JSONResponse(status_code=400, content={"success": False, "message": "Phone number must be a valid 10-digit number, optionally prefixed with +91."})

    upi_reference_id = upi_reference_id.strip().upper()
    if len(upi_reference_id) < 8:
        return JSONResponse(status_code=400, content={"success": False, "message": "UPI/UTR reference ID must be at least 8 characters long."})

    college = (college or "").strip()
    department = (department or "").strip()
    if not college:
        return JSONResponse(status_code=400, content={"success": False, "message": "College name is required."})
    if not department:
        return JSONResponse(status_code=400, content={"success": False, "message": "Department is required."})

    # Check duplicate UTR
    if upi_reference_id != reg.upi_reference_id:
        duplicate_utr = db.query(models.EventRegistration).filter(
            models.EventRegistration.upi_reference_id == upi_reference_id,
            models.EventRegistration.id != reg.id
        ).first()
        if duplicate_utr:
            return JSONResponse(status_code=400, content={"success": False, "message": "This transaction reference ID has already been submitted."})

    # Optional Payment Screenshot replacement validation
    new_screenshot_provided = False
    new_contents = None
    new_filename = None
    new_mime = None
    new_size = None

    if payment_screenshot and payment_screenshot.filename:
        new_contents = await payment_screenshot.read()
        new_size = len(new_contents)
        if new_size > 0:
            new_screenshot_provided = True
            new_filename = payment_screenshot.filename
            new_mime = payment_screenshot.content_type

            ext = os.path.splitext(new_filename)[1].lower()
            allowed_exts = {".jpg", ".jpeg", ".png", ".webp"}
            if ext not in allowed_exts:
                return JSONResponse(status_code=400, content={"success": False, "message": "Screenshot file must be JPG, PNG, or WEBP."})

            allowed_types = {"image/jpeg", "image/png", "image/webp"}
            if new_mime not in allowed_types:
                return JSONResponse(status_code=400, content={"success": False, "message": "Screenshot file must be JPG, PNG, or WEBP."})

            max_size = 3 * 1024 * 1024
            if new_size > max_size:
                return JSONResponse(status_code=400, content={"success": False, "message": "Screenshot size must be below 3MB."})

    # Record old data for audit trail
    old_data = {
        "full_name": reg.full_name,
        "phone": reg.phone,
        "college": reg.college,
        "department": reg.department,
        "year": reg.year,
        "roll_number": reg.roll_number,
        "upi_reference_id": reg.upi_reference_id,
        "payment_screenshot_filename": reg.payment_screenshot_filename,
        "payment_screenshot_size": reg.payment_screenshot_size,
        "payment_status": reg.payment_status,
        "registration_status": reg.registration_status
    }

    # Reset payment status if UTR has changed or screenshot is updated
    utr_changed = upi_reference_id != reg.upi_reference_id
    if utr_changed or new_screenshot_provided:
        reg.payment_status = "PENDING_REVIEW"
    reg.registration_status = "UPDATED"

    # Update database record
    reg.full_name = full_name
    reg.phone = phone
    reg.college = college
    reg.department = department
    reg.year = year
    reg.roll_number = roll_number
    reg.upi_reference_id = upi_reference_id
    
    if new_screenshot_provided:
        reg.payment_screenshot_blob = new_contents
        reg.payment_screenshot_filename = new_filename
        reg.payment_screenshot_mime = new_mime
        reg.payment_screenshot_size = new_size
        
    reg.edit_count += 1
    reg.last_edited_at = get_ist_time()

    db.commit()

    # Audit log
    client_ip = get_client_ip(request)
    new_data = {
        "full_name": full_name,
        "phone": phone,
        "college": college,
        "department": department,
        "year": year,
        "roll_number": roll_number,
        "upi_reference_id": upi_reference_id,
        "new_screenshot_uploaded": new_screenshot_provided
    }
    audit_log = models.RegistrationAuditLog(
        registration_id=reg.registration_id,
        action="EDITED",
        old_data=json.dumps(old_data),
        new_data=json.dumps(new_data),
        performed_by="user",
        ip_address=client_ip
    )
    db.add(audit_log)
    db.commit()

    # Trigger details updated email in background task
    background_tasks.add_task(send_email_background, reg.id, "details_updated")


    return {
        "success": True,
        "message": "Response updated successfully",
        "status_token": reg.status_token
    }

# --- ADMINISTRATIVE API ENDPOINTS ---

@app.post("/api/admin/login")
async def admin_login(payload: schemas.AdminLogin):
    """Process admin password authentication and return token."""
    if payload.admin_password != config.ADMIN_SECRET:
        raise HTTPException(status_code=401, detail="Incorrect admin secret credentials.")

    session_token = security.sign_session("admin_authenticated")
    return {
        "success": True,
        "admin_token": session_token
    }

@app.get("/api/admin/registrations")
async def admin_registrations(
    search: Optional[str] = "",
    payment_status: Optional[str] = "",
    page: int = 1,
    page_size: int = 25,
    db: Session = Depends(get_db),
    admin_auth: str = Depends(verify_admin_token)
):
    """Retrieve administrative list of registrations with statistics and pagination."""
    page = max(1, page)
    page_size = max(1, min(100, page_size))

    total = db.query(models.EventRegistration).count()
    pending = db.query(models.EventRegistration).filter(models.EventRegistration.payment_status == "PENDING_REVIEW").count()
    approved = db.query(models.EventRegistration).filter(models.EventRegistration.payment_status == "APPROVED").count()
    rejected = db.query(models.EventRegistration).filter(models.EventRegistration.payment_status == "REJECTED").count()
    correction = db.query(models.EventRegistration).filter(models.EventRegistration.payment_status == "NEEDS_CORRECTION").count()
    
    today_start = get_ist_time().replace(hour=0, minute=0, second=0, microsecond=0)
    today = db.query(models.EventRegistration).filter(models.EventRegistration.created_at >= today_start).count()

    stats = {
        "total": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "needs_correction": correction,
        "today": today
    }

    query = db.query(models.EventRegistration)

    if search:
        search_q = f"%{search.strip()}%"
        query = query.filter(
            (models.EventRegistration.registration_id.like(search_q)) |
            (models.EventRegistration.full_name.like(search_q)) |
            (models.EventRegistration.email.like(search_q)) |
            (models.EventRegistration.phone.like(search_q)) |
            (models.EventRegistration.upi_reference_id.like(search_q))
        )

    if payment_status:
        query = query.filter(models.EventRegistration.payment_status == payment_status)

    total_filtered = query.count()
    import math
    total_pages = math.ceil(total_filtered / page_size) if total_filtered > 0 else 1

    ordered_query = query.order_by(
        case(
            (models.EventRegistration.payment_status == "PENDING_REVIEW", 1),
            else_=2
        ),
        desc(models.EventRegistration.created_at)
    )

    records = ordered_query.offset((page - 1) * page_size).limit(page_size).all()
    
    registrations_data = []
    for r in records:
        registrations_data.append({
            "registration_id": r.registration_id,
            "full_name": r.full_name,
            "email": r.email,
            "phone": r.phone,
            "amount": r.amount,
            "upi_reference_id": r.upi_reference_id,
            "payment_status": r.payment_status,
            "registration_status": r.registration_status,
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    return {
        "success": True,
        "stats": stats,
        "registrations": registrations_data,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_filtered": total_filtered,
            "total_pages": total_pages
        }
    }

@app.get("/api/payment-screenshot/{registration_id}")
async def get_payment_screenshot(
    registration_id: str,
    db: Session = Depends(get_db),
    admin_auth: str = Depends(verify_admin_token)
):
    """Retrieves uploaded payment screenshot image from DB for admins."""
    registration = db.query(models.EventRegistration).filter(
        models.EventRegistration.registration_id == registration_id
    ).first()

    if not registration or not registration.payment_screenshot_blob:
        raise HTTPException(status_code=404, detail="Screenshot not found")

    return Response(
        content=registration.payment_screenshot_blob,
        media_type=registration.payment_screenshot_mime,
        headers={
            "Content-Disposition": f"inline; filename={registration.payment_screenshot_filename}"
        }
    )

@app.get("/api/user/payment-screenshot/{view_token}")
async def get_user_payment_screenshot(
    view_token: str,
    db: Session = Depends(get_db)
):
    """Retrieves uploaded payment screenshot image from DB for users using view token."""
    registration = db.query(models.EventRegistration).filter(
        models.EventRegistration.view_token == view_token
    ).first()

    if not registration or not registration.payment_screenshot_blob:
        raise HTTPException(status_code=404, detail="Screenshot not found")

    return Response(
        content=registration.payment_screenshot_blob,
        media_type=registration.payment_screenshot_mime,
        headers={
            "Content-Disposition": f"inline; filename={registration.payment_screenshot_filename}"
        }
    )

@app.get("/api/admin/registration/{registration_id}")
async def admin_registration_detail(
    registration_id: str,
    db: Session = Depends(get_db),
    admin_auth: str = Depends(verify_admin_token)
):
    """Retrieve specific registration details, audit logs, and email history."""
    reg = db.query(models.EventRegistration).filter(
        models.EventRegistration.registration_id == registration_id
    ).first()

    if not reg:
        raise HTTPException(status_code=404, detail="Registration record not found.")

    audits = db.query(models.RegistrationAuditLog).filter(
        models.RegistrationAuditLog.registration_id == registration_id
    ).order_by(desc(models.RegistrationAuditLog.created_at)).all()

    emails = db.query(models.EmailLog).filter(
        models.EmailLog.registration_id == registration_id
    ).order_by(desc(models.EmailLog.created_at)).all()

    audits_data = [{
        "action": a.action,
        "old_data": a.old_data,
        "new_data": a.new_data,
        "performed_by": a.performed_by,
        "ip_address": a.ip_address,
        "created_at": a.created_at.strftime("%Y-%m-%d %H:%M:%S")
    } for a in audits]

    emails_data = [{
        "email_to": e.email_to,
        "email_type": e.email_type,
        "subject": e.subject,
        "status": e.status,
        "error_message": e.error_message,
        "created_at": e.created_at.strftime("%Y-%m-%d %H:%M:%S")
    } for e in emails]

    return {
        "success": True,
        "registration": {
            "registration_id": reg.registration_id,
            "response_number": reg.response_number,
            "full_name": reg.full_name,
            "email": reg.email,
            "phone": reg.phone,
            "college": reg.college,
            "department": reg.department,
            "year": reg.year,
            "roll_number": reg.roll_number,
            "event_name": reg.event_name,
            "amount": reg.amount,
            "upi_id": reg.upi_id,
            "upi_reference_id": reg.upi_reference_id,
            "payment_screenshot_filename": reg.payment_screenshot_filename,
            "payment_screenshot_size": reg.payment_screenshot_size,
            "payment_screenshot_mime": reg.payment_screenshot_mime,
            "payment_status": reg.payment_status,
            "registration_status": reg.registration_status,
            "is_edit_locked": reg.is_edit_locked,
            "edit_count": reg.edit_count,
            "admin_note": reg.admin_note,
            "created_at": reg.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "approved_at": reg.approved_at.strftime("%Y-%m-%d %H:%M:%S") if reg.approved_at else None,
            "rejected_at": reg.rejected_at.strftime("%Y-%m-%d %H:%M:%S") if reg.rejected_at else None,
            "user_agent": reg.user_agent,
            "ip_address": reg.ip_address
        },
        "audits": audits_data,
        "emails": emails_data
    }

@app.post("/api/admin/approve/{registration_id}")
async def admin_approve_payment(
    registration_id: str,
    payload: schemas.AdminAction,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin_auth: str = Depends(verify_admin_token)
):
    """Approves registration payment manually and sends confirmation."""
    reg = db.query(models.EventRegistration).filter(
        models.EventRegistration.registration_id == registration_id
    ).first()

    if not reg:
        raise HTTPException(status_code=404, detail="Registration record not found.")

    if reg.payment_status == "APPROVED":
        return {
            "success": True,
            "message": "Already approved",
            "payment_status": "APPROVED",
            "registration_status": "CONFIRMED"
        }

    old_status = reg.payment_status
    note = (payload.admin_note or "").strip()

    reg.payment_status = "APPROVED"
    reg.registration_status = "CONFIRMED"
    reg.admin_note = note
    reg.approved_at = get_ist_time()
    reg.is_edit_locked = True

    db.commit()
    db.refresh(reg)

    client_ip = get_client_ip(request)
    audit = models.RegistrationAuditLog(
        registration_id=registration_id,
        action="APPROVED",
        old_data=json.dumps({"payment_status": old_status}),
        new_data=json.dumps({"payment_status": "APPROVED", "admin_note": reg.admin_note}),
        performed_by="admin",
        ip_address=client_ip
    )
    db.add(audit)
    db.commit()

    # Trigger approval email in background task
    background_tasks.add_task(send_email_background, reg.id, "payment_approved")

    return {
        "success": True,
        "message": "Payment verified and registration confirmed successfully",
        "admin_note": reg.admin_note,
        "payment_status": "APPROVED",
        "registration_status": "CONFIRMED"
    }

@app.post("/api/admin/reject/{registration_id}")
async def admin_reject_payment(
    registration_id: str,
    payload: schemas.AdminAction,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin_auth: str = Depends(verify_admin_token)
):
    """Rejects registration payment manually."""
    reg = db.query(models.EventRegistration).filter(
        models.EventRegistration.registration_id == registration_id
    ).first()

    if not reg:
        raise HTTPException(status_code=404, detail="Registration record not found.")

    old_status = reg.payment_status
    note = (payload.admin_note or "").strip()

    reg.payment_status = "REJECTED"
    reg.registration_status = "REJECTED"
    reg.admin_note = note
    reg.rejected_at = get_ist_time()
    reg.is_edit_locked = False

    db.commit()
    db.refresh(reg)

    client_ip = get_client_ip(request)
    audit = models.RegistrationAuditLog(
        registration_id=registration_id,
        action="REJECTED",
        old_data=json.dumps({"payment_status": old_status}),
        new_data=json.dumps({"payment_status": "REJECTED", "admin_note": reg.admin_note}),
        performed_by="admin",
        ip_address=client_ip
    )
    db.add(audit)
    db.commit()

    # Trigger rejection email in background task
    background_tasks.add_task(send_email_background, reg.id, "payment_rejected")

    return {
        "success": True,
        "message": "Registration rejected successfully",
        "admin_note": reg.admin_note,
        "payment_status": "REJECTED",
        "registration_status": "REJECTED"
    }

@app.post("/api/admin/needs-correction/{registration_id}")
async def admin_mark_correction(
    registration_id: str,
    payload: schemas.AdminAction,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin_auth: str = Depends(verify_admin_token)
):
    """Marks registration as needs correction, unlocking edits."""
    reg = db.query(models.EventRegistration).filter(
        models.EventRegistration.registration_id == registration_id
    ).first()

    if not reg:
        raise HTTPException(status_code=404, detail="Registration record not found.")

    old_status = reg.payment_status
    note = (payload.admin_note or "").strip()

    reg.payment_status = "NEEDS_CORRECTION"
    reg.admin_note = note
    reg.is_edit_locked = False

    db.commit()
    db.refresh(reg)

    client_ip = get_client_ip(request)
    audit = models.RegistrationAuditLog(
        registration_id=registration_id,
        action="NEEDS_CORRECTION",
        old_data=json.dumps({"payment_status": old_status}),
        new_data=json.dumps({"payment_status": "NEEDS_CORRECTION", "admin_note": reg.admin_note}),
        performed_by="admin",
        ip_address=client_ip
    )
    db.add(audit)
    db.commit()

    # Trigger correction email in background task
    background_tasks.add_task(send_email_background, reg.id, "needs_correction")

    return {
        "success": True,
        "message": "Registration marked as needing correction",
        "admin_note": reg.admin_note,
        "payment_status": "NEEDS_CORRECTION",
        "registration_status": reg.registration_status
    }

@app.post("/api/admin/lock-edit/{registration_id}")
async def admin_lock_edit(
    registration_id: str,
    request: Request,
    db: Session = Depends(get_db),
    admin_auth: str = Depends(verify_admin_token)
):
    """Manually lock editing of responses."""
    reg = db.query(models.EventRegistration).filter(
        models.EventRegistration.registration_id == registration_id
    ).first()

    if not reg:
        raise HTTPException(status_code=404, detail="Registration record not found.")

    reg.is_edit_locked = True
    
    client_ip = get_client_ip(request)
    audit = models.RegistrationAuditLog(
        registration_id=registration_id,
        action="LOCK_EDIT",
        new_data="Locked response editing manually",
        performed_by="admin",
        ip_address=client_ip
    )
    db.add(audit)
    db.commit()

    return {"success": True, "message": "Editing locked manually"}

@app.post("/api/admin/unlock-edit/{registration_id}")
async def admin_unlock_edit(
    registration_id: str,
    request: Request,
    db: Session = Depends(get_db),
    admin_auth: str = Depends(verify_admin_token)
):
    """Manually unlock editing of responses."""
    reg = db.query(models.EventRegistration).filter(
        models.EventRegistration.registration_id == registration_id
    ).first()

    if not reg:
        raise HTTPException(status_code=404, detail="Registration record not found.")

    reg.is_edit_locked = False
    
    client_ip = get_client_ip(request)
    audit = models.RegistrationAuditLog(
        registration_id=registration_id,
        action="UNLOCK_EDIT",
        new_data="Unlocked response editing manually",
        performed_by="admin",
        ip_address=client_ip
    )
    db.add(audit)
    db.commit()

    return {"success": True, "message": "Editing unlocked manually"}

@app.post("/api/admin/resend-email/{registration_id}")
async def admin_resend_email(
    registration_id: str,
    payload: schemas.AdminAction,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    admin_auth: str = Depends(verify_admin_token)
):
    """Triggers resend of the latest status email notifications in background."""
    reg = db.query(models.EventRegistration).filter(
        models.EventRegistration.registration_id == registration_id
    ).first()

    if not reg:
        raise HTTPException(status_code=404, detail="Registration record not found.")

    new_note = (payload.admin_note or "").strip()
    if new_note:
        reg.admin_note = new_note
        db.commit()
        db.refresh(reg)

    client_ip = get_client_ip(request)
    audit = models.RegistrationAuditLog(
        registration_id=registration_id,
        action="RESEND_EMAIL",
        new_data=json.dumps({"message": "Queued status email resend in background", "admin_note_used": reg.admin_note or ""}),
        performed_by="admin",
        ip_address=client_ip
    )
    db.add(audit)
    db.commit()

    background_tasks.add_task(send_email_background, reg.id, "resend_email")

    return {
        "success": True,
        "message": "Status email queued successfully",
        "admin_note": reg.admin_note or ""
    }

@app.get("/api/admin/export.csv")
async def admin_export_csv(
    search: Optional[str] = "",
    payment_status: Optional[str] = "",
    db: Session = Depends(get_db),
    admin_auth: str = Depends(verify_admin_token)
):
    """Exports filtered registrations as a CSV attachment file."""
    query = db.query(models.EventRegistration)

    if search:
        search_q = f"%{search.strip()}%"
        query = query.filter(
            (models.EventRegistration.registration_id.like(search_q)) |
            (models.EventRegistration.full_name.like(search_q)) |
            (models.EventRegistration.email.like(search_q)) |
            (models.EventRegistration.phone.like(search_q)) |
            (models.EventRegistration.upi_reference_id.like(search_q))
        )

    if payment_status:
        query = query.filter(models.EventRegistration.payment_status == payment_status)

    records = query.order_by(desc(models.EventRegistration.created_at)).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Registration ID", "Response Number", "Full Name", "Email", "Phone",
        "College", "Department", "Year", "Roll Number", "Event Name", "Fee Paid",
        "UPI Reference / UTR", "Payment Status", "Registration Status", "Edit Count",
        "Submitted At"
    ])

    for r in records:
        writer.writerow([
            r.registration_id, r.response_number, r.full_name, r.email, r.phone,
            r.college, r.department, r.year, r.roll_number or "N/A", r.event_name, r.amount,
            r.upi_reference_id, r.payment_status, r.registration_status, r.edit_count,
            r.created_at.strftime("%Y-%m-%d %H:%M:%S")
        ])

    csv_data = output.getvalue()
    output.close()

    headers = {
        "Content-Disposition": "attachment; filename=registrations_export.csv",
        "Content-type": "text/csv"
    }
    return Response(content=csv_data, headers=headers)

# --- RESPONSE ANALYTICS ROUTING AND AGGREGATIONS ---

def apply_analytics_filters(query, model, days: Optional[str] = None, payment_status: Optional[str] = None, department: Optional[str] = None):
    if days and days != "all":
        try:
            days_int = int(days)
            start_date = get_ist_time() - datetime.timedelta(days=days_int)
            query = query.filter(model.created_at >= start_date)
        except ValueError:
            pass
    if payment_status and payment_status != "all":
        query = query.filter(model.payment_status == payment_status)
    if department and department != "all":
        query = query.filter(model.department == department)
    return query

def get_analytics_summary_data(db: Session, days: Optional[str] = None, payment_status: Optional[str] = None, department: Optional[str] = None):
    q = db.query(models.EventRegistration)
    q = apply_analytics_filters(q, models.EventRegistration, days, payment_status, department)
    
    total = q.count()
    if total == 0:
        return {
            "total_registrations": 0,
            "pending_review": 0,
            "approved": 0,
            "rejected": 0,
            "needs_correction": 0,
            "today_submissions": 0,
            "total_expected_amount": 0,
            "approved_amount": 0,
            "pending_amount": 0,
            "rejected_amount": 0,
            "approval_rate": 0.0,
            "pending_rate": 0.0,
            "rejection_rate": 0.0
        }

    pending = q.filter(models.EventRegistration.payment_status == "PENDING_REVIEW").count()
    approved = q.filter(models.EventRegistration.payment_status == "APPROVED").count()
    rejected = q.filter(models.EventRegistration.payment_status == "REJECTED").count()
    needs_correction = q.filter(models.EventRegistration.payment_status == "NEEDS_CORRECTION").count()
    
    today_start = get_ist_time().replace(hour=0, minute=0, second=0, microsecond=0)
    today_submissions = q.filter(models.EventRegistration.created_at >= today_start).count()
    
    total_expected_amount = db.query(func.coalesce(func.sum(models.EventRegistration.amount), 0)).filter(
        models.EventRegistration.id.in_(q.with_entities(models.EventRegistration.id))
    ).scalar()
    
    approved_amount = db.query(func.coalesce(func.sum(models.EventRegistration.amount), 0)).filter(
        models.EventRegistration.id.in_(q.with_entities(models.EventRegistration.id)),
        models.EventRegistration.payment_status == "APPROVED"
    ).scalar()
    
    pending_amount = db.query(func.coalesce(func.sum(models.EventRegistration.amount), 0)).filter(
        models.EventRegistration.id.in_(q.with_entities(models.EventRegistration.id)),
        models.EventRegistration.payment_status == "PENDING_REVIEW"
    ).scalar()
    
    rejected_amount = db.query(func.coalesce(func.sum(models.EventRegistration.amount), 0)).filter(
        models.EventRegistration.id.in_(q.with_entities(models.EventRegistration.id)),
        models.EventRegistration.payment_status == "REJECTED"
    ).scalar()
    
    return {
        "total_registrations": total,
        "pending_review": pending,
        "approved": approved,
        "rejected": rejected,
        "needs_correction": needs_correction,
        "today_submissions": today_submissions,
        "total_expected_amount": int(total_expected_amount),
        "approved_amount": int(approved_amount),
        "pending_amount": int(pending_amount),
        "rejected_amount": int(rejected_amount),
        "approval_rate": round((approved / total * 100), 2),
        "pending_rate": round((pending / total * 100), 2),
        "rejection_rate": round((rejected / total * 100), 2)
    }

def get_status_distribution_data(db: Session, days: Optional[str] = None, payment_status: Optional[str] = None, department: Optional[str] = None):
    q = db.query(
        models.EventRegistration.payment_status,
        func.count(models.EventRegistration.id).label("count")
    )
    q = apply_analytics_filters(q, models.EventRegistration, days, payment_status, department)
    q = q.group_by(models.EventRegistration.payment_status).all()
    
    labels_map = {
        "PENDING_REVIEW": "Pending Review",
        "APPROVED": "Approved",
        "REJECTED": "Rejected",
        "NEEDS_CORRECTION": "Needs Correction"
    }
    
    counts_map = {k: 0 for k in labels_map.keys()}
    total = 0
    for row in q:
        if row.payment_status in counts_map:
            counts_map[row.payment_status] = row.count
            total += row.count
            
    res = []
    for k, v in counts_map.items():
        res.append({
            "status": k,
            "label": labels_map[k],
            "count": v,
            "percentage": round((v / total * 100), 2) if total > 0 else 0.0
        })
    return res

def get_registration_status_data(db: Session, days: Optional[str] = None, payment_status: Optional[str] = None, department: Optional[str] = None):
    q = db.query(
        models.EventRegistration.registration_status,
        func.count(models.EventRegistration.id).label("count")
    )
    q = apply_analytics_filters(q, models.EventRegistration, days, payment_status, department)
    q = q.group_by(models.EventRegistration.registration_status).all()
    
    labels_map = {
        "SUBMITTED": "Submitted",
        "UPDATED": "Updated",
        "CONFIRMED": "Confirmed",
        "REJECTED": "Rejected",
        "CANCELLED": "Cancelled"
    }
    
    counts_map = {k: 0 for k in labels_map.keys()}
    total = 0
    for row in q:
        status_key = row.registration_status or "SUBMITTED"
        if status_key in counts_map:
            counts_map[status_key] = row.count
            total += row.count
        else:
            counts_map[status_key] = row.count
            total += row.count
            labels_map[status_key] = status_key.replace("_", " ").title()
            
    res = []
    for k, v in counts_map.items():
        res.append({
            "status": k,
            "label": labels_map.get(k, k),
            "count": v,
            "percentage": round((v / total * 100), 2) if total > 0 else 0.0
        })
    return res

def get_department_distribution_data(db: Session, days: Optional[str] = None, payment_status: Optional[str] = None, department: Optional[str] = None):
    dept_expr = func.coalesce(func.nullif(func.trim(models.EventRegistration.department), ""), "Not Provided")
    q = db.query(
        dept_expr.label("dept"),
        func.count(models.EventRegistration.id).label("count")
    )
    q = apply_analytics_filters(q, models.EventRegistration, days, payment_status, department)
    q = q.group_by(dept_expr).order_by(desc("count")).all()
    
    total = sum(row.count for row in q)
    res = []
    for row in q:
        res.append({
            "department": row.dept,
            "label": row.dept,
            "count": row.count,
            "percentage": round((row.count / total * 100), 2) if total > 0 else 0.0
        })
    return res

def get_year_distribution_data(db: Session, days: Optional[str] = None, payment_status: Optional[str] = None, department: Optional[str] = None):
    year_expr = func.coalesce(func.nullif(func.trim(models.EventRegistration.year), ""), "Not Provided")
    q = db.query(
        year_expr.label("year_label"),
        func.count(models.EventRegistration.id).label("count")
    )
    q = apply_analytics_filters(q, models.EventRegistration, days, payment_status, department)
    q = q.group_by(year_expr).order_by(desc("count")).all()
    
    total = sum(row.count for row in q)
    res = []
    for row in q:
        res.append({
            "year": row.year_label,
            "label": row.year_label,
            "count": row.count,
            "percentage": round((row.count / total * 100), 2) if total > 0 else 0.0
        })
    return res

def get_daily_submissions_data(db: Session, days: Optional[str] = None, payment_status: Optional[str] = None, department: Optional[str] = None):
    days_limit = 14
    if days and days != "all":
        try:
            days_limit = int(days)
        except ValueError:
            pass

    today = datetime.date.today()
    if days == "all":
        min_date_row = db.query(func.min(func.date(models.EventRegistration.created_at))).scalar()
        if min_date_row:
            if isinstance(min_date_row, str):
                min_date = datetime.datetime.strptime(min_date_row, "%Y-%m-%d").date()
            else:
                min_date = min_date_row
            days_limit = (today - min_date).days + 1
            if days_limit < 1:
                days_limit = 1
        else:
            days_limit = 30

    date_list = [today - datetime.timedelta(days=x) for x in range(days_limit)]
    date_list.reverse()

    daily_counts = {d.strftime("%Y-%m-%d"): 0 for d in date_list}

    q = db.query(
        func.date(models.EventRegistration.created_at).label("date"),
        func.count(models.EventRegistration.id).label("count")
    )
    if days and days != "all":
        start_date = get_ist_time() - datetime.timedelta(days=days_limit)
        q = q.filter(models.EventRegistration.created_at >= start_date)

    if payment_status and payment_status != "all":
        q = q.filter(models.EventRegistration.payment_status == payment_status)
    if department and department != "all":
        q = q.filter(models.EventRegistration.department == department)

    q = q.group_by(func.date(models.EventRegistration.created_at)).all()

    for row in q:
        date_str = str(row.date)
        if date_str in daily_counts:
            daily_counts[date_str] = row.count
        elif days == "all":
            daily_counts[date_str] = row.count

    res = []
    for d_str, count in daily_counts.items():
        try:
            dt = datetime.datetime.strptime(d_str, "%Y-%m-%d")
            label = dt.strftime("%b %e").replace("  ", " ")
        except Exception:
            label = d_str
        res.append({
            "date": d_str,
            "label": label,
            "count": count
        })
    return res

def get_hourly_submissions_data(db: Session, days: Optional[str] = None, payment_status: Optional[str] = None, department: Optional[str] = None):
    hourly_counts = {h: 0 for h in range(24)}

    q = db.query(
        func.hour(models.EventRegistration.created_at).label("hour"),
        func.count(models.EventRegistration.id).label("count")
    )
    q = apply_analytics_filters(q, models.EventRegistration, days, payment_status, department)
    q = q.group_by(func.hour(models.EventRegistration.created_at)).all()

    for row in q:
        if row.hour is not None:
            hourly_counts[int(row.hour)] = row.count

    res = []
    for h in range(24):
        label = f"{h:02d}:00"
        res.append({
            "hour": h,
            "label": label,
            "count": hourly_counts[h]
        })
    return res

def get_payment_amounts_data(db: Session, days: Optional[str] = None, payment_status: Optional[str] = None, department: Optional[str] = None):
    q = db.query(
        models.EventRegistration.payment_status,
        func.coalesce(func.sum(models.EventRegistration.amount), 0).label("amount")
    )
    q = apply_analytics_filters(q, models.EventRegistration, days, payment_status, department)
    q = q.group_by(models.EventRegistration.payment_status).all()

    labels_map = {
        "APPROVED": "Approved",
        "PENDING_REVIEW": "Pending Review",
        "REJECTED": "Rejected",
        "NEEDS_CORRECTION": "Needs Correction"
    }

    amounts_map = {k: 0 for k in labels_map.keys()}
    for row in q:
        if row.payment_status in amounts_map:
            amounts_map[row.payment_status] = int(row.amount)

    res = []
    for k, v in amounts_map.items():
        res.append({
            "status": k,
            "label": labels_map[k],
            "amount": v
        })
    return res

def get_top_colleges_data(db: Session, days: Optional[str] = None, payment_status: Optional[str] = None, department: Optional[str] = None, limit: int = 10):
    college_expr = func.coalesce(func.nullif(func.trim(models.EventRegistration.college), ""), "Not Provided")
    q = db.query(
        college_expr.label("college_label"),
        func.count(models.EventRegistration.id).label("count")
    )
    q = apply_analytics_filters(q, models.EventRegistration, days, payment_status, department)
    q = q.group_by(college_expr).order_by(desc("count")).limit(limit).all()

    res = []
    for row in q:
        res.append({
            "college": row.college_label,
            "label": row.college_label,
            "count": row.count
        })
    return res

def get_edit_activity_data(db: Session, days: Optional[str] = None, payment_status: Optional[str] = None, department: Optional[str] = None):
    bucket_expr = case(
        (models.EventRegistration.edit_count == 0, "Never Edited"),
        (models.EventRegistration.edit_count == 1, "Edited Once"),
        else_="Edited Multiple Times"
    )
    q = db.query(
        bucket_expr.label("bucket"),
        func.count(models.EventRegistration.id).label("count")
    )
    q = apply_analytics_filters(q, models.EventRegistration, days, payment_status, department)
    q = q.group_by(bucket_expr).all()

    edit_activity_counts = {
        "Never Edited": 0,
        "Edited Once": 0,
        "Edited Multiple Times": 0
    }
    for row in q:
        if row.bucket in edit_activity_counts:
            edit_activity_counts[row.bucket] = row.count

    res = []
    for b, count in edit_activity_counts.items():
        res.append({
            "bucket": b,
            "label": b,
            "count": count
        })
    return res

def get_email_status_data(db: Session, days: Optional[str] = None, payment_status: Optional[str] = None, department: Optional[str] = None):
    q = db.query(
        func.coalesce(models.EventRegistration.email_status, "NOT_SENT").label("status"),
        func.count(models.EventRegistration.id).label("count")
    )
    q = apply_analytics_filters(q, models.EventRegistration, days, payment_status, department)
    q = q.group_by(func.coalesce(models.EventRegistration.email_status, "NOT_SENT")).all()

    total = sum(row.count for row in q)
    res = []
    for row in q:
        label_val = row.status.replace("_", " ").title()
        res.append({
            "status": row.status,
            "label": label_val,
            "count": row.count,
            "percentage": round((row.count / total * 100), 2) if total > 0 else 0.0
        })
    return res

def get_submission_quality_data(db: Session, days: Optional[str] = None, payment_status: Optional[str] = None, department: Optional[str] = None):
    base_q = db.query(models.EventRegistration.id)
    base_q = apply_analytics_filters(base_q, models.EventRegistration, days, payment_status, department)
    filtered_ids = base_q.all()
    id_list = [r[0] for r in filtered_ids]

    if not id_list:
        return {
            "with_screenshot": 0,
            "without_screenshot": 0,
            "missing_college": 0,
            "missing_department": 0,
            "duplicate_email_count": 0
        }

    q = db.query(models.EventRegistration).filter(models.EventRegistration.id.in_(id_list))
    
    with_screenshot = q.filter(models.EventRegistration.payment_screenshot_filename.isnot(None)).count()
    without_screenshot = q.filter(models.EventRegistration.payment_screenshot_filename.is_(None)).count()
    
    missing_college = q.filter(
        (models.EventRegistration.college.is_(None)) | 
        (func.trim(models.EventRegistration.college) == "")
    ).count()
    
    missing_department = q.filter(
        (models.EventRegistration.department.is_(None)) | 
        (func.trim(models.EventRegistration.department) == "")
    ).count()

    email_query = db.query(models.EventRegistration.email).filter(
        models.EventRegistration.id.in_(id_list)
    ).group_by(models.EventRegistration.email).having(func.count(models.EventRegistration.id) > 1)
    
    duplicate_email_count = db.query(func.count(models.EventRegistration.id)).filter(
        models.EventRegistration.id.in_(id_list),
        models.EventRegistration.email.in_(email_query)
    ).scalar() or 0

    return {
        "with_screenshot": with_screenshot,
        "without_screenshot": without_screenshot,
        "missing_college": missing_college,
        "missing_department": missing_department,
        "duplicate_email_count": int(duplicate_email_count)
    }

def get_recent_activity_data(db: Session, days: Optional[str] = None, payment_status: Optional[str] = None, department: Optional[str] = None):
    reg_subquery = db.query(models.EventRegistration.registration_id)
    reg_subquery = apply_analytics_filters(reg_subquery, models.EventRegistration, days, payment_status, department).subquery()

    q = db.query(
        models.RegistrationAuditLog.created_at,
        models.RegistrationAuditLog.action,
        models.RegistrationAuditLog.registration_id,
        models.EventRegistration.full_name
    ).join(
        models.EventRegistration,
        models.EventRegistration.registration_id == models.RegistrationAuditLog.registration_id,
        isouter=True
    ).join(
        reg_subquery,
        reg_subquery.c.registration_id == models.RegistrationAuditLog.registration_id
    ).order_by(desc(models.RegistrationAuditLog.created_at)).limit(10).all()

    res = []
    for row in q:
        name = row.full_name or "Unknown User"
        action = row.action
        msg = f"Registration {row.registration_id} was {action.lower()}"
        if action == "SUBMITTED":
            msg = f"New registration submitted by {name}"
        elif action == "EDITED":
            msg = f"Registration details updated by {name}"
        elif action == "APPROVED":
            msg = f"Payment approved by admin for {name}"
        elif action == "REJECTED":
            msg = f"Registration rejected by admin for {name}"
        elif action == "NEEDS_CORRECTION":
            msg = f"Registration marked for correction by admin for {name}"

        res.append({
            "time": row.created_at.strftime("%Y-%m-%d %H:%M"),
            "type": row.action,
            "registration_id": row.registration_id,
            "name": name,
            "message": msg
        })
    return res

@app.get("/api/admin/analytics/summary")
async def get_analytics_summary(
    days: Optional[str] = None,
    payment_status: Optional[str] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    admin_auth: str = Depends(verify_admin_token)
):
    summary = get_analytics_summary_data(db, days, payment_status, department)
    return {"success": True, "summary": summary}

@app.get("/api/admin/analytics/status-distribution")
async def get_status_distribution(
    days: Optional[str] = None,
    payment_status: Optional[str] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    admin_auth: str = Depends(verify_admin_token)
):
    data = get_status_distribution_data(db, days, payment_status, department)
    return {"success": True, "data": data}

@app.get("/api/admin/analytics/registration-status")
async def get_registration_status(
    days: Optional[str] = None,
    payment_status: Optional[str] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    admin_auth: str = Depends(verify_admin_token)
):
    data = get_registration_status_data(db, days, payment_status, department)
    return {"success": True, "data": data}

@app.get("/api/admin/analytics/department-distribution")
async def get_department_distribution(
    days: Optional[str] = None,
    payment_status: Optional[str] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    admin_auth: str = Depends(verify_admin_token)
):
    data = get_department_distribution_data(db, days, payment_status, department)
    return {"success": True, "data": data}

@app.get("/api/admin/analytics/year-distribution")
async def get_year_distribution(
    days: Optional[str] = None,
    payment_status: Optional[str] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    admin_auth: str = Depends(verify_admin_token)
):
    data = get_year_distribution_data(db, days, payment_status, department)
    return {"success": True, "data": data}

@app.get("/api/admin/analytics/daily-submissions")
async def get_daily_submissions(
    days: Optional[str] = "14",
    payment_status: Optional[str] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    admin_auth: str = Depends(verify_admin_token)
):
    data = get_daily_submissions_data(db, days, payment_status, department)
    return {"success": True, "data": data}

@app.get("/api/admin/analytics/hourly-submissions")
async def get_hourly_submissions(
    days: Optional[str] = None,
    payment_status: Optional[str] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    admin_auth: str = Depends(verify_admin_token)
):
    data = get_hourly_submissions_data(db, days, payment_status, department)
    return {"success": True, "data": data}

@app.get("/api/admin/analytics/payment-amounts")
async def get_payment_amounts(
    days: Optional[str] = None,
    payment_status: Optional[str] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    admin_auth: str = Depends(verify_admin_token)
):
    data = get_payment_amounts_data(db, days, payment_status, department)
    return {"success": True, "data": data}

@app.get("/api/admin/analytics/top-colleges")
async def get_top_colleges(
    days: Optional[str] = None,
    payment_status: Optional[str] = None,
    department: Optional[str] = None,
    limit: int = 10,
    db: Session = Depends(get_db),
    admin_auth: str = Depends(verify_admin_token)
):
    data = get_top_colleges_data(db, days, payment_status, department, limit)
    return {"success": True, "data": data}

@app.get("/api/admin/analytics/edit-activity")
async def get_edit_activity(
    days: Optional[str] = None,
    payment_status: Optional[str] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    admin_auth: str = Depends(verify_admin_token)
):
    data = get_edit_activity_data(db, days, payment_status, department)
    return {"success": True, "data": data}

@app.get("/api/admin/analytics/email-status")
async def get_email_status(
    days: Optional[str] = None,
    payment_status: Optional[str] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    admin_auth: str = Depends(verify_admin_token)
):
    data = get_email_status_data(db, days, payment_status, department)
    return {"success": True, "data": data}

@app.get("/api/admin/analytics/submission-quality")
async def get_submission_quality(
    days: Optional[str] = None,
    payment_status: Optional[str] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    admin_auth: str = Depends(verify_admin_token)
):
    data = get_submission_quality_data(db, days, payment_status, department)
    return {"success": True, "data": data}

@app.get("/api/admin/analytics/recent-activity")
async def get_recent_activity(
    days: Optional[str] = None,
    payment_status: Optional[str] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    admin_auth: str = Depends(verify_admin_token)
):
    data = get_recent_activity_data(db, days, payment_status, department)
    return {"success": True, "data": data}

@app.get("/api/admin/analytics/all")
async def get_all_analytics(
    days: Optional[str] = None,
    payment_status: Optional[str] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    admin_auth: str = Depends(verify_admin_token)
):
    summary = get_analytics_summary_data(db, days, payment_status, department)
    status_dist = get_status_distribution_data(db, days, payment_status, department)
    reg_status = get_registration_status_data(db, days, payment_status, department)
    departments_dist = get_department_distribution_data(db, days, payment_status, department)
    years_dist = get_year_distribution_data(db, days, payment_status, department)
    daily_subs = get_daily_submissions_data(db, days, payment_status, department)
    hourly_subs = get_hourly_submissions_data(db, days, payment_status, department)
    pmt_amts = get_payment_amounts_data(db, days, payment_status, department)
    top_colleges_list = get_top_colleges_data(db, days, payment_status, department, limit=10)
    edit_act = get_edit_activity_data(db, days, payment_status, department)
    email_stat = get_email_status_data(db, days, payment_status, department)
    sub_quality = get_submission_quality_data(db, days, payment_status, department)
    recent_act = get_recent_activity_data(db, days, payment_status, department)
    
    all_depts_q = db.query(models.EventRegistration.department).distinct().all()
    unique_departments = sorted(list(set(d[0].strip() for d in all_depts_q if d[0] and d[0].strip())))

    return {
        "success": True,
        "summary": summary,
        "payment_status": status_dist,
        "registration_status": reg_status,
        "departments": departments_dist,
        "years": years_dist,
        "daily_submissions": daily_subs,
        "hourly_submissions": hourly_subs,
        "payment_amounts": pmt_amts,
        "top_colleges": top_colleges_list,
        "edit_activity": edit_act,
        "email_status": email_stat,
        "submission_quality": sub_quality,
        "recent_activity": recent_act,
        "unique_departments": unique_departments
    }

@app.get("/api/admin/analytics/export.csv")
async def get_analytics_csv(
    days: Optional[str] = None,
    payment_status: Optional[str] = None,
    department: Optional[str] = None,
    db: Session = Depends(get_db),
    admin_auth: str = Depends(verify_admin_token)
):
    summary = get_analytics_summary_data(db, days, payment_status, department)
    status_dist = get_status_distribution_data(db, days, payment_status, department)
    reg_status = get_registration_status_data(db, days, payment_status, department)
    departments_dist = get_department_distribution_data(db, days, payment_status, department)
    years_dist = get_year_distribution_data(db, days, payment_status, department)
    daily_subs = get_daily_submissions_data(db, days, payment_status, department)
    top_colleges_list = get_top_colleges_data(db, days, payment_status, department, limit=10)
    email_stat = get_email_status_data(db, days, payment_status, department)

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["=== RESPONSE ANALYTICS SUMMARY ==="])
    writer.writerow(["Metric", "Value"])
    writer.writerow(["Total Registrations", summary["total_registrations"]])
    writer.writerow(["Pending Review", summary["pending_review"]])
    writer.writerow(["Approved", summary["approved"]])
    writer.writerow(["Rejected", summary["rejected"]])
    writer.writerow(["Needs Correction", summary["needs_correction"]])
    writer.writerow(["Today's Submissions", summary["today_submissions"]])
    writer.writerow(["Total Expected Amount", f"Rs. {summary['total_expected_amount']}"])
    writer.writerow(["Approved Amount", f"Rs. {summary['approved_amount']}"])
    writer.writerow(["Pending Amount", f"Rs. {summary['pending_amount']}"])
    writer.writerow(["Rejected Amount", f"Rs. {summary['rejected_amount']}"])
    writer.writerow(["Approval Rate", f"{summary['approval_rate']}%"])
    writer.writerow(["Pending Rate", f"{summary['pending_rate']}%"])
    writer.writerow(["Rejection Rate", f"{summary['rejection_rate']}%"])
    writer.writerow([])

    writer.writerow(["=== PAYMENT STATUS DISTRIBUTION ==="])
    writer.writerow(["Status", "Label", "Count", "Percentage"])
    for row in status_dist:
        writer.writerow([row["status"], row["label"], row["count"], f"{row['percentage']}%"])
    writer.writerow([])

    writer.writerow(["=== REGISTRATION PROGRESS ==="])
    writer.writerow(["Status", "Label", "Count", "Percentage"])
    for row in reg_status:
        writer.writerow([row["status"], row["label"], row["count"], f"{row['percentage']}%"])
    writer.writerow([])

    writer.writerow(["=== DEPARTMENT DISTRIBUTION ==="])
    writer.writerow(["Department", "Count", "Percentage"])
    for row in departments_dist:
        writer.writerow([row["department"], row["count"], f"{row['percentage']}%"])
    writer.writerow([])

    writer.writerow(["=== ACADEMIC YEAR DISTRIBUTION ==="])
    writer.writerow(["Year", "Count", "Percentage"])
    for row in years_dist:
        writer.writerow([row["year"], row["count"], f"{row['percentage']}%"])
    writer.writerow([])

    writer.writerow(["=== DAILY RESPONSE TREND ==="])
    writer.writerow(["Date", "Label", "Count"])
    for row in daily_subs:
        writer.writerow([row["date"], row["label"], row["count"]])
    writer.writerow([])

    writer.writerow(["=== TOP COLLEGES ==="])
    writer.writerow(["College", "Count"])
    for row in top_colleges_list:
        writer.writerow([row["college"], row["count"]])
    writer.writerow([])

    writer.writerow(["=== EMAIL DELIVERY STATUS ==="])
    writer.writerow(["Status", "Label", "Count", "Percentage"])
    for row in email_stat:
        writer.writerow([row["status"], row["label"], row["count"], f"{row['percentage']}%"])

    csv_data = output.getvalue()
    output.close()

    date_str = datetime.date.today().strftime("%Y-%m-%d")
    headers = {
        "Content-Disposition": f"attachment; filename=analytics-summary-{date_str}.csv",
        "Content-type": "text/csv"
    }
    return Response(content=csv_data, headers=headers)

