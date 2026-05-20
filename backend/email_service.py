import logging
import secrets
import resend
from sqlalchemy.orm import Session
import config
from models import EmailLog
import datetime
from utils import escape_html

# Set resend API key
resend.api_key = config.RESEND_API_KEY

logger = logging.getLogger(__name__)

def log_email_result(
    db: Session,
    registration_id: str,
    email_to: str,
    email_type: str,
    subject: str,
    status: str,
    resend_message_id: str = None,
    error_message: str = None
):
    """Inserts a record into the email_logs table."""
    try:
        log = EmailLog(
            registration_id=registration_id,
            email_to=email_to,
            email_type=email_type,
            subject=subject,
            resend_message_id=resend_message_id,
            status=status,
            error_message=error_message,
            created_at=datetime.datetime.utcnow()
        )
        db.add(log)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log email result to DB: {e}")
        db.rollback()

def render_email_body(registration, title: str, description: str, status_text: str, badge_color: str) -> str:
    """Renders the HTML body of the email with premium styles and action buttons."""
    
    # Escape user values for security
    full_name = escape_html(registration.full_name)
    email = escape_html(registration.email)
    phone = escape_html(registration.phone)
    college = escape_html(registration.college)
    department = escape_html(registration.department)
    year = escape_html(registration.year)
    roll_number = escape_html(registration.roll_number or "N/A")
    utr = escape_html(registration.upi_reference_id)
    reg_id = escape_html(registration.registration_id)
    event_name = escape_html(registration.event_name)
    amount = registration.amount
    upi_id = escape_html(registration.upi_id)
    
    frontend_url = config.FRONTEND_URL
    view_link = f"{frontend_url}/view-response.html?token={registration.view_token}"
    edit_link = f"{frontend_url}/edit-response.html?token={registration.edit_token}"
    status_link = f"{frontend_url}/status.html?token={registration.status_token}"
    
    # Custom message about editing lock
    edit_notice = ""
    if registration.is_edit_locked:
        edit_notice = """
        <div style="margin-top: 15px; padding: 10px; background-color: #3b2020; border-left: 4px solid #f44336; border-radius: 4px; color: #ff9999; font-size: 13px; text-align: left;">
            <strong>Note:</strong> Response editing is locked because your registration has been approved. If you need to make changes, please contact the organizer.
        </div>
        """
    else:
        edit_notice = """
        <div style="margin-top: 15px; padding: 10px; background-color: #1e2530; border-left: 4px solid #3b82f6; border-radius: 4px; color: #93c5fd; font-size: 13px; text-align: left;">
            <strong>Note:</strong> You can edit your response details using the "Edit Response" button below, until the organizers review/approve it.
        </div>
        """

    # Admin note display
    admin_note_section = ""
    if registration.admin_note:
        admin_note_section = f"""
        <div style="margin: 20px 0; padding: 15px; background-color: #2a1b1b; border: 1px solid #ef4444; border-radius: 8px; text-align: left;">
            <p style="margin: 0 0 5px 0; font-size: 12px; color: #ef4444; text-transform: uppercase; font-weight: bold; letter-spacing: 0.05em;">Admin Message:</p>
            <p style="margin: 0; color: #f87171; font-size: 14px; line-height: 1.5;">{escape_html(registration.admin_note)}</p>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0f172a; color: #f8fafc;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #0f172a;">
        <!-- Header / Logo Area -->
        <div style="text-align: center; padding: 20px 0; background: linear-gradient(135deg, #1e1b4b 0%, #311042 100%); border-radius: 12px 12px 0 0; border-bottom: 2px solid #8b5cf6;">
            <h1 style="margin: 0; font-size: 24px; color: #ffffff; letter-spacing: -0.025em; font-weight: 800;">{escape_html(config.ORGANIZER_NAME)}</h1>
            <p style="margin: 5px 0 0 0; font-size: 14px; color: #c084fc;">{event_name}</p>
        </div>
        
        <!-- Main Content Card -->
        <div style="background-color: #1e293b; padding: 30px; border-radius: 0 0 12px 12px; border: 1px solid #334155; border-top: none; text-align: center;">
            <div style="display: inline-block; padding: 6px 16px; background-color: {badge_color}; color: #ffffff; border-radius: 9999px; font-size: 13px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 20px;">
                {status_text}
            </div>
            
            <h2 style="margin: 0 0 10px 0; color: #ffffff; font-size: 20px; font-weight: 700;">{title}</h2>
            <p style="margin: 0 0 25px 0; color: #94a3b8; font-size: 15px; line-height: 1.6;">{description}</p>
            
            {admin_note_section}

            <!-- Details Box -->
            <div style="background-color: #0f172a; border-radius: 8px; border: 1px solid #334155; padding: 20px; margin-bottom: 30px; text-align: left;">
                <h3 style="margin: 0 0 15px 0; font-size: 14px; color: #38bdf8; text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em; border-bottom: 1px solid #334155; padding-bottom: 5px;">Registration Summary</h3>
                <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                    <tr>
                        <td style="padding: 6px 0; color: #64748b; width: 40%;">Registration ID:</td>
                        <td style="padding: 6px 0; color: #ffffff; font-weight: 600; font-family: monospace;">{reg_id}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748b;">Full Name:</td>
                        <td style="padding: 6px 0; color: #ffffff;">{full_name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748b;">Email:</td>
                        <td style="padding: 6px 0; color: #ffffff;">{email}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748b;">Phone Number:</td>
                        <td style="padding: 6px 0; color: #ffffff;">{phone}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748b;">College:</td>
                        <td style="padding: 6px 0; color: #ffffff;">{college}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748b;">Department:</td>
                        <td style="padding: 6px 0; color: #ffffff;">{department} (Year {year})</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748b;">Roll Number:</td>
                        <td style="padding: 6px 0; color: #ffffff;">{roll_number}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748b;">Amount Paid:</td>
                        <td style="padding: 6px 0; color: #22c55e; font-weight: bold;">₹{amount} (via {upi_id})</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748b;">UPI Ref ID / UTR:</td>
                        <td style="padding: 6px 0; color: #ffffff; font-family: monospace;">{utr}</td>
                    </tr>
                </table>
            </div>
            
            <!-- Call to Actions -->
            <div style="margin-bottom: 20px;">
                <a href="{status_link}" target="_blank" style="display: block; background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: #ffffff; text-decoration: none; padding: 12px 24px; border-radius: 6px; font-weight: bold; margin-bottom: 12px; font-size: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
                    Check Status / Live Timeline
                </a>
                
                <div style="display: flex; justify-content: space-between; gap: 10px;">
                    <a href="{view_link}" target="_blank" style="flex: 1; display: inline-block; background-color: #334155; color: #f1f5f9; text-decoration: none; padding: 10px 12px; border-radius: 6px; font-size: 13px; font-weight: bold; text-align: center; border: 1px solid #475569;">
                        View Response Copy
                    </a>
                    
                    <a href="{edit_link}" target="_blank" style="flex: 1; display: inline-block; background-color: #334155; color: #f1f5f9; text-decoration: none; padding: 10px 12px; border-radius: 6px; font-size: 13px; font-weight: bold; text-align: center; border: 1px solid #475569;">
                        Edit Response
                    </a>
                </div>
                
                {edit_notice}
            </div>
            
            <hr style="border: 0; border-top: 1px solid #334155; margin: 30px 0 20px 0;">
            
            <!-- Support Footer -->
            <p style="margin: 0; color: #64748b; font-size: 12px; line-height: 1.5;">
                This email is automated. If you have any questions, contact us at <a href="mailto:{config.SUPPORT_EMAIL}" style="color: #38bdf8; text-decoration: none;">{config.SUPPORT_EMAIL}</a>.<br>
                Event Registration Platform powered by Sakra Vision.
            </p>
        </div>
    </div>
</body>
</html>
"""
    return html

def _send_email_api_call(db: Session, registration, email_type: str, subject: str, html_body: str):
    """Internal helper to invoke the Resend API and log the result."""
    if not config.RESEND_API_KEY or config.RESEND_API_KEY.startswith("re_xxx"):
        # Simulated mode if no valid API key is set
        print(f"\n--- [EMAIL SIMULATION: {email_type.upper()}] ---")
        print(f"To: {registration.email}")
        print(f"Subject: {subject}")
        print("API Key not configured or placeholder. Treating as simulated SUCCESS.")
        print("-------------------------------------------\n")
        log_email_result(
            db=db,
            registration_id=registration.registration_id,
            email_to=registration.email,
            email_type=email_type,
            subject=subject,
            status="SENT",
            resend_message_id="simulated_id_" + secrets.token_hex(8)
        )
        return True

    try:
        response = resend.Emails.send({
            "from": config.FROM_EMAIL,
            "to": registration.email,
            "subject": subject,
            "html": html_body
        })
        
        message_id = response.get("id")
        log_email_result(
            db=db,
            registration_id=registration.registration_id,
            email_to=registration.email,
            email_type=email_type,
            subject=subject,
            status="SENT",
            resend_message_id=message_id
        )
        return True
    except Exception as e:
        logger.error(f"Resend email sending failed for {registration.email}: {e}")
        log_email_result(
            db=db,
            registration_id=registration.registration_id,
            email_to=registration.email,
            email_type=email_type,
            subject=subject,
            status="FAILED",
            error_message=str(e)
        )
        return False

def send_submission_received_email(registration, db: Session):
    subject = f"Response received: {config.EVENT_NAME} - {registration.registration_id}"
    title = "Response Received Successfully"
    description = "Thank you for registering. Your payment is currently under manual review by our team. We will verify your transaction reference and send a confirmation email once approved."
    html_body = render_email_body(
        registration,
        title=title,
        description=description,
        status_text="Pending Review",
        badge_color="#f59e0b" # Orange/Amber
    )
    return _send_email_api_call(db, registration, "submission", subject, html_body)

def send_details_updated_email(registration, db: Session):
    subject = f"Your response was updated - {registration.registration_id}"
    title = "Response Updated Successfully"
    
    if registration.payment_status == "PENDING_REVIEW":
        desc = "Your registration details were updated. Since you updated your transaction ID, your payment status has been reset to Pending Review. Our admin team will verify it shortly."
        status_text = "Pending Review"
        color = "#f59e0b"
    else:
        desc = f"Your registration details were successfully updated. Your current status is: {registration.payment_status}."
        status_text = registration.payment_status.replace("_", " ")
        color = "#ef4444" if "REJECT" in registration.payment_status else ("#22c55e" if "APPROV" in registration.payment_status else "#3b82f6")

    html_body = render_email_body(registration, title=title, description=desc, status_text=status_text, badge_color=color)
    return _send_email_api_call(db, registration, "updated", subject, html_body)

def send_payment_approved_email(registration, db: Session):
    subject = f"Registration confirmed: {config.EVENT_NAME} - {registration.registration_id}"
    title = "Registration Confirmed!"
    description = "Awesome news! Your payment has been manually verified, and your seat for the event is officially secured. We look forward to seeing you!"
    html_body = render_email_body(
        registration,
        title=title,
        description=description,
        status_text="Confirmed / Approved",
        badge_color="#22c55e" # Green
    )
    return _send_email_api_call(db, registration, "approved", subject, html_body)

def send_payment_rejected_email(registration, db: Session):
    subject = f"Action required: Payment issue - {registration.registration_id}"
    title = "Payment Verification Rejected"
    description = "We were unable to verify your payment with the provided transaction reference ID. Please check the admin note below, click the 'Edit Response' button to update your UTR/Reference ID with correct details."
    html_body = render_email_body(
        registration,
        title=title,
        description=description,
        status_text="Rejected",
        badge_color="#ef4444" # Red
    )
    return _send_email_api_call(db, registration, "rejected", subject, html_body)

def send_needs_correction_email(registration, db: Session):
    subject = f"Correction needed for your registration - {registration.registration_id}"
    title = "Correction Needed"
    description = "Your registration details need some adjustments. Please check the admin note below and click the 'Edit Response' button to make corrections to your form submission."
    html_body = render_email_body(
        registration,
        title=title,
        description=description,
        status_text="Needs Correction",
        badge_color="#3b82f6" # Blue
    )
    return _send_email_api_call(db, registration, "correction", subject, html_body)

def send_latest_status_email(registration, db: Session):
    """Sends a fresh copy of the status email based on the current status of the registration."""
    status = registration.payment_status
    if status == "APPROVED":
        return send_payment_approved_email(registration, db)
    elif status == "REJECTED":
        return send_payment_rejected_email(registration, db)
    elif status == "NEEDS_CORRECTION":
        return send_needs_correction_email(registration, db)
    else:
        # Default or PENDING_REVIEW
        return send_submission_received_email(registration, db)
