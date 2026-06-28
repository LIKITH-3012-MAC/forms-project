import logging
import secrets
import resend
from sqlalchemy.orm import Session
import config
from models import EmailLog
import datetime
from utils import escape_html, get_ist_time

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
            created_at=get_ist_time()
        )
        db.add(log)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to log email result to DB: {e}")
        db.rollback()

def frontend_url(path: str) -> str:
    base = config.FRONTEND_URL.rstrip("/")
    clean_path = path.lstrip("/")
    return f"{base}/{clean_path}"

def assert_safe_frontend_url():
    if config.ENVIRONMENT == "production":
        forbidden = ["localhost", "127.0.0.1", "file://"]
        if any(x in config.FRONTEND_URL for x in forbidden):
            print(
                f"⚠️ WARNING: FRONTEND_URL is localhost/127.0.0.1/file:// in production. FRONTEND_URL={config.FRONTEND_URL}"
            )

def organizer_message_block(admin_note: str, message_type: str = "info") -> str:
    note = (admin_note or "").strip()

    if not note:
        return ""

    safe_note = escape_html(note).replace("\n", "<br>")

    if message_type == "approved":
        title = "Message from the Organizer"
        accent = "#16a34a"
        icon = "✓"
        soft_bg = "#ecfdf5"
        border = "#bbf7d0"
    elif message_type == "rejected":
        title = "Action Required from Organizer"
        accent = "#dc2626"
        icon = "!"
        soft_bg = "#fef2f2"
        border = "#fecaca"
    elif message_type == "correction":
        title = "Correction Requested by Organizer"
        accent = "#d97706"
        icon = "!"
        soft_bg = "#fffbeb"
        border = "#fde68a"
    else:
        title = "Message from the Organizer"
        accent = "#0284c7"
        icon = "i"
        soft_bg = "#f0f9ff"
        border = "#bae6fd"

    return f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:24px 0;">
      <tr>
        <td style="
          padding:20px;
          border-radius:18px;
          background:{soft_bg};
          border:1px solid {border};
          border-left:5px solid {accent};
        ">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
            <tr>
              <td style="width:42px;vertical-align:top;">
                <div style="
                  width:34px;
                  height:34px;
                  line-height:34px;
                  text-align:center;
                  border-radius:50%;
                  background:{accent};
                  color:#ffffff;
                  font-size:18px;
                  font-weight:800;
                ">{icon}</div>
              </td>

              <td style="vertical-align:top;padding-left:10px;">
                <p style="
                  margin:0 0 8px;
                  color:{accent};
                  font-family:Arial,sans-serif;
                  font-size:12px;
                  font-weight:800;
                  letter-spacing:0.10em;
                  text-transform:uppercase;
                ">{title}</p>

                <p style="
                  margin:0;
                  color:#0f172a;
                  font-family:Arial,sans-serif;
                  font-size:15px;
                  font-weight:500;
                  line-height:1.7;
                ">{safe_note}</p>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
    """

def render_email_body(registration, title: str, description: str, status_text: str, badge_color: str, message_type: str = "info") -> str:
    """Renders the HTML body of the email with a modern premium responsive light design."""
    
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
    
    view_link = frontend_url(f"view-response.html?token={registration.view_token}")
    edit_link = frontend_url(f"edit-response.html?token={registration.edit_token}")
    status_link = frontend_url(f"status.html?token={registration.status_token}")
    
    # Custom message about editing lock
    edit_notice = ""
    if registration.is_edit_locked:
        edit_notice = """
        <div style="margin-top: 15px; padding: 12px; background-color: #fef2f2; border: 1px solid #fecaca; border-left: 4px solid #ef4444; border-radius: 8px; color: #991b1b; font-size: 13px; text-align: left; line-height: 1.5;">
            <strong>Note:</strong> Response editing is locked because your registration has been approved. If you need to make changes, please contact the organizer.
        </div>
        """
    else:
        edit_notice = """
        <div style="margin-top: 15px; padding: 12px; background-color: #f0f9ff; border: 1px solid #bae6fd; border-left: 4px solid #0284c7; border-radius: 8px; color: #075985; font-size: 13px; text-align: left; line-height: 1.5;">
            <strong>Note:</strong> You can edit your response details using the "Edit Response" button above, until the organizers review/approve it.
        </div>
        """

    # Admin note display
    admin_note_section = organizer_message_block(registration.admin_note, message_type)

    import json
    reg_type = getattr(registration, "registration_type", "individual")
    team_name_val = getattr(registration, "team_name", None) or "N/A"
    team_lead_name = "N/A"
    teammates_list = []
    total_members = 1

    if reg_type == "team":
        team_info_str = getattr(registration, "team_info", None)
        if team_info_str:
            try:
                team_data = json.loads(team_info_str)
                team_lead_name = team_data.get("team_lead", {}).get("name") or registration.full_name
                members = team_data.get("members", [])
                total_members = len(members) + 1
                for idx, m in enumerate(members):
                    name = m.get("name")
                    email_addr = m.get("email")
                    teammates_list.append(f"{name} ({email_addr})")
            except Exception as e:
                print(f"Error parsing team info in email rendering: {e}")
        else:
            team_lead_name = registration.full_name
            teammates_list = []
    
    # Render Team section if applicable
    team_section_html = ""
    if reg_type == "team":
        member_rows = ""
        for idx, m in enumerate(teammates_list):
            member_rows += f"""
            <tr style="border-top: 1px solid #e2e8f0;">
                <td style="padding: 10px 0; color: #334155; font-size: 13px;">
                    <strong>Member {idx + 2}:</strong> {escape_html(m)}
                </td>
            </tr>
            """
        
        team_section_html = f"""
        <!-- Team Information Card -->
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #f8fafc;">
            <tr>
                <td style="padding: 20px;">
                    <h3 style="margin: 0 0 16px 0; font-size: 13px; color: #475569; text-transform: uppercase; font-weight: 800; letter-spacing: 0.08em; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px;">👥 Team Information</h3>
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="font-size: 14px; margin-bottom: 12px;">
                        <tr>
                            <td style="padding: 6px 0; color: #64748b; font-weight: 500; width: 40%; vertical-align: top;">Team Name:</td>
                            <td style="padding: 6px 0; color: #0f172a; font-weight: 700;">{team_name_val}</td>
                        </tr>
                        <tr>
                            <td style="padding: 6px 0; color: #64748b; font-weight: 500; vertical-align: top;">Team Leader:</td>
                            <td style="padding: 6px 0; color: #0f172a; font-weight: 600;">{team_lead_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 6px 0; color: #64748b; font-weight: 500; vertical-align: top;">Total Members:</td>
                            <td style="padding: 6px 0; color: #0f172a; font-weight: 600;">{total_members}</td>
                        </tr>
                    </table>
                    
                    <h4 style="margin: 16px 0 8px 0; font-size: 12px; color: #64748b; text-transform: uppercase; font-weight: 800; letter-spacing: 0.05em;">Member List</h4>
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                        {member_rows}
                    </table>
                </td>
            </tr>
        </table>
        """

    slot_time = escape_html(getattr(registration, "slot_time", None) or "10:00 AM - 11:00 AM")

    # Dynamic status icons and accent colors for status card
    status_icon = "🔔"
    if "approve" in title.lower() or "confirm" in title.lower():
        status_icon = "✅"
    elif "reject" in title.lower():
        status_icon = "❌"
    elif "correct" in title.lower():
        status_icon = "⚠️"
    elif "review" in title.lower() or "pending" in title.lower():
        status_icon = "⏳"

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <!--[if mso]>
    <style type="text/css">
      body, table, td, p, a, div, h1, h2, h3, span {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important; }}
    </style>
    <![endif]-->
</head>
<body style="margin: 0; padding: 0; -webkit-text-size-adjust: 100%; background-color: #ffffff; color: #0f172a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
    <div style="max-width: 600px; margin: 0 auto; padding: 24px; background-color: #ffffff;">
        
        <!-- Header -->
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 24px; text-align: center;">
            <tr>
                <td style="padding: 24px 0; background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-radius: 16px;">
                    <h1 style="margin: 0; font-size: 26px; color: #ffffff; font-weight: 800; letter-spacing: -0.025em; text-transform: uppercase;">{escape_html(config.ORGANIZER_NAME)}</h1>
                    <p style="margin: 6px 0 0 0; font-size: 14px; color: #38bdf8; font-weight: 600;">{event_name}</p>
                </td>
            </tr>
        </table>

        <!-- Main Card -->
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border: 1px solid #e2e8f0; border-radius: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.03); margin-bottom: 24px;">
            <tr>
                <td style="padding: 32px 24px;">
                    
                    <!-- Status Banner / Card -->
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 24px; text-align: left;">
                        <tr>
                            <td style="padding: 20px; background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; border-left: 5px solid {badge_color};">
                                <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                    <tr>
                                        <td style="vertical-align: top; padding-right: 12px; font-size: 24px; line-height: 1;">
                                            {status_icon}
                                        </td>
                                        <td style="vertical-align: top;">
                                            <div style="font-size: 11px; color: {badge_color}; font-weight: 800; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 4px;">{status_text}</div>
                                            <h2 style="margin: 0 0 8px 0; color: #0f172a; font-size: 18px; font-weight: 800; letter-spacing: -0.01em;">{title}</h2>
                                            <p style="margin: 0; color: #475569; font-size: 14px; line-height: 1.6;">{description}</p>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>

                    {admin_note_section}

                    <!-- Registration Summary Card -->
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #f8fafc;">
                        <tr>
                            <td style="padding: 20px;">
                                <h3 style="margin: 0 0 16px 0; font-size: 13px; color: #475569; text-transform: uppercase; font-weight: 800; letter-spacing: 0.08em; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px;">📋 Registration Details</h3>
                                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="font-size: 14px;">
                                    <tr>
                                        <td style="padding: 8px 0; color: #64748b; font-weight: 500; width: 40%; vertical-align: top;">Registration ID:</td>
                                        <td style="padding: 8px 0; color: #0f172a; font-weight: 700; font-family: monospace; word-break: break-all; width: 60%;">{reg_id}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 8px 0; color: #64748b; font-weight: 500; vertical-align: top;">Full Name:</td>
                                        <td style="padding: 8px 0; color: #0f172a; font-weight: 600;">{full_name}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 8px 0; color: #64748b; font-weight: 500; vertical-align: top;">Email:</td>
                                        <td style="padding: 8px 0; color: #0f172a; word-break: break-all;">{email}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 8px 0; color: #64748b; font-weight: 500; vertical-align: top;">Phone:</td>
                                        <td style="padding: 8px 0; color: #0f172a;">{phone}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 8px 0; color: #64748b; font-weight: 500; vertical-align: top;">College:</td>
                                        <td style="padding: 8px 0; color: #0f172a; line-height: 1.4;">{college}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 8px 0; color: #64748b; font-weight: 500; vertical-align: top;">Department:</td>
                                        <td style="padding: 8px 0; color: #0f172a;">{department} (Year {year})</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 8px 0; color: #64748b; font-weight: 500; vertical-align: top;">Roll Number:</td>
                                        <td style="padding: 8px 0; color: #0f172a;">{roll_number}</td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>

                    <!-- Payment Information Card -->
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #f8fafc;">
                        <tr>
                            <td style="padding: 20px;">
                                <h3 style="margin: 0 0 16px 0; font-size: 13px; color: #475569; text-transform: uppercase; font-weight: 800; letter-spacing: 0.08em; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px;">💳 Payment Information</h3>
                                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="font-size: 14px;">
                                    <tr>
                                        <td style="padding: 8px 0; color: #64748b; font-weight: 500; width: 40%; vertical-align: top;">Amount Paid:</td>
                                        <td style="padding: 8px 0; color: #16a34a; font-weight: 700;">₹{amount} (via {upi_id})</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 8px 0; color: #64748b; font-weight: 500; vertical-align: top;">UPI Ref ID / UTR:</td>
                                        <td style="padding: 8px 0; color: #0f172a; font-family: monospace;">{utr}</td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>

                    <!-- Team Details Card (Only if Team) -->
                    {team_section_html}

                    <!-- Event Information Card -->
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 28px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #f8fafc;">
                        <tr>
                            <td style="padding: 20px;">
                                <h3 style="margin: 0 0 16px 0; font-size: 13px; color: #475569; text-transform: uppercase; font-weight: 800; letter-spacing: 0.08em; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px;">📅 Event Details</h3>
                                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="font-size: 14px;">
                                    <tr>
                                        <td style="padding: 8px 0; color: #64748b; font-weight: 500; width: 40%; vertical-align: top;">Event Name:</td>
                                        <td style="padding: 8px 0; color: #0f172a; font-weight: 600;">{event_name}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 8px 0; color: #64748b; font-weight: 500; vertical-align: top;">Date:</td>
                                        <td style="padding: 8px 0; color: #0f172a;">15 July 2026</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 8px 0; color: #64748b; font-weight: 500; vertical-align: top;">Time:</td>
                                        <td style="padding: 8px 0; color: #0f172a;">10:00 AM</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 8px 0; color: #64748b; font-weight: 500; vertical-align: top;">Slot Time:</td>
                                        <td style="padding: 8px 0; color: #2563eb; font-weight: 600;">{slot_time}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 8px 0; color: #64748b; font-weight: 500; vertical-align: top;">Venue:</td>
                                        <td style="padding: 8px 0; color: #0f172a; line-height: 1.4;">Sakra Vision Innovation Center<br><span style="font-size:12px; color:#64748b;">Hyderabad</span></td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>

                    <!-- AI Assistant Card -->
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 28px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #f8fafc; border-left: 5px solid #6366f1;">
                        <tr>
                            <td style="padding: 20px;">
                                <h3 style="margin: 0 0 10px 0; font-size: 14px; color: #4f46e5; font-weight: 800;">🤖 Sakra Vision AI Assistant</h3>
                                <p style="margin: 0 0 12px 0; font-size: 13px; color: #475569; line-height: 1.5;">Our automated AI Voice Assistant will use your phone number to update you. You may receive:</p>
                                <ul style="margin: 0; padding-left: 20px; font-size: 13px; color: #475569; line-height: 1.6;">
                                    <li>📞 Outbound voice calls for registration/payment confirmations.</li>
                                    <li>Real-time status updates and confirmation emails.</li>
                                    <li>📅 Slot allocation and check-in reminders.</li>
                                    <li>📢 Organizer announcements and event reminders.</li>
                                </ul>
                            </td>
                        </tr>
                    </table>

                    <!-- Action Buttons -->
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-top: 32px; text-align: center;">
                        <tr>
                            <td style="padding-bottom: 12px;">
                                <a href="{status_link}" target="_blank" style="display: inline-block; width: 85%; max-width: 320px; background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); color: #ffffff; text-decoration: none; padding: 14px 24px; border-radius: 10px; font-weight: 700; font-size: 15px; box-shadow: 0 4px 6px rgba(37,99,235,0.15); text-align: center;">
                                    Check Status / Live Timeline
                                </a>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding-bottom: 8px;">
                                <table role="presentation" width="85%" cellspacing="0" cellpadding="0" align="center">
                                    <tr>
                                        <td width="48%">
                                            <a href="{view_link}" target="_blank" style="display: block; background-color: #ffffff; color: #475569; text-decoration: none; padding: 10px 12px; border-radius: 8px; font-size: 13px; font-weight: 700; text-align: center; border: 1px solid #cbd5e1;">
                                                View Response Copy
                                            </a>
                                        </td>
                                        <td width="4%"></td>
                                        <td width="48%">
                                            <a href="{edit_link}" target="_blank" style="display: block; background-color: #ffffff; color: #475569; text-decoration: none; padding: 10px 12px; border-radius: 8px; font-size: 13px; font-weight: 700; text-align: center; border: 1px solid #cbd5e1;">
                                                Edit Response
                                            </a>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding-top: 10px;">
                                {edit_notice}
                            </td>
                        </tr>
                    </table>

                </td>
            </tr>
        </table>

        <!-- Footer -->
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="text-align: center; font-size: 12px; color: #64748b; line-height: 1.6; padding: 24px 0 12px 0;">
            <tr>
                <td style="border-top: 1px solid #e2e8f0; padding-top: 24px;">
                    <p style="margin: 0 0 4px 0; font-weight: 700; font-size: 14px; color: #334155;">SAKRA VISION</p>
                    <p style="margin: 0 0 12px 0;">Founder: Likith Naidu | Support: 9440113763 | <a href="mailto:likith.anumakonda@gmail.com" style="color: #2563eb; text-decoration: none;">likith.anumakonda@gmail.com</a></p>
                    <p style="margin: 0;">This email is automated. If you have any questions, please contact us.</p>
                    <p style="margin: 4px 0 0 0;">&copy; 2026 Sakra Vision. All rights reserved.</p>
                </td>
            </tr>
        </table>

    </div>
</body>
</html>
"""
    return html


def render_member_email_body(registration, member_name: str) -> str:
    """Renders tailored HTML email body for team members with a clean modern aesthetic."""
    event_name = escape_html(registration.event_name)
    team_name = escape_html(registration.team_name or "N/A")
    team_lead = escape_html(registration.full_name)
    registration_status = escape_html(registration.registration_status or "PENDING")
    payment_status = escape_html(registration.payment_status or "PENDING_REVIEW").replace("_", " ")
    
    event_date = "15 July 2026"
    slot_time = escape_html(registration.slot_time or "10:00 AM - 11:00 AM")
    venue_name = "Sakra Vision Innovation Center"
    admin_message = escape_html(registration.admin_note or "No message provided.").replace("\n", "<br>")
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Team Registration Update</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0f172a; color: #f8fafc;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #0f172a;">
        <!-- Header / Logo Area -->
        <div style="text-align: center; padding: 20px 0; background: linear-gradient(135deg, #1e1b4b 0%, #311042 100%); border-radius: 12px 12px 0 0; border-bottom: 2px solid #8b5cf6;">
            <h1 style="margin: 0; font-size: 24px; color: #ffffff; letter-spacing: -0.025em; font-weight: 800;">{escape_html(config.ORGANIZER_NAME)}</h1>
            <p style="margin: 5px 0 0 0; font-size: 14px; color: #c084fc;">{event_name}</p>
        </div>
        
        <!-- Main Content Card -->
        <div style="background-color: #1e293b; padding: 30px; border-radius: 0 0 12px 12px; border: 1px solid #334155; border-top: none; text-align: left;">
            <p style="margin: 0 0 20px 0; font-size: 16px; color: #f1f5f9;">Hello <strong>{escape_html(member_name)}</strong>,</p>
            
            <p style="margin: 0 0 15px 0; font-size: 15px; color: #cbd5e1; line-height: 1.6;">This is an automated update from Sakra Vision.</p>
            <p style="margin: 0 0 20px 0; font-size: 15px; color: #cbd5e1; line-height: 1.6;">You are registered as a member of Team <strong>"{team_name}"</strong> for <strong>{event_name}</strong>.</p>
            
            <!-- Details Box -->
            <div style="background-color: #0f172a; border-radius: 8px; border: 1px solid #334155; padding: 20px; margin-bottom: 30px; text-align: left;">
                <h3 style="margin: 0 0 15px 0; font-size: 14px; color: #38bdf8; text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em; border-bottom: 1px solid #334155; padding-bottom: 5px;">Registration Details</h3>
                <table style="width: 100%; border-collapse: collapse; font-size: 14px; table-layout: fixed;">
                    <tr>
                        <td style="padding: 6px 0; color: #64748b; width: 35%; vertical-align: top;">Team Leader:</td>
                        <td style="padding: 6px 0; color: #ffffff; font-weight: 600; width: 65%;">{team_lead}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748b; vertical-align: top;">Current Registration Status:</td>
                        <td style="padding: 6px 0; color: #ffffff; text-transform: uppercase;">{registration_status}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748b; vertical-align: top;">Current Payment Status:</td>
                        <td style="padding: 6px 0; color: #ffffff; text-transform: uppercase;">{payment_status}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748b; vertical-align: top;">Event Date:</td>
                        <td style="padding: 6px 0; color: #ffffff;">{event_date}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748b; vertical-align: top;">Slot Time:</td>
                        <td style="padding: 6px 0; color: #ffffff;">{slot_time}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px 0; color: #64748b; vertical-align: top;">Venue:</td>
                        <td style="padding: 6px 0; color: #ffffff;">{venue_name}</td>
                    </tr>
                </table>
            </div>

            <!-- Message from Organizer -->
            <div style="padding: 16px; border-left: 4px solid #3b82f6; background-color: #0f172a; border-radius: 4px; margin-bottom: 25px;">
                <strong style="color: #3b82f6; display: block; margin-bottom: 6px; font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em;">Organizer Message</strong>
                <p style="margin: 0; color: #cbd5e1; font-size: 14px; line-height: 1.6;">{admin_message}</p>
            </div>
            
            <p style="margin: 0 0 20px 0; font-size: 14px; color: #94a3b8;">A confirmation has also been shared with your Team Leader.</p>
            <p style="margin: 0 0 20px 0; font-size: 14px; color: #cbd5e1;">Thank you.<br>Sakra Vision</p>
            
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

def _send_single_email_to_recipient(registration, recipient_email: str, email_type: str, subject: str, html_body: str) -> bool:
    """Invokes Resend API for a single recipient and logs the transaction using a fresh DB session, with automatic retry for rate limits."""
    from database import SessionLocal
    db = SessionLocal()
    try:
        assert_safe_frontend_url()
        
        if not config.RESEND_API_KEY or config.RESEND_API_KEY.startswith("re_xxx") or not config.RESEND_API_KEY.strip():
            # Simulated mode if no valid API key is set
            print(f"\n--- [EMAIL SIMULATION: {email_type.upper()}] ---")
            print(f"To: {recipient_email}")
            print(f"Subject: {subject}")
            print("API Key not configured or placeholder. Treating as simulated SUCCESS.")
            print("-------------------------------------------\n")
            log_email_result(
                db=db,
                registration_id=registration.registration_id,
                email_to=recipient_email,
                email_type=email_type,
                subject=subject,
                status="SENT",
                resend_message_id="simulated_id_" + secrets.token_hex(8)
            )
            return True

        import time
        max_retries = 4
        delay = 0.6
        
        for attempt in range(max_retries):
            try:
                response = resend.Emails.send({
                    "from": config.FROM_EMAIL,
                    "to": recipient_email,
                    "subject": subject,
                    "html": html_body
                })
                
                message_id = response.get("id")
                log_email_result(
                    db=db,
                    registration_id=registration.registration_id,
                    email_to=recipient_email,
                    email_type=email_type,
                    subject=subject,
                    status="SENT",
                    resend_message_id=message_id
                )
                return True
            except Exception as e:
                err_str = str(e).lower()
                if "too many requests" in err_str or "rate limit" in err_str or "429" in err_str:
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))
                        continue
                logger.error(f"Resend email sending failed for {recipient_email}: {e}")
                log_email_result(
                    db=db,
                    registration_id=registration.registration_id,
                    email_to=recipient_email,
                    email_type=email_type,
                    subject=subject,
                    status="FAILED",
                    error_message=str(e)
                )
                return False
    finally:
        db.close()

def _send_email_api_call(db: Session, registration, email_type: str, subject: str, html_body: str) -> bool:
    """Internal helper to invoke the Resend API for Team Leader and all registered teammates concurrently."""
    recipients = [registration.email]

    reg_type = getattr(registration, "registration_type", "individual")
    if reg_type == "team":
        team_info_str = getattr(registration, "team_info", None)
        if team_info_str:
            try:
                import json
                team_data = json.loads(team_info_str)
                members = team_data.get("members", [])
                for m in members:
                    m_email = m.get("email")
                    if m_email:
                        recipients.append(m_email)
            except Exception as e:
                logger.error(f"Error parsing team members: {e}")

    # Remove empty values, invalid email addresses, and duplicates
    import re
    valid_email_regex = re.compile(r'^[\w\.-]+@[\w\.-]+\.\w+$')
    
    clean_recipients = []
    seen = set()
    for r in recipients:
        if r:
            r_clean = r.strip().lower()
            if r_clean and r_clean not in seen and valid_email_regex.match(r_clean):
                clean_recipients.append(r_clean)
                seen.add(r_clean)

    # Dispatch concurrently using ThreadPoolExecutor
    import concurrent.futures
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(clean_recipients))) as executor:
        futures = {
            executor.submit(
                _send_single_email_to_recipient,
                registration=registration,
                recipient_email=email,
                email_type=email_type,
                subject=subject,
                html_body=html_body
            ): email
            for email in clean_recipients
        }
        for future in concurrent.futures.as_completed(futures):
            email = futures[future]
            try:
                success = future.result()
                results.append(success)
            except Exception as e:
                logger.error(f"Error executing email send thread for {email}: {e}")
                results.append(False)

    return any(results) if results else False

def send_submission_received_email(registration, db: Session):
    subject = f"Response received: {config.EVENT_NAME} - {registration.registration_id}"
    title = "Response Received Successfully"
    description = "Thank you for registering. Your payment is currently under manual review by our team. We will verify your transaction reference and send a confirmation email once approved."
    html_body = render_email_body(
        registration,
        title=title,
        description=description,
        status_text="Pending Review",
        badge_color="#f59e0b", # Orange/Amber
        message_type="info"
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

    html_body = render_email_body(registration, title=title, description=desc, status_text=status_text, badge_color=color, message_type="info")
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
        badge_color="#22c55e", # Green
        message_type="approved"
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
        badge_color="#ef4444", # Red
        message_type="rejected"
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
        badge_color="#3b82f6", # Blue
        message_type="correction"
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

def send_certificate_email(registration, db: Session):
    subject = f"Thank You for Attending {config.EVENT_NAME} | Your Certificate is Ready"
    
    cert_link = frontend_url(f"certificate.html?token={registration.certificate_token}")

    import json
    reg_type = getattr(registration, "registration_type", "individual")
    team_name_val = getattr(registration, "team_name", None) or "N/A"
    team_lead_name = "N/A"
    teammates_list = []
    total_members = 1

    if reg_type == "team":
        team_info_str = getattr(registration, "team_info", None)
        if team_info_str:
            try:
                team_data = json.loads(team_info_str)
                team_lead_name = team_data.get("team_lead", {}).get("name") or registration.full_name
                members = team_data.get("members", [])
                total_members = len(members) + 1
                for idx, m in enumerate(members):
                    name = m.get("name")
                    email_addr = m.get("email")
                    teammates_list.append(f"{name} ({email_addr})")
            except Exception as e:
                print(f"Error parsing team info in email rendering: {e}")
        else:
            team_lead_name = registration.full_name
            teammates_list = []
    
    # Render Team section if applicable
    team_section_html = ""
    if reg_type == "team":
        member_rows = ""
        for idx, m in enumerate(teammates_list):
            member_rows += f"""
            <tr style="border-top: 1px solid #e2e8f0;">
                <td style="padding: 10px 0; color: #334155; font-size: 13px;">
                    <strong>Member {idx + 2}:</strong> {escape_html(m)}
                </td>
            </tr>
            """
        
        team_section_html = f"""
        <!-- Team Information Card -->
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #f8fafc;">
            <tr>
                <td style="padding: 20px;">
                    <h3 style="margin: 0 0 16px 0; font-size: 13px; color: #475569; text-transform: uppercase; font-weight: 800; letter-spacing: 0.08em; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px;">👥 Team Information</h3>
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="font-size: 14px; margin-bottom: 12px;">
                        <tr>
                            <td style="padding: 6px 0; color: #64748b; font-weight: 500; width: 40%; vertical-align: top;">Team Name:</td>
                            <td style="padding: 6px 0; color: #0f172a; font-weight: 700;">{team_name_val}</td>
                        </tr>
                        <tr>
                            <td style="padding: 6px 0; color: #64748b; font-weight: 500; vertical-align: top;">Team Leader:</td>
                            <td style="padding: 6px 0; color: #0f172a; font-weight: 600;">{team_lead_name}</td>
                        </tr>
                        <tr>
                            <td style="padding: 6px 0; color: #64748b; font-weight: 500; vertical-align: top;">Total Members:</td>
                            <td style="padding: 6px 0; color: #0f172a; font-weight: 600;">{total_members}</td>
                        </tr>
                    </table>
                    
                    <h4 style="margin: 16px 0 8px 0; font-size: 12px; color: #64748b; text-transform: uppercase; font-weight: 800; letter-spacing: 0.05em;">Member List</h4>
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                        {member_rows}
                    </table>
                </td>
            </tr>
        </table>
        """
    
    html_body = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your Certificate is Ready</title>
    <!--[if mso]>
    <style type="text/css">
      body, table, td, p, a, div, h1, h2, h3, span {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important; }}
    </style>
    <![endif]-->
</head>
<body style="margin: 0; padding: 0; -webkit-text-size-adjust: 100%; background-color: #ffffff; color: #0f172a; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
    <div style="max-width: 600px; margin: 0 auto; padding: 24px; background-color: #ffffff;">
        
        <!-- Header -->
        <div style="text-align: center; padding: 24px 0; background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); border-radius: 16px;">
            <h1 style="margin: 0; font-size: 24px; color: #ffffff; letter-spacing: -0.025em; font-weight: 800;">{escape_html(config.ORGANIZER_NAME)}</h1>
            <p style="margin: 5px 0 0 0; font-size: 14px; color: #38bdf8;">{escape_html(config.EVENT_NAME)}</p>
        </div>
        
        <!-- Main Card -->
        <div style="background-color: #ffffff; padding: 32px 24px; border-radius: 16px; border: 1px solid #e2e8f0; border-top: none; margin-top: -10px; box-shadow: 0 4px 12px rgba(0,0,0,0.03);">
            <p style="margin: 0 0 20px 0; font-size: 16px; color: #0f172a;">Hello <strong>{escape_html(registration.full_name)}</strong>,</p>
            
            <p style="margin: 0 0 15px 0; font-size: 15px; color: #475569; line-height: 1.6;">Thank you for attending <strong>{escape_html(config.EVENT_NAME)}</strong>.</p>
            <p style="margin: 0 0 15px 0; font-size: 15px; color: #475569; line-height: 1.6;">We are glad to have you with us during the workshop. Your participation, energy, and performance were truly appreciated by the Sakra Vision team. We hope this event helped you gain valuable knowledge and practical experience.</p>
            <p style="margin: 0 0 25px 0; font-size: 15px; color: #475569; line-height: 1.6;">Your participation certificate is now ready.</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{cert_link}" target="_blank" style="display: inline-block; background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); color: #ffffff; text-decoration: none; padding: 14px 28px; border-radius: 8px; font-weight: bold; font-size: 16px; box-shadow: 0 4px 6px rgba(37,99,235,0.15);">
                    View & Download Certificate
                </a>
            </div>
            
            <!-- Details Card -->
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #f8fafc;">
                <tr>
                    <td style="padding: 20px;">
                        <h3 style="margin: 0 0 15px 0; font-size: 13px; color: #475569; text-transform: uppercase; font-weight: 800; letter-spacing: 0.08em; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px;">📋 Registration Details</h3>
                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="font-size: 14px;">
                            <tr>
                                <td style="padding: 6px 0; color: #64748b; width: 40%; vertical-align: top;">Registration ID:</td>
                                <td style="padding: 6px 0; color: #0f172a; font-weight: 600; font-family: monospace;">{escape_html(registration.registration_id)}</td>
                            </tr>
                            <tr>
                                <td style="padding: 6px 0; color: #64748b; vertical-align: top;">Full Name:</td>
                                <td style="padding: 6px 0; color: #0f172a; font-weight: 600;">{escape_html(registration.full_name)}</td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>

            <!-- Team Details Card (Only if Team) -->
            {team_section_html}
            
            <hr style="border: 0; border-top: 1px solid #e2e8f0; margin: 30px 0 20px 0;">
            
            <p style="margin: 0; color: #64748b; font-size: 14px; line-height: 1.6;">
                Thank you once again for being a part of this event.<br><br>
                Warm regards,<br>
                <strong>Sakra Vision Team</strong><br>
                Event Organization Department<br><br>
                For support, contact:<br>
                Likith Naidu Anumakonda<br>
                9440113763
            </p>
        </div>
    </div>
</body>
</html>
"""
    return _send_email_api_call(db, registration, "certificate", subject, html_body)


def send_admin_user_credentials_email(email_to: str, temp_password: str, db: Session):
    subject = "Your Account Has Been Created"
    login_url = f"{config.FRONTEND_URL}/admin-login.html"
    
    html_body = f"""
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px; background-color: #ffffff; color: #1a202c;">
        <h2 style="color: #4f46e5; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px;">Account Created Successfully</h2>
        <p>Hello,</p>
        <p>An administrative account has been created for you with full privileges.</p>
        <table style="width: 100%; margin: 20px 0; border-collapse: collapse; background-color: #f7fafc; border-radius: 6px;">
            <tr>
                <td style="padding: 12px; font-weight: bold; border: 1px solid #edf2f7; width: 30%;">Login Email:</td>
                <td style="padding: 12px; border: 1px solid #edf2f7;">{email_to}</td>
            </tr>
            <tr>
                <td style="padding: 12px; font-weight: bold; border: 1px solid #edf2f7;">Temporary Password:</td>
                <td style="padding: 12px; border: 1px solid #edf2f7; font-family: monospace; font-size: 16px; color: #e53e3e;">{temp_password}</td>
            </tr>
            <tr>
                <td style="padding: 12px; font-weight: bold; border: 1px solid #edf2f7;">Login URL:</td>
                <td style="padding: 12px; border: 1px solid #edf2f7;"><a href="{login_url}" style="color: #4f46e5; text-decoration: none; font-weight: 600;">Access Admin Portal</a></td>
            </tr>
        </table>
        <div style="background-color: #fffaf0; border-left: 4px solid #dd6b20; padding: 15px; margin: 20px 0; border-radius: 4px;">
            <p style="margin: 0; font-weight: bold; color: #dd6b20;">Important Security Notice:</p>
            <p style="margin: 5px 0 0 0;">You will be forced to change your password immediately upon your first login. Please keep your temporary credentials secure.</p>
        </div>
        <p style="margin-top: 30px; font-size: 12px; color: #a0aec0; border-top: 1px solid #e2e8f0; padding-top: 15px;">This is an automated message. Please do not reply directly to this email.</p>
    </div>
    """
    
    # Check key and simulate if needed
    if not config.RESEND_API_KEY or config.RESEND_API_KEY.startswith("re_xxx") or not config.RESEND_API_KEY.strip():
        print(f"\\n--- [EMAIL SIMULATION: ADMIN CREATED USER] ---")
        print(f"To: {email_to}")
        print(f"Subject: {subject}")
        print(f"Temp Password: {temp_password}")
        print("API Key not configured or placeholder. Treating as simulated SUCCESS.")
        print("-------------------------------------------\\n")
        
        log_email_result(
            db=db,
            registration_id="ADMIN_USER_CREATE",
            email_to=email_to,
            email_type="admin_user_created",
            subject=subject,
            status="SENT",
            resend_message_id="simulated_id_" + secrets.token_hex(8)
        )
        return True

    try:
        response = resend.Emails.send({
            "from": config.FROM_EMAIL,
            "to": email_to,
            "subject": subject,
            "html": html_body
        })
        message_id = response.get("id")
        log_email_result(
            db=db,
            registration_id="ADMIN_USER_CREATE",
            email_to=email_to,
            email_type="admin_user_created",
            subject=subject,
            status="SENT",
            resend_message_id=message_id
        )
        return True
    except Exception as e:
        logger.error(f"Resend email sending failed for admin user {email_to}: {e}")
        log_email_result(
            db=db,
            registration_id="ADMIN_USER_CREATE",
            email_to=email_to,
            email_type="admin_user_created",
            subject=subject,
            status="FAILED",
            error_message=str(e)
        )
        return False
