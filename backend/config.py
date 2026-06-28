import os
from dotenv import load_dotenv

# Load env variables from .env if present
load_dotenv()

APP_NAME = os.getenv("APP_NAME", "Event Registration System")
BASE_URL = os.getenv("BASE_URL", "https://forms-project-1-xe3v.onrender.com").rstrip("/")
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://forms-project-f3sb.vercel.app").rstrip("/")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")
DB_NAME = os.getenv("DB_NAME", "event_db")

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
OMNI_API_KEY = os.getenv("OMNIDIM_API_KEY") or os.getenv("OMNI_API_KEY") or ""
OMNI_AGENT_ID = os.getenv("OMNIDIM_AGENT_ID") or os.getenv("OMNI_AGENT_ID") or ""
FROM_EMAIL = os.getenv("FROM_EMAIL", "events@yourdomain.com")

ADMIN_SECRET = os.getenv("ADMIN_SECRET", "change_this_admin_password")
SECRET_KEY = os.getenv("SECRET_KEY", "change_this_super_secret_key")

EVENT_NAME = os.getenv("EVENT_NAME", "AI Workshop 2026")
EVENT_SUBTITLE = os.getenv("EVENT_SUBTITLE", "Build AI systems from idea to deployment")
EVENT_DESCRIPTION = os.getenv("EVENT_DESCRIPTION", "Hands-on AI workshop covering Generative AI, AI Agents, LLMs, Computer Vision, and Automation.")
EVENT_AMOUNT = int(os.getenv("EVENT_AMOUNT", "700"))
EVENT_DEADLINE = os.getenv("EVENT_DEADLINE", "2026-08-01 23:59:59")
EVENT_SEATS_TOTAL = int(os.getenv("EVENT_SEATS_TOTAL", "200"))
UPI_ID = os.getenv("UPI_ID", "yourupi@bank")
ORGANIZER_NAME = os.getenv("ORGANIZER_NAME", "SAKRA VISION")
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "support@yourdomain.com")

ALLOW_DUPLICATE_EMAIL = os.getenv("ALLOW_DUPLICATE_EMAIL", "false").lower() in ("true", "1", "yes")
LOCK_EDIT_AFTER_APPROVAL = os.getenv("LOCK_EDIT_AFTER_APPROVAL", "true").lower() in ("true", "1", "yes")

# CAPTCHA configuration
CAPTCHA_SECRET_KEY = os.getenv("CAPTCHA_SECRET_KEY", "")
CAPTCHA_VERIFY_URL = os.getenv("CAPTCHA_VERIFY_URL", "https://challenges.cloudflare.com/turnstile/v0/siteverify")
CAPTCHA_SECRET_TOKEN = os.getenv("CAPTCHA_SECRET_TOKEN", "")

