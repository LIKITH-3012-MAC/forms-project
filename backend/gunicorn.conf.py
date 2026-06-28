"""
Gunicorn Configuration
======================
Production-ready Gunicorn settings for the Sakra Forms backend.
Uses Uvicorn workers for ASGI support with sensible defaults
for concurrency, timeouts, and request recycling.
"""

import multiprocessing

# --- Server Socket ---
bind = "0.0.0.0:8000"

# --- Worker Processes ---
workers = min(multiprocessing.cpu_count() * 2 + 1, 8)
worker_class = "uvicorn.workers.UvicornWorker"

# --- Timeouts ---
keepalive = 120
timeout = 120
graceful_timeout = 30

# --- Worker Recycling (prevents memory leaks) ---
max_requests = 1000
max_requests_jitter = 50

# --- Logging ---
accesslog = "-"
errorlog = "-"
loglevel = "info"

# --- Performance ---
preload_app = True
