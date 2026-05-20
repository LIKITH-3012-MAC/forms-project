# Forms Project: Premium Event Registration Platform

A production-grade, highly secure, and visually stunning alternative to standard forms. Featuring a unified, dark-mode tactile neumorphism design system, manual UPI QR payment, MySQL data structures, Resend email automations, and a robust admin dashboard.

## 🚀 Key Features

*   **Premium Neumorphic Design**: Built using high-refresh-rate 144Hz optimized micro-animations, glassmorphism layers, and responsive CSS variables.
*   **Manual UPI QR Code Payments**: Integrates custom UPI URI schemes (`upi://pay`) and static QR generation with validation constraints.
*   **Global Error Handling**: Comprehensive FastAPI exception handlers that gracefully redirect users to a custom `/problem` screen while logging diagnostics in the database.
*   **Admin CRM Dashboard**: Real-time stats, state filters, details history, CSV export, Resend email triggers, and edit lock policies.
*   **Security & Safety**: Complete block on direct HTML file jumping, hidden system stack traces, and database auditing logs.

## 🛠️ Tech Stack

*   **Backend**: Python, FastAPI, Uvicorn, SQLAlchemy
*   **Database**: MySQL / SQLite (development fallback)
*   **Frontend**: Vanilla HTML5, CSS3, ES6 JavaScript
*   **Services**: Resend Email API

## 📋 Getting Started

### 1. Installation
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Running the Server
```bash
uvicorn main:app --reload
```
The server will start at `http://127.0.0.1:8000`.
