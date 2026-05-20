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

## 🎨 Favicon Setup

The custom-designed premium Favicon and App Icon System is fully configured inside the `frontend/` directory.

### Icon Assets Included:
- `frontend/assets/favicon.svg`: The source scalable vector icon using glowing neon accents and linear gradients.
- `frontend/assets/favicon.ico`: Fallback ICO file containing multi-size resolutions (16px, 32px, 48px, etc.).
- `frontend/assets/apple-touch-icon.png`: Apple-specific app touch icon (180x180).
- `frontend/assets/icon-192.png`: PWA standard icon (192x192).
- `frontend/assets/icon-512.png`: PWA standard high-resolution splash icon (512x512).
- `frontend/assets/site.webmanifest`: Standard Web App Manifest specifying short name, theme colors, and icons.

### Configuration:
1. **HTML Integration**: Every frontend page has the absolute path tags embedded in its `<head>` structure.
2. **PWA Enabled**: Built-in support for Android/iOS standalone homescreen launching with theme color `#0f172a`.
3. **Regeneration (Optional)**: If you ever want to update the icons from a new SVG, simply run the Python image generator utility at `scratch/generate_icons.py` or compile via [RealFaviconGenerator](https://realfavicongenerator.net/).
