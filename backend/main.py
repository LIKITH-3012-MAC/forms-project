import os
import csv
import io
import json
import datetime
from typing import Optional
from fastapi import FastAPI, Depends, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import case, desc

import config
import models
import schemas
import security
import email_service
import html_pages
from database import engine, get_db, SessionLocal
from utils import generate_registration_id, generate_secure_token, escape_html

# Initialize tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title=config.APP_NAME)

# Mount static folder
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# Helper: Check deadline status
def is_deadline_passed() -> bool:
    try:
        deadline_dt = datetime.datetime.strptime(config.EVENT_DEADLINE, "%Y-%m-%d %H:%M:%S")
        return datetime.datetime.now() > deadline_dt
    except Exception as e:
        # Fallback to false if parsing fails
        print(f"Deadline date parsing failed: {e}")
        return False


# Helper: Check admin session
def is_admin_session_valid(request: Request) -> bool:
    cookie = request.cookies.get("admin_session")
    if not cookie:
        return False
    user_id = security.verify_session(cookie)
    return user_id == "admin_authenticated"


# Helper: Get current client IP
def get_client_ip(request: Request) -> str:
    # Handle proxy headers if deployed (e.g. Render/Cloudflare)
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


# 1. 404 handler:
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    user_agent = request.headers.get("user-agent", "Unknown")
    ip_address = get_client_ip(request)
    path = str(request.url.path)
    reason = "Page not found"
    details = "The page you tried to open does not exist or is not available directly."
    
    log_problem_to_db(
        path=path,
        reason=reason,
        details=details,
        user_agent=user_agent,
        ip_address=ip_address,
        exception_type="404 NotFound"
    )
    return HTMLResponse(
        content=html_pages.render_problem_html(reason=reason, details=details),
        status_code=404
    )


# 2. 500 handler:
@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    user_agent = request.headers.get("user-agent", "Unknown")
    ip_address = get_client_ip(request)
    path = str(request.url.path)
    reason = "Server issue"
    details = "Something went wrong while processing your request."
    
    exception_type = type(exc).__name__ if exc else "500 InternalServerError"
    
    log_problem_to_db(
        path=path,
        reason=reason,
        details=details,
        user_agent=user_agent,
        ip_address=ip_address,
        exception_type=exception_type
    )
    return HTMLResponse(
        content=html_pages.render_problem_html(reason=reason, details=details),
        status_code=500
    )


# 3. generic Exception handler:
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    user_agent = request.headers.get("user-agent", "Unknown")
    ip_address = get_client_ip(request)
    path = str(request.url.path)
    reason = "Unexpected issue"
    details = "An unexpected issue occurred. Please try again or contact support."
    
    print(f"INTERNAL ERROR EXCEPTION: {exc}", flush=True)
    import traceback
    traceback.print_exc()
    
    log_problem_to_db(
        path=path,
        reason=reason,
        details=details,
        user_agent=user_agent,
        ip_address=ip_address,
        exception_type=type(exc).__name__
    )
    return HTMLResponse(
        content=html_pages.render_problem_html(reason=reason, details=details),
        status_code=500
    )


# 4. HTTPException handler:
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api"):
        return Response(
            content=json.dumps({"detail": exc.detail}),
            status_code=exc.status_code,
            media_type="application/json"
        )
        
    user_agent = request.headers.get("user-agent", "Unknown")
    ip_address = get_client_ip(request)
    path = str(request.url.path)
    
    reason = f"HTTP Error {exc.status_code}"
    details = exc.detail
    
    log_problem_to_db(
        path=path,
        reason=reason,
        details=details,
        user_agent=user_agent,
        ip_address=ip_address,
        exception_type=f"HTTPException_{exc.status_code}"
    )
    
    return HTMLResponse(
        content=html_pages.render_problem_html(reason=reason, details=details),
        status_code=exc.status_code
    )


# --- MAIN USER ROUTES ---

@app.get("/")
async def root_redirect():
    """Redirect home page to registration form."""
    return RedirectResponse(url="/form", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/form", response_class=FileResponse)
async def serve_form_page():
    """Serve the static/form.html file."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    form_path = os.path.join(base_dir, "static", "form.html")
    form_path = os.path.normpath(form_path)
    if not os.path.exists(form_path):
        raise HTTPException(
            status_code=404, 
            detail="form.html not found. Please ensure static/form.html exists."
        )
    return FileResponse(form_path)


@app.get("/api/form-config")
async def get_form_config(db: Session = Depends(get_db)):
    """Return registration parameters and live seat info as JSON."""
    # Count approved seats
    approved_count = db.query(models.EventRegistration).filter(
        models.EventRegistration.payment_status == "APPROVED"
    ).count()

    seats_available = max(0, config.EVENT_SEATS_TOTAL - approved_count)
    deadline_passed = is_deadline_passed()
    
    # Form is enabled if deadline hasn't passed and seats are available
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
        "qr_image_url": "/static/payment-qr.png",
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
    payload: schemas.RegistrationCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Processes new registration submission."""
    # 1. Validate Form Constraints (Seats & Deadline)
    approved_count = db.query(models.EventRegistration).filter(
        models.EventRegistration.payment_status == "APPROVED"
    ).count()
    seats_available = config.EVENT_SEATS_TOTAL - approved_count
    if seats_available <= 0:
        raise HTTPException(status_code=400, detail="Registration seats are fully booked.")

    if is_deadline_passed():
        raise HTTPException(status_code=400, detail="Registration deadline has expired.")

    # 2. Duplicate UTR check
    duplicate_utr = db.query(models.EventRegistration).filter(
        models.EventRegistration.upi_reference_id == payload.upi_reference_id
    ).first()
    if duplicate_utr:
        raise HTTPException(status_code=400, detail="This transaction reference ID has already been submitted.")

    # 3. Duplicate Email check if restricted
    if not config.ALLOW_DUPLICATE_EMAIL:
        duplicate_email = db.query(models.EventRegistration).filter(
            models.EventRegistration.email == payload.email
        ).first()
        if duplicate_email:
            raise HTTPException(status_code=400, detail="This email address is already registered.")

    # 4. Generate metadata
    reg_id = generate_registration_id()
    while db.query(models.EventRegistration).filter(models.EventRegistration.registration_id == reg_id).first():
        reg_id = generate_registration_id() # Ensure uniqueness

    total_submissions = db.query(models.EventRegistration).count()
    response_num = total_submissions + 1

    # 5. Populate and write record (using config values for payment parameters to bypass client tampering)
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "Unknown")

    registration = models.EventRegistration(
        registration_id=reg_id,
        response_number=response_num,
        full_name=payload.full_name,
        email=payload.email,
        phone=payload.phone,
        college=payload.college,
        department=payload.department,
        year=payload.year,
        roll_number=payload.roll_number,
        event_name=config.EVENT_NAME,
        amount=config.EVENT_AMOUNT,
        upi_id=config.UPI_ID,
        upi_reference_id=payload.upi_reference_id,
        payment_screenshot_url=payload.payment_screenshot_url,
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

    # 6. Write Audit log
    audit_data = payload.model_dump()
    audit_data.pop("confirm", None) # remove confirm boolean from db dump
    audit_log = models.RegistrationAuditLog(
        registration_id=reg_id,
        action="SUBMITTED",
        new_data=json.dumps(audit_data),
        performed_by="user",
        ip_address=client_ip
    )
    db.add(audit_log)
    db.commit()

    # 7. Trigger Resend Email automation asynchronously (email failure shouldn't break DB insert)
    email_sent = email_service.send_submission_received_email(registration, db)
    if email_sent:
        registration.email_status = "SENT"
    else:
        registration.email_status = "FAILED"
    db.commit()

    return {
        "success": True,
        "message": "Response submitted successfully",
        "registration_id": reg_id,
        "redirect_url": f"/thank-you/{reg_id}?token={registration.status_token}"
    }


@app.get("/thank-you/{registration_id}", response_class=HTMLResponse)
async def thank_you_page(registration_id: str, token: str, db: Session = Depends(get_db)):
    """Render thank you HTML from backend string function."""
    reg = db.query(models.EventRegistration).filter(
        models.EventRegistration.registration_id == registration_id
    ).first()

    if not reg or reg.status_token != token:
        return RedirectResponse(
            url="/problem?reason=invalid_token&details=The%20token%20provided%20is%20invalid%20or%20does%20not%20match.",
            status_code=302
        )

    html_content = html_pages.render_thank_you_html(reg)
    return HTMLResponse(content=html_content)


@app.get("/r/{view_token}", response_class=HTMLResponse)
async def view_response_page(view_token: str, db: Session = Depends(get_db)):
    """Render read-only response copy HTML from backend string function."""
    reg = db.query(models.EventRegistration).filter(
        models.EventRegistration.view_token == view_token
    ).first()

    if not reg:
        return RedirectResponse(
            url="/problem?reason=invalid_token&details=The%20response%20view%20token%20could%20not%20be%20found%20or%20is%20invalid.",
            status_code=302
        )

    html_content = html_pages.render_view_response_html(reg)
    return HTMLResponse(content=html_content)


@app.get("/status/{status_token}", response_class=HTMLResponse)
async def status_page(status_token: str, db: Session = Depends(get_db)):
    """Render registration status/timeline HTML from backend string function."""
    reg = db.query(models.EventRegistration).filter(
        models.EventRegistration.status_token == status_token
    ).first()

    if not reg:
        return RedirectResponse(
            url="/problem?reason=invalid_token&details=The%20status%20timeline%20token%20is%20invalid%20or%20not%20found.",
            status_code=302
        )

    html_content = html_pages.render_status_html(reg)
    return HTMLResponse(content=html_content)


@app.get("/edit/{edit_token}", response_class=HTMLResponse)
async def edit_page(edit_token: str, db: Session = Depends(get_db)):
    """Render response editor HTML form from backend string function."""
    reg = db.query(models.EventRegistration).filter(
        models.EventRegistration.edit_token == edit_token
    ).first()

    if not reg:
        return RedirectResponse(
            url="/problem?reason=invalid_token&details=The%20edit%20token%20is%20invalid%20or%20not%20found.",
            status_code=302
        )

    if reg.edit_token_expires_at and reg.edit_token_expires_at < datetime.datetime.utcnow():
        return RedirectResponse(
            url="/problem?reason=expired_token&details=This%20editing%20link%20has%20expired.%20For%20security%2C%20please%20request%20a%20new%20link.",
            status_code=302
        )

    # Check lock policies
    if reg.is_edit_locked and config.LOCK_EDIT_AFTER_APPROVAL:
        return HTMLResponse(content=html_pages.render_edit_locked_html(reg), status_code=400)

    html_content = html_pages.render_edit_html(reg)
    return HTMLResponse(content=html_content)


@app.post("/edit/{edit_token}")
async def process_edit_submission(
    edit_token: str,
    payload: schemas.RegistrationUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Processes edited responses."""
    reg = db.query(models.EventRegistration).filter(
        models.EventRegistration.edit_token == edit_token
    ).first()

    if not reg:
        raise HTTPException(status_code=404, detail="Edit token not found.")

    if reg.is_edit_locked and config.LOCK_EDIT_AFTER_APPROVAL:
        raise HTTPException(status_code=400, detail="Editing is locked for this response.")

    # Check duplicate UTR against other registrations
    if payload.upi_reference_id != reg.upi_reference_id:
        duplicate_utr = db.query(models.EventRegistration).filter(
            models.EventRegistration.upi_reference_id == payload.upi_reference_id,
            models.EventRegistration.id != reg.id
        ).first()
        if duplicate_utr:
            raise HTTPException(status_code=400, detail="This transaction ID has already been submitted.")

    # Record old data for audit trail
    old_data = {
        "full_name": reg.full_name,
        "phone": reg.phone,
        "college": reg.college,
        "department": reg.department,
        "year": reg.year,
        "roll_number": reg.roll_number,
        "upi_reference_id": reg.upi_reference_id,
        "payment_screenshot_url": reg.payment_screenshot_url,
        "payment_status": reg.payment_status,
        "registration_status": reg.registration_status
    }

    # Reset payment status if UTR has changed
    utr_changed = payload.upi_reference_id != reg.upi_reference_id
    if utr_changed:
        reg.payment_status = "PENDING_REVIEW"
        reg.registration_status = "UPDATED"
    else:
        # If UTR wasn't changed, registration status is still updated
        reg.registration_status = "UPDATED"

    # Update database record
    reg.full_name = payload.full_name
    reg.phone = payload.phone
    reg.college = payload.college
    reg.department = payload.department
    reg.year = payload.year
    reg.roll_number = payload.roll_number
    reg.upi_reference_id = payload.upi_reference_id
    reg.payment_screenshot_url = payload.payment_screenshot_url
    reg.edit_count += 1
    reg.last_edited_at = datetime.datetime.utcnow()

    db.commit()

    # Log action in audits
    client_ip = get_client_ip(request)
    audit_log = models.RegistrationAuditLog(
        registration_id=reg.registration_id,
        action="EDITED",
        old_data=json.dumps(old_data),
        new_data=json.dumps(payload.model_dump()),
        performed_by="user",
        ip_address=client_ip
    )
    db.add(audit_log)
    db.commit()

    # Trigger updated notification email asynchronously
    email_sent = email_service.send_details_updated_email(reg, db)
    if email_sent:
        reg.email_status = "SENT"
    else:
        reg.email_status = "FAILED"
    db.commit()

    return {
        "success": True,
        "message": "Response updated successfully",
        "redirect_url": f"/status/{reg.status_token}"
    }


# --- ADMINISTRATIVE CONSOLE ROUTES ---

@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Renders administrative login panel."""
    if is_admin_session_valid(request):
        return RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    return HTMLResponse(content=html_pages.render_admin_login_html())


@app.post("/admin/login")
async def admin_login(
    admin_password: str = Form(...),
):
    """Process admin password authentication and set signed cookie session."""
    if admin_password != config.ADMIN_SECRET:
        return HTMLResponse(
            content=html_pages.render_admin_login_html("Incorrect admin secret credentials."),
            status_code=401
        )

    # Secure sign session cookie value
    session_cookie = security.sign_session("admin_authenticated")
    
    response = RedirectResponse(url="/admin", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key="admin_session",
        value=session_cookie,
        httponly=True,
        samesite="lax",
        secure=False # set True in production with TLS
    )
    return response


@app.post("/admin/logout")
async def admin_logout():
    """Clear admin session cookie."""
    response = RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(key="admin_session")
    return response


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    search: Optional[str] = "",
    payment_status: Optional[str] = "",
    db: Session = Depends(get_db)
):
    """Administrative overview and registration management dashboard."""
    if not is_admin_session_valid(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    # Compute Statistics counters
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
        "correction": correction,
        "today": today
    }

    # Fetch registrations query
    query = db.query(models.EventRegistration)

    # Apply search filter (match Reg ID, Name, Email, Phone, UTR)
    if search:
        search_q = f"%{search.strip()}%"
        query = query.filter(
            (models.EventRegistration.registration_id.like(search_q)) |
            (models.EventRegistration.full_name.like(search_q)) |
            (models.EventRegistration.email.like(search_q)) |
            (models.EventRegistration.phone.like(search_q)) |
            (models.EventRegistration.upi_reference_id.like(search_q))
        )

    # Apply payment status filter
    if payment_status:
        query = query.filter(models.EventRegistration.payment_status == payment_status)

    # Sorting logic: PENDING_REVIEW comes first, then ordered by created_at desc
    ordered_query = query.order_by(
        case(
            (models.EventRegistration.payment_status == "PENDING_REVIEW", 1),
            else_=2
        ),
        desc(models.EventRegistration.created_at)
    )

    records = ordered_query.all()
    filters = {"search": search, "status": payment_status}

    html_content = html_pages.render_admin_dashboard_html(records, stats, filters)
    return HTMLResponse(content=html_content)


@app.get("/admin/registration/{registration_id}", response_class=HTMLResponse)
async def admin_registration_detail(
    registration_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Retrieve full attendee files, history, audit trails and email log."""
    if not is_admin_session_valid(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    reg = db.query(models.EventRegistration).filter(
        models.EventRegistration.registration_id == registration_id
    ).first()

    if not reg:
        return RedirectResponse(
            url="/problem?reason=registration_not_found&details=Registration%20record%20could%20not%20be%20located.",
            status_code=302
        )

    # Fetch audit and email logs
    audits = db.query(models.RegistrationAuditLog).filter(
        models.RegistrationAuditLog.registration_id == registration_id
    ).order_by(desc(models.RegistrationAuditLog.created_at)).all()

    emails = db.query(models.EmailLog).filter(
        models.EmailLog.registration_id == registration_id
    ).order_by(desc(models.EmailLog.created_at)).all()

    html_content = html_pages.render_admin_detail_html(reg, audits, emails)
    return HTMLResponse(content=html_content)


@app.post("/admin/approve/{registration_id}")
async def admin_approve_payment(
    registration_id: str,
    request: Request,
    admin_note: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Verifies UPI manual payment, locks edit access and confirms seat."""
    if not is_admin_session_valid(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    reg = db.query(models.EventRegistration).filter(
        models.EventRegistration.registration_id == registration_id
    ).first()

    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    # If already approved, skip sending duplicate emails
    if reg.payment_status == "APPROVED":
        return RedirectResponse(
            url=f"/admin/registration/{registration_id}", 
            status_code=status.HTTP_303_SEE_OTHER
        )

    # Record action parameters
    old_status = reg.payment_status
    reg.payment_status = "APPROVED"
    reg.registration_status = "CONFIRMED"
    reg.approved_at = datetime.datetime.utcnow()
    reg.is_edit_locked = True
    if admin_note is not None:
        reg.admin_note = admin_note.strip()

    # Log audit
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

    # Send confirmation email
    email_sent = email_service.send_payment_approved_email(reg, db)
    if email_sent:
        reg.email_status = "SENT"
    else:
        reg.email_status = "FAILED"
    db.commit()

    return RedirectResponse(
        url=f"/admin/registration/{registration_id}", 
        status_code=status.HTTP_303_SEE_OTHER
    )


@app.post("/admin/reject/{registration_id}")
async def admin_reject_payment(
    registration_id: str,
    request: Request,
    admin_note: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Rejects UPI reference, unlocks editor to allow correction."""
    if not is_admin_session_valid(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    reg = db.query(models.EventRegistration).filter(
        models.EventRegistration.registration_id == registration_id
    ).first()

    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    old_status = reg.payment_status
    reg.payment_status = "REJECTED"
    reg.registration_status = "REJECTED"
    reg.rejected_at = datetime.datetime.utcnow()
    reg.is_edit_locked = False
    
    if admin_note:
        reg.admin_note = admin_note.strip()

    # Log audit
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

    # Send rejection notification with correction links
    email_sent = email_service.send_payment_rejected_email(reg, db)
    if email_sent:
        reg.email_status = "SENT"
    else:
        reg.email_status = "FAILED"
    db.commit()

    return RedirectResponse(
        url=f"/admin/registration/{registration_id}", 
        status_code=status.HTTP_303_SEE_OTHER
    )


@app.post("/admin/needs-correction/{registration_id}")
async def admin_mark_correction(
    registration_id: str,
    request: Request,
    admin_note: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Marks registration as needs correction, unlocks user edits."""
    if not is_admin_session_valid(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    reg = db.query(models.EventRegistration).filter(
        models.EventRegistration.registration_id == registration_id
    ).first()

    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    old_status = reg.payment_status
    reg.payment_status = "NEEDS_CORRECTION"
    reg.is_edit_locked = False
    
    if admin_note:
        reg.admin_note = admin_note.strip()

    # Log audit
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

    # Send correction needed email
    email_sent = email_service.send_needs_correction_email(reg, db)
    if email_sent:
        reg.email_status = "SENT"
    else:
        reg.email_status = "FAILED"
    db.commit()

    return RedirectResponse(
        url=f"/admin/registration/{registration_id}", 
        status_code=status.HTTP_303_SEE_OTHER
    )


@app.post("/admin/lock-edit/{registration_id}")
async def admin_lock_edit(
    registration_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Manually lock editing of responses."""
    if not is_admin_session_valid(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    reg = db.query(models.EventRegistration).filter(
        models.EventRegistration.registration_id == registration_id
    ).first()

    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

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

    return RedirectResponse(
        url=f"/admin/registration/{registration_id}", 
        status_code=status.HTTP_303_SEE_OTHER
    )


@app.post("/admin/unlock-edit/{registration_id}")
async def admin_unlock_edit(
    registration_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Manually unlock editing of responses."""
    if not is_admin_session_valid(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    reg = db.query(models.EventRegistration).filter(
        models.EventRegistration.registration_id == registration_id
    ).first()

    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

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

    return RedirectResponse(
        url=f"/admin/registration/{registration_id}", 
        status_code=status.HTTP_303_SEE_OTHER
    )


@app.post("/admin/resend-email/{registration_id}")
async def admin_resend_email(
    registration_id: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """Triggers resend of the latest status email notifications."""
    if not is_admin_session_valid(request):
        return RedirectResponse(url="/admin/login", status_code=status.HTTP_303_SEE_OTHER)

    reg = db.query(models.EventRegistration).filter(
        models.EventRegistration.registration_id == registration_id
    ).first()

    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    # Resend status email
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
    
    if email_sent:
        reg.email_status = "SENT"
    else:
        reg.email_status = "FAILED"
        
    db.commit()

    return RedirectResponse(
        url=f"/admin/registration/{registration_id}", 
        status_code=status.HTTP_303_SEE_OTHER
    )


@app.get("/admin/export.csv")
async def admin_export_csv(
    request: Request,
    search: Optional[str] = "",
    payment_status: Optional[str] = "",
    db: Session = Depends(get_db)
):
    """Exports filtered registrations as a CSV attachment file."""
    if not is_admin_session_valid(request):
        return Response("Unauthorized access", status_code=401)

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

    # Create CSV memory buffer
    output = io.StringIO()
    writer = csv.writer(output)

    # Header Row
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


@app.get("/health")
async def health_check():
    """Service health state endpoint."""
    return {"status": "ok", "service": "event-registration-fastapi"}


@app.get("/problem", response_class=HTMLResponse)
async def problem_page(request: Request, reason: Optional[str] = None, details: Optional[str] = None):
    # Log timestamp, requested path, reason, user IP, user-agent, exception type if available
    path = str(request.url.path)
    if request.query_params:
        path += f"?{request.query_params}"
    user_agent = request.headers.get("user-agent", "Unknown")
    ip_address = get_client_ip(request)
    
    # If no reason/details specified, set defaults
    reason_str = reason or "Unexpected issue"
    details_str = details or "Something went wrong while loading this page."
    
    # Log to DB
    log_problem_to_db(
        path=path,
        reason=reason_str,
        details=details_str,
        user_agent=user_agent,
        ip_address=ip_address,
        exception_type=None
    )
    
    return HTMLResponse(
        content=html_pages.render_problem_html(reason=reason_str, details=details_str)
    )


@app.get("/{path:path}", response_class=HTMLResponse)
async def catch_all(path: str, request: Request):
    # Block direct HTML file access/jumping
    if path.endswith(".html") and path not in ["form", "static/form.html"]:
        return RedirectResponse(url="/problem?reason=invalid_html_access", status_code=302)

    # API routes return JSON for 404
    if path.startswith("api") or path.startswith("/api"):
        return Response(
            content=json.dumps({"detail": "Not Found"}),
            status_code=404,
            media_type="application/json"
        )

    # Log 404 page error
    user_agent = request.headers.get("user-agent", "Unknown")
    ip_address = get_client_ip(request)
    reason = "Page not found"
    details = "This page is not available. Please return to the event form."
    
    log_problem_to_db(
        path="/" + path,
        reason=reason,
        details=details,
        user_agent=user_agent,
        ip_address=ip_address,
        exception_type="404 NotFound (Catch All)"
    )

    return HTMLResponse(
        content=html_pages.render_problem_html(reason=reason, details=details),
        status_code=404
    )
