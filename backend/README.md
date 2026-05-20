# Premium Event Registration Platform (Google Forms Alternative)

A complete, production-grade event registration system built using **FastAPI** and **MySQL**. It features manual UPI payment verification (via QR codes/UTR references), Resend email automation, security controls, live timelines, response editing links, and a premium cyber-dark administrative CRM panel.

---

## 🛠️ System Architecture

This project strictly adheres to a **zero-template engine rule (no Jinja2, no templates folder)**.
- **Single Page Frontend**: The form filling interface is served entirely from a single static physical HTML file: `static/form.html`.
- **Backend-Driven Interface Generation**: All downstream screens (Thank You page, Response View Copy, Live Timeline, Response Editing form, Admin Login, Admin detail pages, and Error panels) are constructed on the fly inside FastAPI routes using Python string rendering methods via `HTMLResponse`. This provides unified state-rendering from backend data and eliminates standard templating complexities.
- **Manual Payment Verification Pattern**:
  - The client makes a manual transaction using their preferred UPI app (PhonePe/GPay/Paytm) by scanning the event QR code.
  - The user enters their unique UPI/UTR transaction reference ID on submission.
  - The payment status is set to `PENDING_REVIEW` and registration to `SUBMITTED`.
  - Administrators review the transaction in their banking app and manually Approve, Reject, or request Correction in the admin console.

---

## 📂 Project Structure

```
event-registration-fastapi/
├── main.py                 # Core routing, validations, session controls
├── config.py               # Env configuration loading & defaults
├── database.py             # Database engine & fallback session configuration
├── models.py               # SQLAlchemy ORM schemas (Registration, Audits, EmailLogs)
├── schemas.py              # Pydantic validation rules and string normalization
├── email_service.py        # Resend API email rendering and delivery logics
├── security.py             # Secure cookie session serializer
├── html_pages.py           # Backend page shell and string-rendered HTML pages
├── utils.py                # Unique ID generators and XSS protection helpers
├── requirements.txt        # Python dependency specifications
├── .env.example            # Environment configuration template
├── render.yaml             # Render deployment configuration
├── README.md               # User guide
└── static/
    ├── form.html           # Unified registration intake form
    ├── payment-qr.png      # Event payment QR code (Scan to pay)
    └── logo.png            # Organizer branding logo
```

---

## 🚀 Setup & Installation Instructions

### 1. Configure the Environment
Clone the repository and copy the environment template:
```bash
cp .env.example .env
```
Open `.env` and configure your credentials:
- **`ADMIN_SECRET`**: Password for admin portal access.
- **`SECRET_KEY`**: Cryptographic seed to sign cookie sessions securely.
- **`RESEND_API_KEY`**: Retrieve this from your Resend Dashboard.
- **`EVENT_AMOUNT`**: Set registration amount.
- **`UPI_ID`**: Your destination UPI address.

### 2. Set Up Virtual Environment & Dependencies
Create a virtual environment and install standard requirements:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Setup MySQL Database
Ensure MySQL is running on your host and create the database specified in your `.env` configuration:
```sql
CREATE DATABASE event_db;
```
*Note: If no MySQL database is running, the application will automatically fall back to SQLite (`fallback_event_db.db`) in `development` mode for local evaluation.*

### 4. Setup QR Assets
Ensure your payment QR code and logo are placed inside the static directory:
- `static/payment-qr.png`
- `static/logo.png`

---

## 🏃 Running the Application

Start the local development server:
```bash
uvicorn main:app --reload
```

- **User Registration Intake Form**: [http://localhost:8000/form](http://localhost:8000/form)
- **Administrative Portal Dashboard**: [http://localhost:8000/admin/login](http://localhost:8000/admin/login)
- **Health Check Endpoint**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 🛡️ Administrative Manual Payment Approval Workflow

1. A participant submits the form with their UPI UTR reference ID.
2. The system triggers a confirmation email to the participant indicating that verification is pending review.
3. The administrator logs into the **Admin CRM Portal** (`/admin/login`).
4. On the dashboard, pending registrations appear at the top of the table.
5. Clicking **View** on a record shows the participant details, audit log, and payment screenshot if provided.
6. The administrator verifies the receipt of the corresponding fee using GPay/PhonePe or the bank statement.
7. Action options:
   - **Approve**: Confirms the seat, locks the response from further edits, and sends a final receipt confirmation email.
   - **Reject**: Marks the payment as invalid, unlocks details for updating, and sends a warning email with editing links.
   - **Needs Correction**: Sends an email requesting details correction (e.g. invalid UTR or screenshot upload error), keeping editing access unlocked.

---

## 🎨 Premium Visual Elements

- **Theme**: Unified dark-mode styling utilizing high-contrast violet and blue neon glow schemes.
- **Interactive Forms**: A multi-step form stepper (Details -> Payment -> Confirm) with localStorage persistence to prevent data loss on browser refresh.
- **Asynchronous Checks**: Automatic client-side UTR validation using debounce calls to verify reference uniqueness before submission.
- **Security Protections**: Built-in HTML sanitization routines to prevent XSS injection, secure cookie signing, audit logging, and deadline/seat checks.
