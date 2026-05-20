import os
import csv
import io
import json
import datetime
from typing import Optional
from fastapi import FastAPI, Depends, Request, HTTPException, status, Response, Form, File, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import case, desc

import config
import models
import schemas
import security
import email_service
from database import engine, get_db, SessionLocal
from utils import generate_registration_id, generate_secure_token, escape_html

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
    user_agent = request.headers.get("user-agent", "Unknown")
    ip_address = get_client_ip(request)
    print(f"Global exception: {exc}")
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
            "message": "An unexpected server error occurred.",
            "code": "INTERNAL_SERVER_ERROR"
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
    return {"status": "ok", "service": "event-registration-fastapi"}

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

    upi_reference_id = upi_reference_id.strip().upper()
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
        return JSONResponse(status_code=400, content={"success": False, "message": "This transaction reference ID has already been submitted."})

    # Duplicate Email check if restricted
    if not config.ALLOW_DUPLICATE_EMAIL:
        duplicate_email = db.query(models.EventRegistration).filter(
            models.EventRegistration.email == email
        ).first()
        if duplicate_email:
            return JSONResponse(status_code=400, content={"success": False, "message": "This email address is already registered."})

    # Validate payment screenshot file
    if not payment_screenshot or not payment_screenshot.filename:
        return JSONResponse(status_code=400, content={"success": False, "message": "Payment screenshot is required."})

    contents = await payment_screenshot.read()
    file_size = len(contents)
    if file_size == 0:
        return JSONResponse(status_code=400, content={"success": False, "message": "Payment screenshot is required."})

    filename = payment_screenshot.filename
    content_type = payment_screenshot.content_type

    ext = os.path.splitext(filename)[1].lower()
    allowed_exts = {".jpg", ".jpeg", ".png", ".webp"}
    if ext not in allowed_exts:
        return JSONResponse(status_code=400, content={"success": False, "message": "Screenshot file must be JPG, PNG, or WEBP."})

    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    if content_type not in allowed_types:
        return JSONResponse(status_code=400, content={"success": False, "message": "Screenshot file must be JPG, PNG, or WEBP."})

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
    db.commit()
    db.refresh(registration)

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

    # Trigger Resend Email automation
    email_sent = email_service.send_submission_received_email(registration, db)
    registration.email_status = "SENT" if email_sent else "FAILED"
    db.commit()

    return {
        "success": True,
        "registration_id": reg_id,
        "view_token": registration.view_token,
        "edit_token": registration.edit_token,
        "status_token": registration.status_token,
        "redirect_url": f"{config.FRONTEND_URL}/thank-you.html?rid={reg_id}&token={registration.status_token}"
    }

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

    if reg.edit_token_expires_at and reg.edit_token_expires_at < datetime.datetime.utcnow():
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
    reg.last_edited_at = datetime.datetime.utcnow()

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

    # Trigger details updated email
    email_sent = email_service.send_details_updated_email(reg, db)
    reg.email_status = "SENT" if email_sent else "FAILED"
    db.commit()

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
    db: Session = Depends(get_db),
    admin_auth: str = Depends(verify_admin_token)
):
    """Retrieve administrative list of registrations with statistics."""
    total = db.query(models.EventRegistration).count()
    pending = db.query(models.EventRegistration).filter(models.EventRegistration.payment_status == "PENDING_REVIEW").count()
    approved = db.query(models.EventRegistration).filter(models.EventRegistration.payment_status == "APPROVED").count()
    rejected = db.query(models.EventRegistration).filter(models.EventRegistration.payment_status == "REJECTED").count()
    correction = db.query(models.EventRegistration).filter(models.EventRegistration.payment_status == "NEEDS_CORRECTION").count()
    
    today_start = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
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

    ordered_query = query.order_by(
        case(
            (models.EventRegistration.payment_status == "PENDING_REVIEW", 1),
            else_=2
        ),
        desc(models.EventRegistration.created_at)
    )

    records = ordered_query.all()
    
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
        "registrations": registrations_data
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
        return {"success": True, "message": "Already approved"}

    old_status = reg.payment_status
    reg.payment_status = "APPROVED"
    reg.registration_status = "CONFIRMED"
    reg.approved_at = datetime.datetime.utcnow()
    reg.is_edit_locked = True
    
    if payload.admin_note is not None:
        reg.admin_note = payload.admin_note.strip()

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

    email_sent = email_service.send_payment_approved_email(reg, db)
    reg.email_status = "SENT" if email_sent else "FAILED"
    db.commit()

    return {"success": True, "message": "Payment verified and registration confirmed successfully"}

@app.post("/api/admin/reject/{registration_id}")
async def admin_reject_payment(
    registration_id: str,
    payload: schemas.AdminAction,
    request: Request,
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
    reg.payment_status = "REJECTED"
    reg.registration_status = "REJECTED"
    reg.rejected_at = datetime.datetime.utcnow()
    reg.is_edit_locked = False
    
    if payload.admin_note:
        reg.admin_note = payload.admin_note.strip()

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

    email_sent = email_service.send_payment_rejected_email(reg, db)
    reg.email_status = "SENT" if email_sent else "FAILED"
    db.commit()

    return {"success": True, "message": "Registration rejected successfully"}

@app.post("/api/admin/needs-correction/{registration_id}")
async def admin_mark_correction(
    registration_id: str,
    payload: schemas.AdminAction,
    request: Request,
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
    reg.payment_status = "NEEDS_CORRECTION"
    reg.is_edit_locked = False
    
    if payload.admin_note:
        reg.admin_note = payload.admin_note.strip()

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

    email_sent = email_service.send_needs_correction_email(reg, db)
    reg.email_status = "SENT" if email_sent else "FAILED"
    db.commit()

    return {"success": True, "message": "Registration marked as needing correction"}

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
    request: Request,
    db: Session = Depends(get_db),
    admin_auth: str = Depends(verify_admin_token)
):
    """Triggers resend of the latest status email notifications."""
    reg = db.query(models.EventRegistration).filter(
        models.EventRegistration.registration_id == registration_id
    ).first()

    if not reg:
        raise HTTPException(status_code=404, detail="Registration record not found.")

    email_sent = email_service.send_latest_status_email(reg, db)
    
    client_ip = get_client_ip(request)
    audit = models.RegistrationAuditLog(
        registration_id=registration_id,
        action="RESEND_EMAIL",
        new_data=f"Resent latest status email. Delivery Status: {'Success' if email_sent else 'Failed'}",
        performed_by="admin",
        ip_address=client_ip
    )
    db.add(audit)
    
    reg.email_status = "SENT" if email_sent else "FAILED"
    db.commit()

    if not email_sent:
        raise HTTPException(status_code=500, detail="Failed to send email. Check API key status.")

    return {"success": True, "message": "Status email notification resent successfully"}

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
