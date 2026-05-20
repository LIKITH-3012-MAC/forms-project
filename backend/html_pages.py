import json
import datetime
from utils import escape_html, format_datetime
import config

def page_shell(title: str, body: str, extra_css: str = "", extra_js: str = "") -> str:
    """Returns a full premium HTML document with a cohesive dark-mode design system."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(title)} - {escape_html(config.APP_NAME)}</title>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
    
    <!-- Design Tokens / Core Styling -->
    <style>
        :root {{
            /* Unified responsive variables */
            --bg: #080b11;
            --surface: rgba(17, 24, 39, 0.7);
            --surface-2: #111827;
            --border: rgba(255, 255, 255, 0.08);
            
            --primary: #8b5cf6;
            --primary-glow: rgba(139, 92, 246, 0.15);
            --primary-2: #3b82f6;
            --accent: #d946ef;
            
            --text: #f3f4f6;
            --muted: #9ca3af;
            --text-dark: #6b7280;
            
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --info: #3b82f6;
            
            --radius-sm: 8px;
            --radius-md: 14px;
            --radius-lg: 20px;
            
            --shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            
            --space-1: 4px;
            --space-2: 8px;
            --space-3: 12px;
            --space-4: 16px;
            --space-5: 20px;
            --space-6: 24px;
            --space-7: 32px;
            --space-8: 40px;
            
            --ease-out-expo: cubic-bezier(0.16, 1, 0.3, 1);
            --ease-out-back: cubic-bezier(0.34, 1.56, 0.64, 1);
            --transition: all 0.4s var(--ease-out-expo);
            --transition-bounce: all 0.5s var(--ease-out-back);
            
            /* Neumorphism design tokens */
            --neo-bg: rgba(255, 255, 255, 0.08);
            --neo-bg-strong: rgba(255, 255, 255, 0.13);
            --neo-border: rgba(255, 255, 255, 0.16);
            --neo-highlight: rgba(255, 255, 255, 0.35);
            --neo-shadow-dark: rgba(0, 0, 0, 0.45);
            --neo-shadow-light: rgba(255, 255, 255, 0.08);
            --neo-primary: #38bdf8;
            --neo-primary-2: #8b5cf6;
            --neo-success: #22c55e;
            --neo-danger: #ef4444;
            --neo-warning: #f59e0b;
            --neo-radius: 18px;
            
            /* Alias variables for backward compatibility */
            --bg-base: var(--bg);
            --bg-surface: var(--surface);
            --bg-card: var(--surface-2);
            --border-color: var(--border);
            --text-main: var(--text);
            --text-muted: var(--muted);
            --secondary: var(--primary-2);
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            background-color: var(--bg);
            color: var(--text);
            font-family: 'Outfit', sans-serif;
            min-height: 100dvh;
            display: flex;
            flex-direction: column;
            overflow-x: hidden;
            position: relative;
        }}

        /* Subtle animated background grid/blobs */
        body::before {{
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-image: 
                radial-gradient(circle at 10% 20%, rgba(139, 92, 246, 0.08) 0%, transparent 40%),
                radial-gradient(circle at 90% 80%, rgba(59, 130, 246, 0.08) 0%, transparent 40%);
            z-index: -1;
            pointer-events: none;
        }}

        header {{
            padding: var(--space-4) 5%;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
            background-color: rgba(8, 11, 17, 0.8);
            backdrop-filter: blur(10px);
            position: sticky;
            top: 0;
            z-index: 100;
        }}

        .logo {{
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 700;
            font-size: 20px;
            background: linear-gradient(135deg, #ffffff 30%, #a855f7 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .logo-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: var(--primary);
            box-shadow: 0 0 10px var(--primary);
        }}

        main {{
            flex: 1;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: var(--space-5) 16px;
            width: 100%;
        }}

        footer {{
            padding: var(--space-4);
            text-align: center;
            font-size: 13px;
            color: var(--text-dark);
            border-top: 1px solid var(--border);
            background-color: rgba(8, 11, 17, 0.9);
            margin-top: auto;
        }}

        /* Universal text wrapping for long strings */
        .val, td, th, p, h1, h2, h3, a, span, strong, div {{
            overflow-wrap: anywhere;
        }}

        /* Prevent interactive elements overflow */
        input, select, textarea, button, .card, table, img {{
            max-width: 100%;
        }}

        img {{
            height: auto;
        }}

        /* Buttons & Badges */
        /* Neumorphism Buttons Styling */
        .neo-btn {{
            position: relative;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            min-height: 48px;
            padding: 12px 20px;
            border: 1px solid var(--neo-border);
            border-radius: var(--neo-radius);
            background:
                linear-gradient(145deg, rgba(255,255,255,0.13), rgba(255,255,255,0.04));
            color: var(--text);
            font-weight: 800;
            letter-spacing: 0.01em;
            cursor: pointer;
            user-select: none;
            text-decoration: none;
            box-shadow:
                10px 10px 24px var(--neo-shadow-dark),
                -8px -8px 20px var(--neo-shadow-light),
                inset 1px 1px 0 var(--neo-highlight);
            transition:
                transform 180ms ease,
                box-shadow 180ms ease,
                border-color 180ms ease,
                background 180ms ease,
                filter 180ms ease;
            overflow: hidden;
            font-family: inherit;
            width: 100%;
        }}

        .neo-btn::before {{
            content: "";
            position: absolute;
            inset: 0;
            background:
                radial-gradient(circle at 30% 20%, rgba(255,255,255,0.28), transparent 32%),
                linear-gradient(120deg, transparent, rgba(255,255,255,0.12), transparent);
            opacity: 0;
            transition: opacity 180ms ease;
            pointer-events: none;
        }}

        @media (hover: hover) {{
            .neo-btn:hover {{
                transform: translateY(-2px);
                border-color: rgba(56,189,248,0.45);
                filter: brightness(1.08);
                box-shadow:
                    14px 14px 32px rgba(0,0,0,0.52),
                    -10px -10px 24px rgba(255,255,255,0.10),
                    0 0 28px rgba(56,189,248,0.18),
                    inset 1px 1px 0 rgba(255,255,255,0.35);
            }}

            .neo-btn:hover::before {{
                opacity: 1;
            }}
        }}

        .neo-btn:active {{
            transform: translateY(1px) scale(0.99);
            box-shadow:
                inset 8px 8px 18px rgba(0,0,0,0.40),
                inset -6px -6px 14px rgba(255,255,255,0.08),
                0 0 18px rgba(56,189,248,0.10);
        }}

        .neo-btn:focus-visible {{
            outline: 3px solid rgba(56,189,248,0.55);
            outline-offset: 3px;
        }}

        .neo-btn:disabled,
        .neo-btn[aria-disabled="true"] {{
            opacity: 0.55;
            cursor: not-allowed;
            transform: none !important;
            filter: grayscale(0.3);
            box-shadow:
                6px 6px 16px var(--neo-shadow-dark),
                -4px -4px 12px var(--neo-shadow-light);
        }}

        /* Legacy .btn compatibility wrapper */
        .btn {{
            position: relative;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            min-height: 48px;
            padding: 12px 20px;
            border: 1px solid var(--neo-border);
            border-radius: var(--neo-radius);
            background:
                linear-gradient(145deg, rgba(255,255,255,0.13), rgba(255,255,255,0.04));
            color: var(--text);
            font-weight: 800;
            letter-spacing: 0.01em;
            cursor: pointer;
            user-select: none;
            text-decoration: none;
            box-shadow:
                10px 10px 24px var(--neo-shadow-dark),
                -8px -8px 20px var(--neo-shadow-light),
                inset 1px 1px 0 var(--neo-highlight);
            transition:
                transform 180ms ease,
                box-shadow 180ms ease,
                border-color 180ms ease,
                background 180ms ease,
                filter 180ms ease;
            overflow: hidden;
            font-family: inherit;
            width: 100%;
        }}

        .btn::before {{
            content: "";
            position: absolute;
            inset: 0;
            background:
                radial-gradient(circle at 30% 20%, rgba(255,255,255,0.28), transparent 32%),
                linear-gradient(120deg, transparent, rgba(255,255,255,0.12), transparent);
            opacity: 0;
            transition: opacity 180ms ease;
            pointer-events: none;
        }}

        @media (hover: hover) {{
            .btn:hover {{
                transform: translateY(-2px);
                border-color: rgba(56,189,248,0.45);
                filter: brightness(1.08);
                box-shadow:
                    14px 14px 32px rgba(0,0,0,0.52),
                    -10px -10px 24px rgba(255,255,255,0.10),
                    0 0 28px rgba(56,189,248,0.18),
                    inset 1px 1px 0 rgba(255,255,255,0.35);
            }}
            .btn:hover::before {{
                opacity: 1;
            }}
        }}

        .btn:active {{
            transform: translateY(1px) scale(0.99);
            box-shadow:
                inset 8px 8px 18px rgba(0,0,0,0.40),
                inset -6px -6px 14px rgba(255,255,255,0.08),
                0 0 18px rgba(56,189,248,0.10);
        }}

        .btn:focus-visible {{
            outline: 3px solid rgba(56,189,248,0.55);
            outline-offset: 3px;
        }}

        .btn:disabled,
        .btn[aria-disabled="true"] {{
            opacity: 0.55;
            cursor: not-allowed;
            transform: none !important;
            filter: grayscale(0.3);
        }}

        /* Variants */
        .neo-btn-primary, .btn-primary {{
            color: #ffffff !important;
            background:
                linear-gradient(135deg, rgba(56,189,248,0.95), rgba(139,92,246,0.95)) !important;
            border-color: rgba(255,255,255,0.24) !important;
            box-shadow:
                12px 12px 28px rgba(0,0,0,0.50),
                -8px -8px 22px rgba(255,255,255,0.09),
                0 0 30px rgba(56,189,248,0.24),
                inset 1px 1px 0 rgba(255,255,255,0.40) !important;
        }}

        .neo-btn-secondary, .btn-secondary {{
            color: var(--text) !important;
            background: linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0.03)) !important;
            border-color: rgba(255,255,255,0.12) !important;
            box-shadow:
                8px 8px 20px rgba(0,0,0,0.40),
                -6px -6px 16px rgba(255,255,255,0.06),
                inset 1px 1px 0 rgba(255,255,255,0.2) !important;
        }}

        @media (hover: hover) {{
            .neo-btn-secondary:hover, .btn-secondary:hover {{
                border-color: rgba(56,189,248,0.3) !important;
                box-shadow:
                    10px 10px 24px rgba(0,0,0,0.45),
                    -8px -8px 20px rgba(255,255,255,0.08),
                    0 0 20px rgba(56,189,248,0.1),
                    inset 1px 1px 0 rgba(255,255,255,0.25) !important;
            }}
        }}

        .neo-btn-success, .btn-success {{
            color: #ffffff !important;
            background: linear-gradient(135deg, rgba(34,197,94,0.9), rgba(16,185,129,0.9)) !important;
            border-color: rgba(255,255,255,0.2) !important;
            box-shadow:
                10px 10px 24px rgba(0,0,0,0.45),
                -8px -8px 20px rgba(255,255,255,0.08),
                0 0 24px rgba(34,197,94,0.25),
                inset 1px 1px 0 rgba(255,255,255,0.3) !important;
        }}

        .neo-btn-danger, .btn-danger {{
            color: #ffffff !important;
            background: linear-gradient(135deg, rgba(239,68,68,0.9), rgba(220,38,38,0.9)) !important;
            border-color: rgba(255,255,255,0.2) !important;
            box-shadow:
                10px 10px 24px rgba(0,0,0,0.45),
                -8px -8px 20px rgba(255,255,255,0.08),
                0 0 24px rgba(239,68,68,0.25),
                inset 1px 1px 0 rgba(255,255,255,0.3) !important;
        }}

        .neo-btn-warning, .btn-warning {{
            color: #ffffff !important;
            background: linear-gradient(135deg, rgba(245,158,11,0.9), rgba(217,119,6,0.9)) !important;
            border-color: rgba(255,255,255,0.2) !important;
            box-shadow:
                10px 10px 24px rgba(0,0,0,0.45),
                -8px -8px 20px rgba(255,255,255,0.08),
                0 0 24px rgba(245,158,11,0.25),
                inset 1px 1px 0 rgba(255,255,255,0.3) !important;
        }}

        .neo-btn-ghost, .btn-ghost {{
            color: var(--text) !important;
            background: transparent !important;
            border-color: transparent !important;
            box-shadow: none !important;
        }}
        @media (hover: hover) {{
            .neo-btn-ghost:hover, .btn-ghost:hover {{
                background: rgba(255,255,255,0.05) !important;
                border-color: var(--neo-border) !important;
                box-shadow:
                    6px 6px 16px rgba(0,0,0,0.3),
                    -4px -4px 12px rgba(255,255,255,0.04) !important;
            }}
        }}

        .neo-btn-icon {{
            width: 46px !important;
            height: 46px !important;
            min-height: 46px !important;
            padding: 0 !important;
            border-radius: 16px !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
        }}

        .neo-btn-wide {{
            min-width: 180px;
        }}

        @media (max-width: 639px) {{
            .neo-btn, .btn {{
                width: 100% !important;
                min-height: 50px;
                padding: 13px 16px;
                border-radius: 18px;
            }}
            .button-row, .action-row, .btn-panel {{
                display: grid !important;
                grid-template-columns: 1fr !important;
                gap: 10px !important;
            }}
        }}

        @media (min-width: 640px) {{
            .btn {{
                width: auto;
            }}
        }}

        @media (min-width: 768px) {{
            .button-row, .action-row, .btn-panel {{
                display: flex !important;
                align-items: center !important;
                justify-content: space-between !important;
                gap: 12px !important;
                flex-wrap: wrap !important;
                flex-direction: row !important;
            }}
            .neo-btn {{
                width: auto !important;
            }}
        }}

        .badge {{
            display: inline-block;
            padding: 4px 12px;
            font-size: 11px;
            font-weight: 700;
            border-radius: 9999px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}

        .badge-pending {{
            background-color: rgba(245, 158, 11, 0.15);
            color: var(--warning);
            border: 1px solid rgba(245, 158, 11, 0.3);
        }}

        .badge-approved {{
            background-color: rgba(16, 185, 129, 0.15);
            color: var(--success);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }}

        .badge-rejected {{
            background-color: rgba(239, 68, 68, 0.15);
            color: var(--danger);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }}

        .badge-correction {{
            background-color: rgba(59, 130, 246, 0.15);
            color: var(--info);
            border: 1px solid rgba(59, 130, 246, 0.3);
        }}

        /* Forms Layout & Cards */
        .card {{
            background-color: var(--surface-2);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: var(--space-5);
            width: 100%;
            max-width: 650px;
            box-shadow: var(--shadow);
            backdrop-filter: blur(12px);
            animation: fadeIn 0.4s ease-out;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(15px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* Horizontal Scrollable Table Wrapper */
        .table-scroll, .table-container {{
            width: 100%;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
            border: 1px solid var(--border);
            border-radius: var(--radius-sm);
        }}

        /* Stacking elements helper */
        .responsive-action-grid {{
            display: grid;
            grid-template-columns: 1fr;
            gap: var(--space-2);
        }}

        @media (min-width: 640px) {{
            .responsive-action-grid {{
                grid-template-columns: 1fr 1fr;
            }}
        }}

        /* Lenis Smooth Scroll styles */
        html.lenis {{
            height: auto;
        }}
        .lenis.lenis-smooth {{
            scroll-behavior: auto !important;
        }}
        .lenis.lenis-smooth [data-lenis-prevent] {{
            overflow: clip;
        }}
        .lenis.lenis-stopped {{
            overflow: hidden;
        }}
        .lenis.lenis-scrolling iframe {{
            pointer-events: none;
        }}

        {extra_css}
    </style>
</head>
<body>
    <header>
        <a href="/form" class="logo">
            <div class="logo-dot"></div>
            {escape_html(config.ORGANIZER_NAME)}
        </a>
        <div style="font-size: 13px; color: var(--muted);">
            {escape_html(config.EVENT_NAME)}
        </div>
    </header>

    <main>
        {body}
    </main>

    <footer>
        &copy; {datetime.datetime.now().year} {escape_html(config.ORGANIZER_NAME)}. All rights reserved.
    </footer>

    <!-- Lenis Smooth Scroll -->
    <script src="https://cdn.jsdelivr.net/npm/@studio-freight/lenis@1.0.42/dist/lenis.min.js"></script>
    <script>
        // Initialize Lenis smooth scrolling optimized for high refresh rates (144Hz+)
        const lenis = new Lenis({{
            duration: 1.2,
            easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
            direction: 'vertical',
            gestureDirection: 'vertical',
            smooth: true,
            mouseMultiplier: 1,
            smoothTouch: false,
            touchMultiplier: 2,
            infinite: false,
        }});

        function raf(time) {{
            lenis.raf(time);
            requestAnimationFrame(raf);
        }}

        // Native requestAnimationFrame runs at the monitor's native refresh rate (up to 144Hz/240Hz+)
        requestAnimationFrame(raf);
    </script>

    {extra_js}
</body>
</html>
"""

def render_thank_you_html(registration) -> str:
    """Generates the thank you screen."""
    reg_id = escape_html(registration.registration_id)
    status_token = escape_html(registration.status_token)
    edit_token = escape_html(registration.edit_token)
    view_token = escape_html(registration.view_token)

    body = f"""
    <div class="card" style="text-align: center;">
        <!-- Success Tick Icon Animation -->
        <div class="success-checkmark">
            <div class="check-icon">
                <span class="icon-line line-tip"></span>
                <span class="icon-line line-long"></span>
                <div class="icon-circle"></div>
                <div class="icon-fix"></div>
            </div>
        </div>

        <h1 style="font-size: 26px; margin: 20px 0 10px 0; font-family: 'Space Grotesk', sans-serif;">Submission Received!</h1>
        <p style="color: var(--text-muted); font-size: 15px; margin-bottom: 25px; line-height: 1.5;">
            Thank you, <strong>{escape_html(registration.full_name)}</strong>! Your details have been submitted. An email confirmation has been triggered to <strong>{escape_html(registration.email)}</strong>.
        </p>

        <div style="background-color: rgba(255,255,255,0.02); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 15px; margin-bottom: 30px; text-align: left;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px;">
                <span style="color: var(--text-muted);">Registration ID:</span>
                <span style="font-family: monospace; font-weight: 700; color: var(--primary);">{reg_id}</span>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 14px;">
                <span style="color: var(--text-muted);">Payment Status:</span>
                <span class="badge badge-pending">Pending Review</span>
            </div>
        </div>

        <div style="display: flex; flex-direction: column; gap: 12px;">
            <a href="/status/{status_token}" class="btn btn-primary">
                <svg width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"></path></svg>
                Check Status 📍
            </a>
            <div class="responsive-action-grid">
                <a href="/r/{view_token}" class="btn btn-secondary" style="font-size: 13px;">
                    View Response 👁
                </a>
                <a href="/edit/{edit_token}" class="btn btn-secondary" style="font-size: 13px;">
                    Edit Response ✏️
                </a>
            </div>
            <a href="/form" class="btn btn-secondary" style="margin-top: 10px; border-style: dashed;">
                Submit Another Response ➕
            </a>
        </div>
    </div>
    """
    
    extra_css = """
        /* Checkmark Animation */
        .success-checkmark {
            width: 80px;
            height: 80px;
            margin: 0 auto 20px auto;
        }
        .success-checkmark .check-icon {
            width: 80px;
            height: 80px;
            position: relative;
            border-radius: 50%;
            box-sizing: content-box;
            border: 4px solid var(--success);
        }
        .success-checkmark .check-icon::after {
            content: '';
            position: absolute;
            background: transparent;
            z-index: 1;
        }
        .success-checkmark .check-icon .icon-line {
            height: 5px;
            background-color: var(--success);
            display: block;
            border-radius: 2px;
            position: absolute;
            z-index: 10;
        }
        .success-checkmark .check-icon .icon-line.line-tip {
            top: 46px;
            left: 19px;
            width: 25px;
            transform: rotate(45deg);
            animation: icon-line-tip 0.75s;
        }
        .success-checkmark .check-icon .icon-line.line-long {
            top: 38px;
            right: 17px;
            width: 47px;
            transform: rotate(-45deg);
            animation: icon-line-long 0.75s;
        }
        .success-checkmark .check-icon .icon-circle {
            top: -4px;
            left: -4px;
            z-index: 10;
            width: 80px;
            height: 80px;
            border-radius: 50%;
            box-sizing: content-box;
            border: 4px solid rgba(16, 185, 129, .2);
            position: absolute;
        }
        @keyframes icon-line-tip {
            0% { width: 0; left: 1px; top: 19px; }
            54% { width: 0; left: 1px; top: 19px; }
            70% { width: 50px; left: -8px; top: 37px; }
            84% { width: 17px; left: 21px; top: 48px; }
            100% { width: 25px; left: 19px; top: 46px; }
        }
        @keyframes icon-line-long {
            0% { width: 0; right: 46px; top: 54px; }
            65% { width: 0; right: 46px; top: 54px; }
            84% { width: 55px; right: 0px; top: 35px; }
            100% { width: 47px; right: 17px; top: 38px; }
        }
    """
    return page_shell("Thank You", body, extra_css)


def render_view_response_html(registration) -> str:
    """Generates the view response page (Google Forms format summary)."""
    status = registration.payment_status
    if status == "APPROVED":
        badge = '<span class="badge badge-approved">Approved / Confirmed</span>'
    elif status == "REJECTED":
        badge = '<span class="badge badge-rejected">Rejected</span>'
    elif status == "NEEDS_CORRECTION":
        badge = '<span class="badge badge-correction">Needs Correction</span>'
    else:
        badge = '<span class="badge badge-pending">Pending Review</span>'

    # Display lock status message
    lock_badge = ""
    if registration.is_edit_locked:
        lock_badge = '<div style="margin-top: 10px; font-size:12px; color: var(--danger); font-weight:600;">🔒 Editing Locked</div>'

    # Admin note display
    admin_note_section = ""
    if registration.admin_note:
        admin_note_section = f"""
        <div style="background-color: rgba(239, 68, 68, 0.05); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: var(--radius-sm); padding: 15px; margin-bottom: 25px; text-align: left;">
            <div style="font-size: 12px; color: var(--danger); font-weight: 700; text-transform: uppercase; margin-bottom: 4px;">Admin Note:</div>
            <div style="font-size: 14px; color: #fca5a5; line-height: 1.4;">{escape_html(registration.admin_note)}</div>
        </div>
        """

    screenshot_section = ""
    if registration.payment_screenshot_url:
        screenshot_section = f"""
        <div style="margin-top: 8px;">
            <a href="{escape_html(registration.payment_screenshot_url)}" target="_blank" style="color: var(--primary); text-decoration: none; font-size: 13px; font-weight: 500; display: inline-flex; align-items: center; gap: 4px;">
                <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                View Uploaded Image
            </a>
        </div>
        """

    body = f"""
    <div class="card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid var(--border-color); padding-bottom: 15px; margin-bottom: 20px;">
            <div>
                <h1 style="font-size: 24px; font-family: 'Space Grotesk', sans-serif;">Response Summary</h1>
                <p style="font-size: 12px; color: var(--text-dark); margin-top: 4px;">Registered on: {format_datetime(registration.created_at)}</p>
            </div>
            <div style="text-align: right;">
                {badge}
                {lock_badge}
            </div>
        </div>

        {admin_note_section}

        <div class="form-display-grid">
            <div class="display-row">
                <span class="label">Full Name</span>
                <span class="val">{escape_html(registration.full_name)}</span>
            </div>
            <div class="display-row">
                <span class="label">Email Address</span>
                <span class="val">{escape_html(registration.email)}</span>
            </div>
            <div class="display-row">
                <span class="label">Phone Number</span>
                <span class="val">{escape_html(registration.phone)}</span>
            </div>
            <div class="display-row">
                <span class="label">College Name</span>
                <span class="val">{escape_html(registration.college)}</span>
            </div>
            <div class="display-row">
                <span class="label">Department</span>
                <span class="val">{escape_html(registration.department)}</span>
            </div>
            <div class="display-row">
                <span class="label">Year of Study</span>
                <span class="val">Year {escape_html(registration.year)}</span>
            </div>
            <div class="display-row">
                <span class="label">Roll / Register Number</span>
                <span class="val">{escape_html(registration.roll_number or "Not Provided")}</span>
            </div>
            
            <div style="grid-column: 1 / -1; height: 1px; background-color: var(--border-color); margin: 15px 0;"></div>
            
            <div class="display-row">
                <span class="label">Event Name</span>
                <span class="val" style="color: var(--secondary); font-weight:600;">{escape_html(registration.event_name)}</span>
            </div>
            <div class="display-row">
                <span class="label">Fee Paid</span>
                <span class="val" style="color: var(--success); font-weight: 700;">₹{registration.amount}</span>
            </div>
            <div class="display-row">
                <span class="label">UPI Ref ID / UTR Number</span>
                <span class="val" style="font-family: monospace; font-weight: 700;">{escape_html(registration.upi_reference_id)}</span>
            </div>
            <div class="display-row">
                <span class="label">Payment Screenshot URL</span>
                <span class="val" style="word-break: break-all;">
                    {escape_html(registration.payment_screenshot_url or "Not Provided")}
                    {screenshot_section}
                </span>
            </div>
        </div>

        <div style="margin-top: 30px; display: flex; flex-direction: column; gap: 10px;">
            <a href="/status/{escape_html(registration.status_token)}" class="btn btn-primary">
                Check Status 📍
            </a>
            <div class="responsive-action-grid">
                <a href="/edit/{escape_html(registration.edit_token)}" class="btn btn-secondary">
                    Edit Response ✏️
                </a>
                <button onclick="window.history.back()" class="btn btn-secondary">
                    Go Back ↩
                </button>
            </div>
        </div>
    </div>
    """

    extra_css = """
        .form-display-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 16px;
        }
        .display-row {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }
        .display-row .label {
            font-size: 12px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.03em;
            font-weight: 600;
        }
        .display-row .val {
            font-size: 15px;
            color: var(--text-main);
            word-break: break-word;
        }
        @media (max-width: 639px) {
            .form-display-grid {
                grid-template-columns: 1fr;
            }
        }
    """
    return page_shell("View Response", body, extra_css)


def render_status_html(registration) -> str:
    """Generates the live status timeline page."""
    status = registration.payment_status
    reg_status = registration.registration_status
    status_token = escape_html(registration.status_token)
    edit_token = escape_html(registration.edit_token)

    # Calculate status active stages
    # Stage 1: Submitted (always active)
    # Stage 2: Payment manual review (active if submitted)
    # Stage 3: Approval/Rejection/Correction (depends on status)
    # Stage 4: Email sent (depends on email_status)

    step1_class = "step-active"
    step2_class = "step-active"
    step3_class = "step-pending"
    step3_title = "Verification Complete"
    step3_desc = "Your registration status is being processed."
    
    if status == "APPROVED":
        step3_class = "step-success"
        step3_title = "Registration Confirmed"
        step3_desc = "Organizer verified transaction. Your seat is confirmed."
    elif status == "REJECTED":
        step3_class = "step-error"
        step3_title = "Payment Verification Failed"
        step3_desc = "Organizer rejected this transaction. Please see note below."
    elif status == "NEEDS_CORRECTION":
        step3_class = "step-warning"
        step3_title = "Correction Requested"
        step3_desc = "Some details require correction. Please edit your details."
    else:
        # PENDING_REVIEW
        step2_class = "step-active step-pulse"
        step3_desc = "Awaiting manual verification by administrative staff."

    step4_class = "step-pending"
    if registration.email_status == "SENT":
        step4_class = "step-success"
    elif registration.email_status == "FAILED":
        step4_class = "step-error"

    # Status summary block
    status_summary = ""
    admin_action_box = ""
    if status == "APPROVED":
        status_summary = """
        <div class="alert alert-success">
            <strong>Registration Confirmed!</strong> Your payment has been verified, and your registration is complete. Welcome to the event!
        </div>
        """
    elif status == "REJECTED":
        status_summary = """
        <div class="alert alert-danger">
            <strong>Registration Rejected.</strong> The administrative team could not verify your payment with the reference provided.
        </div>
        """
        admin_action_box = f"""
        <div style="margin-top: 15px; text-align: center;">
            <p style="font-size: 14px; color: var(--text-muted); margin-bottom: 12px;">Please click below to correct your details (e.g. UTR/screenshot) and re-submit.</p>
            <a href="/edit/{edit_token}" class="btn btn-primary">Edit Response ✏️</a>
        </div>
        """
    elif status == "NEEDS_CORRECTION":
        status_summary = """
        <div class="alert alert-warning">
            <strong>Correction Needed.</strong> There is a mismatch or missing information in your registration.
        </div>
        """
        admin_action_box = f"""
        <div style="margin-top: 15px; text-align: center;">
            <p style="font-size: 14px; color: var(--text-muted); margin-bottom: 12px;">Review the note below, then update your details using the edit form.</p>
            <a href="/edit/{edit_token}" class="btn btn-primary">Edit Response ✏️</a>
        </div>
        """
    else:
        status_summary = """
        <div class="alert alert-info">
            <strong>Under Review.</strong> Your transaction reference is queued for review. Admin will check GPay/PhonePe records shortly.
        </div>
        """

    admin_note_block = ""
    if registration.admin_note:
        admin_note_block = f"""
        <div style="background-color: rgba(255,255,255,0.02); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 15px; margin: 20px 0; text-align: left;">
            <div style="font-size: 11px; color: var(--text-muted); font-weight: 700; text-transform: uppercase; margin-bottom: 5px;">Admin Note / Feedback:</div>
            <div style="font-size: 14px; color: var(--text-main); font-style: italic;">"{escape_html(registration.admin_note)}"</div>
        </div>
        """

    body = f"""
    <div class="card">
        <h1 style="font-size: 24px; margin-bottom: 5px; font-family: 'Space Grotesk', sans-serif; text-align: center;">Registration Timeline</h1>
        <p style="color: var(--text-muted); font-size: 14px; text-align: center; margin-bottom: 25px;">
            Registration ID: <strong style="font-family: monospace; color: var(--primary);">{escape_html(registration.registration_id)}</strong>
        </p>

        {status_summary}
        {admin_note_block}

        <!-- Timeline container -->
        <div class="timeline">
            <div class="timeline-item {step1_class}">
                <div class="timeline-marker"></div>
                <div class="timeline-content">
                    <h3>Response Submitted</h3>
                    <p>Form submission saved successfully at {format_datetime(registration.created_at)}</p>
                </div>
            </div>

            <div class="timeline-item {step2_class}">
                <div class="timeline-marker"></div>
                <div class="timeline-content">
                    <h3>Payment Under Manual Review</h3>
                    <p>Reference: <strong style="font-family: monospace;">{escape_html(registration.upi_reference_id)}</strong>. Admin verifies bank transaction.</p>
                </div>
            </div>

            <div class="timeline-item {step3_class}">
                <div class="timeline-marker"></div>
                <div class="timeline-content">
                    <h3>{step3_title}</h3>
                    <p>{step3_desc}</p>
                </div>
            </div>

            <div class="timeline-item {step4_class}">
                <div class="timeline-marker"></div>
                <div class="timeline-content">
                    <h3>Confirmation Email Triggered</h3>
                    <p>Status: {escape_html(registration.email_status)} to {escape_html(registration.email)}</p>
                </div>
            </div>
        </div>

        {admin_action_box}

        <div class="responsive-action-grid" style="margin-top: 30px; border-top: 1px solid var(--border-color); padding-top: 20px;">
            <a href="/form" class="btn btn-secondary">
                Home 🏠
            </a>
            <button onclick="window.history.back()" class="btn btn-secondary">
                Go Back ↩
            </button>
        </div>
    </div>
    """

    extra_css = """
        .alert {
            padding: 12px 16px;
            border-radius: var(--radius-sm);
            font-size: 14px;
            margin-bottom: 20px;
            text-align: center;
            border: 1px solid transparent;
        }
        .alert-success {
            background-color: rgba(16, 185, 129, 0.1);
            color: var(--success);
            border-color: rgba(16, 185, 129, 0.2);
        }
        .alert-danger {
            background-color: rgba(239, 68, 68, 0.1);
            color: var(--danger);
            border-color: rgba(239, 68, 68, 0.2);
        }
        .alert-warning {
            background-color: rgba(245, 158, 11, 0.1);
            color: var(--warning);
            border-color: rgba(245, 158, 11, 0.2);
        }
        .alert-info {
            background-color: rgba(59, 130, 246, 0.1);
            color: var(--info);
            border-color: rgba(59, 130, 246, 0.2);
        }

        /* Timeline styling */
        .timeline {
            position: relative;
            padding: 10px 0;
            margin: 15px 0 15px 15px;
            border-left: 2px solid rgba(255,255,255,0.06);
        }
        .timeline-item {
            position: relative;
            margin-bottom: 24px;
            padding-left: 30px;
        }
        .timeline-item:last-child {
            margin-bottom: 0;
        }
        .timeline-marker {
            position: absolute;
            top: 4px;
            left: -7px;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background-color: var(--text-dark);
            border: 2px solid var(--bg-base);
            transition: var(--transition);
        }
        .timeline-content h3 {
            font-size: 15px;
            margin-bottom: 4px;
            font-weight: 600;
        }
        .timeline-content p {
            font-size: 13px;
            color: var(--text-muted);
            line-height: 1.4;
        }

        /* Timeline States */
        .timeline-item.step-active .timeline-marker {
            background-color: var(--primary);
            box-shadow: 0 0 10px var(--primary);
        }
        .timeline-item.step-active.step-pulse .timeline-marker {
            animation: markerPulse 1.5s infinite alternate;
        }
        .timeline-item.step-success .timeline-marker {
            background-color: var(--success);
            box-shadow: 0 0 10px var(--success);
        }
        .timeline-item.step-error .timeline-marker {
            background-color: var(--danger);
            box-shadow: 0 0 10px var(--danger);
        }
        .timeline-item.step-warning .timeline-marker {
            background-color: var(--warning);
            box-shadow: 0 0 10px var(--warning);
        }
        .timeline-item.step-pending .timeline-marker {
            background-color: var(--text-dark);
        }
        .timeline-item.step-success .timeline-content h3 { color: var(--success); }
        .timeline-item.step-error .timeline-content h3 { color: var(--danger); }
        .timeline-item.step-warning .timeline-content h3 { color: var(--warning); }
        .timeline-item.step-active .timeline-content h3 { color: var(--text-main); }
        .timeline-item.step-pending .timeline-content h3 { color: var(--text-dark); }

        @keyframes markerPulse {
            0% { transform: scale(1); box-shadow: 0 0 4px var(--primary); }
            100% { transform: scale(1.3); box-shadow: 0 0 12px var(--primary); }
        }
    """
    return page_shell("Registration Status", body, extra_css)


def render_edit_html(registration) -> str:
    """Generates the response editing form."""
    edit_token = escape_html(registration.edit_token)
    
    body = f"""
    <div class="card">
        <h1 style="font-size: 24px; font-family: 'Space Grotesk', sans-serif; margin-bottom: 5px;">Edit Response Details</h1>
        <p style="color: var(--text-muted); font-size: 13px; margin-bottom: 20px;">
            Registration ID: <strong style="font-family: monospace; color: var(--primary);">{escape_html(registration.registration_id)}</strong>
        </p>

        <!-- Warning Callout Box -->
        <div style="background-color: rgba(245, 158, 11, 0.05); border-left: 4px solid var(--warning); padding: 12px; border-radius: var(--radius-sm); font-size: 13px; color: #fcd34d; margin-bottom: 25px; line-height: 1.4;">
            <strong>⚠️ Crucial Notice:</strong> Changing your UPI Transaction / UTR ID will immediately reset your verification status to <strong>Pending Review</strong>.
        </div>

        <form id="editForm" onsubmit="handleEditSubmit(event)">
            <div class="form-group">
                <label>Email Address <span class="badge badge-info" style="font-size: 9px; padding: 2px 6px;">Read Only</span></label>
                <input type="text" class="form-control" value="{escape_html(registration.email)}" disabled style="opacity: 0.65; cursor: not-allowed;">
            </div>

            <div class="grid-2">
                <div class="form-group">
                    <label for="full_name">Full Name *</label>
                    <input type="text" id="full_name" name="full_name" class="form-control" value="{escape_html(registration.full_name)}" required minlength="2" maxlength="150">
                </div>
                <div class="form-group">
                    <label for="phone">Phone Number *</label>
                    <input type="tel" id="phone" name="phone" class="form-control" value="{escape_html(registration.phone)}" required>
                </div>
            </div>

            <div class="form-group">
                <label for="college">College Name *</label>
                <input type="text" id="college" name="college" class="form-control" value="{escape_html(registration.college)}" required maxlength="200">
            </div>

            <div class="grid-2">
                <div class="form-group">
                    <label for="department">Department *</label>
                    <input type="text" id="department" name="department" class="form-control" value="{escape_html(registration.department)}" required maxlength="120">
                </div>
                <div class="form-group">
                    <label for="year">Year of Study *</label>
                    <select id="year" name="year" class="form-control" required>
                        <option value="1" {"selected" if registration.year == "1" else ""}>1st Year</option>
                        <option value="2" {"selected" if registration.year == "2" else ""}>2nd Year</option>
                        <option value="3" {"selected" if registration.year == "3" else ""}>3rd Year</option>
                        <option value="4" {"selected" if registration.year == "4" else ""}>4th Year</option>
                        <option value="5" {"selected" if registration.year == "5" else ""}>5th Year</option>
                    </select>
                </div>
            </div>

            <div class="form-group">
                <label for="roll_number">Roll / Register Number <span style="color: var(--text-dark);">(Optional)</span></label>
                <input type="text" id="roll_number" name="roll_number" class="form-control" value="{escape_html(registration.roll_number)}" maxlength="50">
            </div>

            <div style="border-top: 1px solid var(--border-color); margin: 20px 0; padding-top: 15px;"></div>

            <div class="form-group">
                <label for="upi_reference_id" style="color: var(--warning); font-weight: 600;">UPI Reference ID / UTR Number *</label>
                <input type="text" id="upi_reference_id" name="upi_reference_id" class="form-control highlight-input" value="{escape_html(registration.upi_reference_id)}" required minlength="8" maxlength="120" style="font-family: monospace; letter-spacing: 0.05em;">
                <div id="utrMessage" class="validation-msg"></div>
            </div>

            <div class="form-group">
                <label for="payment_screenshot_url">Payment Screenshot URL <span style="color: var(--text-dark);">(Optional)</span></label>
                <input type="url" id="payment_screenshot_url" name="payment_screenshot_url" class="form-control" value="{escape_html(registration.payment_screenshot_url or '')}">
            </div>

            <div id="errorMessage" class="error-banner" style="display: none;"></div>

            <div class="responsive-action-grid" style="margin-top: 25px;">
                <button type="submit" class="btn btn-primary" id="submitBtn">
                    Save Changes ✨
                </button>
                <button type="button" onclick="window.history.back()" class="btn btn-secondary">
                    Cancel
                </button>
            </div>
        </form>
    </div>
    """

    extra_css = """
        .form-group {
            margin-bottom: 16px;
            text-align: left;
        }
        .form-group label {
            display: block;
            margin-bottom: 6px;
            font-size: 13px;
            font-weight: 500;
            color: var(--text-main);
        }
        .form-control {
            width: 100%;
            background-color: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-sm);
            padding: 10px 14px;
            font-size: 14px;
            color: white;
            font-family: 'Outfit', sans-serif;
            transition: var(--transition);
        }
        .form-control:focus {
            outline: none;
            border-color: var(--primary);
            box-shadow: 0 0 0 3px var(--primary-glow);
            background-color: rgba(255, 255, 255, 0.05);
        }
        .highlight-input:focus {
            border-color: var(--warning);
            box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.15);
        }
        .grid-2 {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }
        .validation-msg {
            font-size: 12px;
            margin-top: 4px;
            min-height: 16px;
        }
        .validation-msg.available { color: var(--success); }
        .validation-msg.taken { color: var(--danger); }
        .error-banner {
            background-color: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.2);
            color: var(--danger);
            padding: 10px;
            border-radius: var(--radius-sm);
            font-size: 13px;
            margin-top: 15px;
            text-align: center;
        }
        @media (max-width: 639px) {
            .grid-2 {
                grid-template-columns: 1fr;
            }
        }
    """

    extra_js = f"""
    <script>
        const originalUtr = "{escape_html(registration.upi_reference_id)}";
        const utrInput = document.getElementById("upi_reference_id");
        const utrMsg = document.getElementById("utrMessage");
        const submitBtn = document.getElementById("submitBtn");
        const errorBanner = document.getElementById("errorMessage");

        let utrValid = true;

        utrInput.addEventListener("input", debounce(async (e) => {{
            const val = e.target.value.trim().toUpperCase();
            if (!val || val === originalUtr) {{
                utrMsg.textContent = "";
                utrValid = true;
                submitBtn.disabled = false;
                return;
            }}

            if (val.length < 8) {{
                utrMsg.textContent = "UTR must be at least 8 characters";
                utrMsg.className = "validation-msg taken";
                utrValid = false;
                return;
            }}

            try {{
                const res = await fetch(`/api/check-utr/${{encodeURIComponent(val)}}`);
                const data = await res.json();
                if (data.available) {{
                    utrMsg.textContent = "✓ Transaction ID is unique";
                    utrMsg.className = "validation-msg available";
                    utrValid = true;
                    submitBtn.disabled = false;
                }} else {{
                    utrMsg.textContent = "✗ This Transaction ID/UTR has already been submitted";
                    utrMsg.className = "validation-msg taken";
                    utrValid = false;
                    submitBtn.disabled = true;
                }}
            }} catch (err) {{
                console.error("UTR validation error", err);
            }}
        }}, 400));

        function debounce(func, delay) {{
            let timeout;
            return function(...args) {{
                clearTimeout(timeout);
                timeout = setTimeout(() => func.apply(this, args), delay);
            }};
        }}

        async function handleEditSubmit(e) {{
            e.preventDefault();
            if (!utrValid) return;

            submitBtn.disabled = true;
            submitBtn.textContent = "Saving Changes...";
            errorBanner.style.display = "none";

            const payload = {{
                full_name: document.getElementById("full_name").value,
                phone: document.getElementById("phone").value,
                college: document.getElementById("college").value,
                department: document.getElementById("department").value,
                year: document.getElementById("year").value,
                roll_number: document.getElementById("roll_number").value || null,
                upi_reference_id: utrInput.value.trim().toUpperCase(),
                payment_screenshot_url: document.getElementById("payment_screenshot_url").value || null
            }};

            try {{
                const response = await fetch(`/edit/{edit_token}`, {{
                    method: "POST",
                    headers: {{ "Content-Type": "application/json" }},
                    body: JSON.stringify(payload)
                }});

                const data = await response.json();
                if (response.ok) {{
                    // Redirect to status page
                    window.location.href = data.redirect_url;
                }} else {{
                    errorBanner.textContent = data.detail || "Failed to update response details. Check inputs.";
                    errorBanner.style.display = "block";
                    submitBtn.disabled = false;
                    submitBtn.textContent = "Save Changes";
                }}
            }} catch (err) {{
                errorBanner.textContent = "Network error. Please try again.";
                errorBanner.style.display = "block";
                submitBtn.disabled = false;
                submitBtn.textContent = "Save Changes";
            }}
        }}
    </script>
    """
    return page_shell("Edit Response", body, extra_css, extra_js)


def render_invalid_token_html(message="The link you followed is invalid.") -> str:
    body = f"""
    <div class="card" style="text-align: center; border-color: rgba(239, 68, 68, 0.3);">
        <div style="font-size: 50px; margin-bottom: 15px;">⚠️</div>
        <h1 style="font-size: 24px; font-family: 'Space Grotesk', sans-serif; margin-bottom: 10px; color: var(--danger);">Invalid Token</h1>
        <p style="color: var(--text-muted); font-size: 15px; margin-bottom: 25px; line-height: 1.5;">
            {escape_html(message)} Please double check the link sent in your email or contact support.
        </p>
        <a href="/form" class="btn btn-secondary">Home 🏠</a>
    </div>
    """
    return page_shell("Invalid Link", body)


def render_expired_token_html(message="The verification token has expired.") -> str:
    body = f"""
    <div class="card" style="text-align: center; border-color: rgba(239, 68, 68, 0.3);">
        <div style="font-size: 50px; margin-bottom: 15px;">⌛</div>
        <h1 style="font-size: 24px; font-family: 'Space Grotesk', sans-serif; margin-bottom: 10px; color: var(--danger);">Link Expired</h1>
        <p style="color: var(--text-muted); font-size: 15px; margin-bottom: 25px; line-height: 1.5;">
            {escape_html(message)} For security, editing links expire after some time. Please contact organizers if you need to modify details.
        </p>
        <a href="/form" class="btn btn-secondary">Home 🏠</a>
    </div>
    """
    return page_shell("Link Expired", body)


def render_edit_locked_html(registration) -> str:
    body = f"""
    <div class="card" style="text-align: center; border-color: rgba(139, 92, 246, 0.3);">
        <div style="font-size: 50px; margin-bottom: 15px;">🔒</div>
        <h1 style="font-size: 24px; font-family: 'Space Grotesk', sans-serif; margin-bottom: 10px; color: var(--primary);">Editing Locked</h1>
        <p style="color: var(--text-muted); font-size: 15px; margin-bottom: 25px; line-height: 1.5;">
            Editing is locked for Registration ID: <strong>{escape_html(registration.registration_id)}</strong>.<br>
            Since your payment has already been verified and approved, modifying response details is no longer permitted.
        </p>
        <div class="responsive-action-grid" style="margin-top: 20px;">
            <a href="/status/{escape_html(registration.status_token)}" class="btn btn-primary">Check Status 📍</a>
            <a href="/r/{escape_html(registration.view_token)}" class="btn btn-secondary">View Response 👁</a>
        </div>
    </div>
    """
    return page_shell("Editing Locked", body)


def render_admin_login_html(error=None) -> str:
    error_banner = ""
    if error:
        error_banner = f"""
        <div style="background-color: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.2); border-radius: var(--radius-sm); padding: 10px; color: var(--danger); font-size: 13px; margin-bottom: 15px; text-align: center;">
            {escape_html(error)}
        </div>
        """

    body = f"""
    <div class="card" style="max-width: 400px;">
        <h1 style="font-size: 22px; font-family: 'Space Grotesk', sans-serif; text-align: center; margin-bottom: 8px;">Admin Login</h1>
        <p style="color: var(--text-muted); font-size: 13px; text-align: center; margin-bottom: 20px;">Provide secret credentials to access dashboard</p>

        {error_banner}

        <form action="/admin/login" method="POST">
            <div style="margin-bottom: 18px;">
                <label for="admin_password" style="display: block; margin-bottom: 6px; font-size: 13px; color: var(--text-muted);">Admin Secret Password</label>
                <input type="password" id="admin_password" name="admin_password" style="width:100%; background-color: rgba(255,255,255,0.03); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 12px; font-size: 14px; color: white;" required autofocus>
            </div>
            <button type="submit" class="btn btn-primary" style="width: 100%;">Access CRM Dashboard ↗</button>
        </form>
    </div>
    """
    return page_shell("Admin Access", body)


def render_admin_dashboard_html(records, stats, filters) -> str:
    """Renders the comprehensive administrative dashboard."""
    # Filter state variables
    search_q = escape_html(filters.get("search", ""))
    sel_status = filters.get("status", "")
    
    # Render table rows
    table_rows = ""
    if not records:
        table_rows = """
        <tr>
            <td colspan="9" style="text-align: center; color: var(--text-dark); padding: 40px 10px;">
                No registration records match the criteria.
            </td>
        </tr>
        """
    else:
        for r in records:
            # Status styling
            if r.payment_status == "APPROVED":
                status_b = f'<span class="badge badge-approved">Approved</span>'
            elif r.payment_status == "REJECTED":
                status_b = f'<span class="badge badge-rejected">Rejected</span>'
            elif r.payment_status == "NEEDS_CORRECTION":
                status_b = f'<span class="badge badge-correction">Needs Action</span>'
            else:
                status_b = f'<span class="badge badge-pending">Pending</span>'

            # Build action forms
            action_buttons = f"""
            <div style="display: flex; gap: 5px; justify-content: center;">
                <a href="/admin/registration/{r.registration_id}" class="btn btn-secondary" style="padding: 6px 12px; font-size:12px;">View 👁</a>
                {f'''
                <form action="/admin/approve/{r.registration_id}" method="POST" style="display:inline;" onsubmit="return confirm('Approve payment for {escape_html(r.full_name)}?')">
                    <button type="submit" class="btn btn-success" style="padding: 6px 12px; font-size:12px;">Approve ✅</button>
                </form>
                ''' if r.payment_status != "APPROVED" else ""}
            </div>
            """

            table_rows += f"""
            <tr {"style='background-color: rgba(245, 158, 11, 0.02);'" if r.payment_status == "PENDING_REVIEW" else ""}>
                <td style="font-family: monospace; font-size: 13px; font-weight: 600; color: var(--primary);">{escape_html(r.registration_id)}</td>
                <td>
                    <div style="font-weight: 500;">{escape_html(r.full_name)}</div>
                    <div style="font-size:11px; color: var(--text-muted);">{escape_html(r.email)}</div>
                </td>
                <td style="font-size: 13px;">{escape_html(r.phone)}</td>
                <td style="font-size: 13px; max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{escape_html(r.college)}">
                    {escape_html(r.college)}
                </td>
                <td style="font-weight: 600; color: var(--success);">₹{r.amount}</td>
                <td style="font-family: monospace; font-size: 12px;" title="{escape_html(r.upi_reference_id)}">{escape_html(r.upi_reference_id)}</td>
                <td style="text-align: center;">{status_b}</td>
                <td style="font-size: 12px; color: var(--text-dark);">{r.created_at.strftime("%b %d, %H:%M")}</td>
                <td>{action_buttons}</td>
            </tr>
            """

    # Build the HTML body string
    body = f"""
    <div style="width: 100%; max-width: 1300px; margin: 0 auto;">
        
        <!-- Header Panel with Logout -->
        <div class="admin-header-panel">
            <div class="admin-title-group">
                <h1 class="admin-title">CRM Event Console</h1>
                <p class="admin-subtitle">Manage manual bank verification & attendee registrations</p>
            </div>
            <div class="admin-header-actions">
                <a href="/admin/export.csv?search={search_q}&payment_status={sel_status}" class="btn btn-secondary">
                    <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                    Export CSV ⬇️
                </a>
                <form action="/admin/logout" method="POST" style="width: 100%;">
                    <button type="submit" class="btn btn-danger" style="width: 100%;">Logout ↗</button>
                </form>
            </div>
        </div>

        <!-- Dashboard Stats Cards Grid -->
        <div class="stats-grid">
            <div class="stat-card">
                <span class="stat-title">Total Submissions</span>
                <span class="stat-val" style="color: var(--text-main);">{stats.get("total", 0)}</span>
            </div>
            <div class="stat-card" style="border-left: 4px solid var(--warning);">
                <span class="stat-title" style="color: var(--warning);">Pending Verification</span>
                <span class="stat-val" style="color: var(--warning);">{stats.get("pending", 0)}</span>
            </div>
            <div class="stat-card" style="border-left: 4px solid var(--success);">
                <span class="stat-title" style="color: var(--success);">Approved Confirmed</span>
                <span class="stat-val" style="color: var(--success);">{stats.get("approved", 0)}</span>
            </div>
            <div class="stat-card" style="border-left: 4px solid var(--info);">
                <span class="stat-title" style="color: var(--info);">Needs Correction</span>
                <span class="stat-val" style="color: var(--info);">{stats.get("correction", 0)}</span>
            </div>
            <div class="stat-card" style="border-left: 4px solid var(--danger);">
                <span class="stat-title" style="color: var(--danger);">Rejected</span>
                <span class="stat-val" style="color: var(--danger);">{stats.get("rejected", 0)}</span>
            </div>
            <div class="stat-card">
                <span class="stat-title">Today's Inflow</span>
                <span class="stat-val" style="color: var(--primary);">{stats.get("today", 0)}</span>
            </div>
        </div>

        <!-- Filter & Search Controls bar -->
        <div style="background-color: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 15px; margin-bottom: 20px;">
            <form method="GET" action="/admin" class="admin-filters-form">
                <div class="filter-group filter-group-search">
                    <input type="text" name="search" placeholder="Search by Registration ID, UTR, Name, Email, Phone..." class="filter-input" value="{search_q}">
                </div>
                <div class="filter-group filter-group-select">
                    <select name="payment_status" class="filter-input">
                        <option value="">-- All Payment Status --</option>
                        <option value="PENDING_REVIEW" {"selected" if sel_status == "PENDING_REVIEW" else ""}>Pending Review</option>
                        <option value="APPROVED" {"selected" if sel_status == "APPROVED" else ""}>Approved</option>
                        <option value="REJECTED" {"selected" if sel_status == "REJECTED" else ""}>Rejected</option>
                        <option value="NEEDS_CORRECTION" {"selected" if sel_status == "NEEDS_CORRECTION" else ""}>Needs Correction</option>
                    </select>
                </div>
                <div class="btn-group">
                    <button type="submit" class="btn btn-primary" style="padding: 10px 20px;">Apply Filters 🔍</button>
                    <a href="/admin" class="btn btn-secondary" style="padding: 10px 20px;">Clear 🧹</a>
                </div>
            </form>
        </div>

        <!-- Desktop Records Table -->
        <div class="table-container">
            <table class="crm-table">
                <thead>
                    <tr>
                        <th style="width: 140px;">Reg ID</th>
                        <th>Attendee Details</th>
                        <th>Phone</th>
                        <th>College</th>
                        <th>Amount</th>
                        <th>UTR / UPI Ref</th>
                        <th style="text-align: center; width: 130px;">Payment Status</th>
                        <th style="width: 120px;">Submitted</th>
                        <th style="text-align: center; width: 180px;">Quick Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
    </div>
    """

    extra_css = """
        .admin-header-panel {
            display: flex;
            flex-direction: column;
            gap: var(--space-4);
            margin-bottom: var(--space-6);
        }
        .admin-title {
            font-size: 26px;
            font-family: 'Space Grotesk', sans-serif;
            line-height: 1.2;
        }
        .admin-subtitle {
            font-size: 14px;
            color: var(--text-muted);
            margin-top: var(--space-1);
        }
        .admin-header-actions {
            display: flex;
            gap: var(--space-3);
            width: 100%;
        }
        .admin-header-actions .btn, .admin-header-actions form {
            flex: 1;
        }
        @media (min-width: 768px) {
            .admin-header-panel {
                flex-direction: row;
                justify-content: space-between;
                align-items: center;
            }
            .admin-header-actions {
                width: auto;
            }
            .admin-header-actions .btn, .admin-header-actions form {
                flex: initial;
            }
        }

        .admin-filters-form {
            display: flex;
            flex-direction: column;
            gap: var(--space-3);
        }
        .admin-filters-form .filter-group {
            width: 100%;
        }
        .admin-filters-form .btn-group {
            display: flex;
            gap: var(--space-2);
            width: 100%;
        }
        .admin-filters-form .btn-group .btn {
            flex: 1;
        }
        @media (min-width: 768px) {
            .admin-filters-form {
                flex-direction: row;
                flex-wrap: wrap;
                align-items: center;
            }
            .admin-filters-form .filter-group-search {
                flex: 1;
                min-width: 250px;
            }
            .admin-filters-form .filter-group-select {
                width: 200px;
            }
            .admin-filters-form .btn-group {
                width: auto;
            }
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
            margin-bottom: 20px;
        }
        @media (min-width: 640px) {
            .stats-grid {
                grid-template-columns: repeat(3, 1fr);
            }
        }
        @media (min-width: 1024px) {
            .stats-grid {
                grid-template-columns: repeat(6, 1fr);
            }
        }

        .stat-card {
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-sm);
            padding: 18px;
            display: flex;
            flex-direction: column;
            gap: 6px;
            transition: var(--transition-bounce);
        }
        .stat-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
            border-color: var(--primary);
        }
        .stat-title {
            font-size: 11px;
            color: var(--text-dark);
            text-transform: uppercase;
            font-weight: 700;
            letter-spacing: 0.05em;
        }
        .stat-val {
            font-size: 26px;
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 700;
        }
        
        .filter-input {
            width: 100%;
            background-color: rgba(0,0,0,0.2);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-sm);
            padding: 10px 12px;
            font-size: 14px;
            color: white;
            font-family: 'Outfit', sans-serif;
        }
        .filter-input:focus {
            outline: none;
            border-color: var(--primary);
        }

        .table-container {
            background-color: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            overflow-x: auto;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        }
        .crm-table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 14px;
        }
        .crm-table th {
            background-color: rgba(255,255,255,0.02);
            padding: 14px 16px;
            color: var(--text-muted);
            font-weight: 600;
            border-bottom: 1px solid var(--border-color);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.02em;
        }
        .crm-table td {
            padding: 14px 16px;
            border-bottom: 1px solid var(--border-color);
            color: var(--text-main);
            vertical-align: middle;
        }
        .crm-table tr {
            transition: var(--transition);
        }
        .crm-table tr:hover {
            background-color: rgba(255, 255, 255, 0.03);
        }
    """
    return page_shell("Admin Console", body, extra_css)


def render_admin_detail_html(registration, audit_logs, email_logs) -> str:
    """Renders the comprehensive record detail and audit view for admins."""
    # Compute status labels
    status = registration.payment_status
    if status == "APPROVED":
        status_badge = '<span class="badge badge-approved">Approved / Confirmed</span>'
    elif status == "REJECTED":
        status_badge = '<span class="badge badge-rejected">Rejected</span>'
    elif status == "NEEDS_CORRECTION":
        status_badge = '<span class="badge badge-correction">Needs Correction</span>'
    else:
        status_badge = '<span class="badge badge-pending">Pending Review</span>'

    # Lock toggler action buttons
    lock_action = ""
    if registration.is_edit_locked:
        lock_action = f"""
        <form action="/admin/unlock-edit/{registration.registration_id}" method="POST" style="display:inline;">
            <button type="submit" class="btn btn-secondary" style="color: var(--warning);">Unlock Editing 🔓</button>
        </form>
        """
    else:
        lock_action = f"""
        <form action="/admin/lock-edit/{registration.registration_id}" method="POST" style="display:inline;">
            <button type="submit" class="btn btn-secondary" style="color: var(--text-muted);">Lock Editing 🔒</button>
        </form>
        """

    # Format audit logs rows
    audit_rows = ""
    if not audit_logs:
        audit_rows = "<tr><td colspan='4' style='color: var(--text-dark); text-align:center;'>No audit trail logged.</td></tr>"
    else:
        for log in audit_logs:
            audit_rows += f"""
            <tr>
                <td style="font-size:12px; font-weight:600; color: var(--secondary);">{escape_html(log.action)}</td>
                <td style="font-size:12px; color: var(--text-muted); font-family: monospace; white-space: pre-wrap; max-width:200px;">
                    {f"Old: {escape_html(log.old_data)}" if log.old_data else ""}
                    {f"<br>New: {escape_html(log.new_data)}" if log.new_data else ""}
                </td>
                <td style="font-size:12px;">{escape_html(log.performed_by)} ({escape_html(log.ip_address or "-")})</td>
                <td style="font-size:11px; color: var(--text-dark);">{format_datetime(log.created_at)}</td>
            </tr>
            """

    # Format email logs rows
    email_rows = ""
    if not email_logs:
        email_rows = "<tr><td colspan='5' style='color: var(--text-dark); text-align:center;'>No email delivery logs.</td></tr>"
    else:
        for log in email_logs:
            status_b = f'<span class="badge badge-approved" style="padding: 2px 8px; font-size:9px;">SENT</span>' if log.status == "SENT" else f'<span class="badge badge-rejected" style="padding: 2px 8px; font-size:9px;">FAILED</span>'
            email_rows += f"""
            <tr>
                <td style="font-size:12px; font-weight:600;">{escape_html(log.email_type)}</td>
                <td style="font-size:12px; color: var(--text-muted);">{escape_html(log.email_to)}</td>
                <td style="font-size:12px; font-family:monospace;">{escape_html(log.resend_message_id or "-")}</td>
                <td>{status_b}</td>
                <td style="font-size:11px; color: var(--text-dark);">{format_datetime(log.created_at)}</td>
            </tr>
            """

    screenshot_box = ""
    if registration.payment_screenshot_url:
        screenshot_box = f"""
        <div style="margin-top: 15px;">
            <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 5px; font-weight:600; text-transform:uppercase;">Screenshot Uploaded:</p>
            <a href="{escape_html(registration.payment_screenshot_url)}" target="_blank" style="display:block; max-width:300px; border:1px solid var(--border-color); border-radius:var(--radius-sm); overflow:hidden;">
                <img src="{escape_html(registration.payment_screenshot_url)}" style="width:100%; height:auto; display:block; object-fit:contain;" alt="Payment Proof">
            </a>
        </div>
        """

    # Main structure builder
    body = f"""
    <div class="admin-detail-layout">
        
        <!-- Left Column: Data Summary & Actions -->
        <div style="display: flex; flex-direction: column; gap: 20px;">
            
            <div style="background-color: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 25px;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom: 15px; border-bottom:1px solid var(--border-color); padding-bottom:15px;">
                    <div>
                        <a href="/admin" style="font-size: 13px; color: var(--primary); text-decoration: none; display:flex; align-items:center; gap: 4px; margin-bottom: 5px;">&larr; Back to Dashboard</a>
                        <h2 style="font-family:'Space Grotesk', sans-serif; font-size:22px;">{escape_html(registration.full_name)}</h2>
                        <span style="font-family: monospace; font-size: 13px; color: var(--text-muted);">{escape_html(registration.registration_id)}</span>
                    </div>
                    <div>
                        {status_badge}
                    </div>
                </div>

                <div class="detail-grid">
                    <div><span>Email:</span><strong>{escape_html(registration.email)}</strong></div>
                    <div><span>Phone:</span><strong>{escape_html(registration.phone)}</strong></div>
                    <div><span>College:</span><strong>{escape_html(registration.college)}</strong></div>
                    <div><span>Dept / Year:</span><strong>{escape_html(registration.department)} (Year {registration.year})</strong></div>
                    <div><span>Roll No:</span><strong>{escape_html(registration.roll_number or "N/A")}</strong></div>
                    <div><span>Amount:</span><strong style="color:var(--success)">₹{registration.amount}</strong></div>
                    <div><span>UTR Ref:</span><strong style="font-family:monospace; color:var(--text-main); font-size:15px;">{escape_html(registration.upi_reference_id)}</strong></div>
                    <div><span>Edit Locked:</span><strong>{"🔒 Yes" if registration.is_edit_locked else "🔓 No"} (Edits: {registration.edit_count})</strong></div>
                    <div style="grid-column: 1 / -1;"><span>IP / UserAgent:</span><strong style="font-size:11px; font-family:monospace; word-break:break-all;">{escape_html(registration.ip_address)} / {escape_html(registration.user_agent)}</strong></div>
                </div>

                {screenshot_box}
            </div>

            <!-- Audit Trail Box -->
            <div style="background-color: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 20px; overflow: hidden;">
                <h3 style="font-size: 15px; margin-bottom: 12px; font-family: 'Space Grotesk', sans-serif; border-bottom: 1px solid var(--border-color); padding-bottom: 8px;">Registration Audit Trail</h3>
                <div class="table-container">
                    <table class="detail-sub-table">
                        <thead>
                            <tr>
                                <th>Action</th>
                                <th>Diff Data</th>
                                <th>Performed By</th>
                                <th>Timestamp</th>
                            </tr>
                        </thead>
                        <tbody>
                            {audit_rows}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Right Column: Verification Actions and Communications logs -->
        <div style="display: flex; flex-direction: column; gap: 20px;">
            
            <!-- Administrative Control Panel -->
            <div style="background-color: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 25px;">
                <h3 style="font-size: 15px; margin-bottom: 15px; font-family: 'Space Grotesk', sans-serif;">Verification Actions</h3>
                
                <form id="actionForm" method="POST" style="display:flex; flex-direction:column; gap:12px;">
                    <div>
                        <label for="admin_note" style="display:block; font-size:12px; color:var(--text-muted); margin-bottom:5px;">Admin Note (Visible to user in timeline & emails)</label>
                        <textarea id="admin_note" name="admin_note" rows="3" style="width:100%; background:rgba(0,0,0,0.2); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:10px; color:white; font-family:'Outfit', sans-serif; font-size:13px;" placeholder="Reason for rejection or correction request...">{escape_html(registration.admin_note or '')}</textarea>
                    </div>

                    <div style="display:flex; flex-direction:column; gap:8px;">
                        <button type="submit" onclick="submitAction('approve')" class="btn btn-success" style="width:100%;">
                            Approve ✅
                        </button>
                        <div class="responsive-action-grid">
                            <button type="submit" onclick="submitAction('reject')" class="btn btn-danger">
                                Reject ❌
                            </button>
                            <button type="submit" onclick="submitAction('needs-correction')" class="btn btn-secondary" style="color:var(--info);">
                                Needs Correction ⚠️
                            </button>
                        </div>
                    </div>
                </form>

                <div style="border-top:1px solid var(--border-color); margin: 20px 0; padding-top:15px; display:flex; flex-direction:column; gap:10px;">
                    {lock_action}
                    
                    <form action="/admin/resend-email/{registration.registration_id}" method="POST" style="display:inline;">
                        <button type="submit" class="btn btn-secondary" style="width:100%;">Resend Email ✉️</button>
                    </form>
                </div>
            </div>

            <!-- Email logs box -->
            <div style="background-color: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 20px;">
                <h3 style="font-size: 15px; margin-bottom: 12px; font-family: 'Space Grotesk', sans-serif; border-bottom: 1px solid var(--border-color); padding-bottom: 8px;">Resend Email Deliveries</h3>
                <div class="table-container">
                    <table class="detail-sub-table">
                        <thead>
                            <tr>
                                <th>Type</th>
                                <th>Recipient</th>
                                <th>Message ID</th>
                                <th>Status</th>
                                <th>Sent At</th>
                            </tr>
                        </thead>
                        <tbody>
                            {email_rows}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    """

    extra_js = f"""
    <script>
        function submitAction(actionType) {{
            const form = document.getElementById("actionForm");
            form.action = "/admin/" + actionType + "/{registration.registration_id}";
        }}
    </script>
    """

    extra_css = """
        .admin-detail-layout {
            width: 100%;
            max-width: 1120px;
            margin: 0 auto;
            display: grid;
            grid-template-columns: 1fr;
            gap: 20px;
            text-align: left;
        }
        @media (min-width: 1024px) {
            .admin-detail-layout {
                grid-template-columns: 1.5fr 1fr;
            }
        }
        .detail-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 10px;
            font-size: 14px;
        }
        @media (min-width: 640px) {
            .detail-grid {
                grid-template-columns: 1fr 1fr;
                gap: 16px;
            }
        }
        .detail-grid div {
            display: flex;
            justify-content: space-between;
            border-bottom: 1px solid rgba(255,255,255,0.02);
            padding-bottom: 6px;
            flex-direction: column;
            gap: 4px;
        }
        @media (min-width: 480px) {
            .detail-grid div {
                flex-direction: row;
                gap: 10px;
            }
        }
        .detail-grid span {
            color: var(--text-muted);
        }
        .detail-sub-table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }
        .detail-sub-table th {
            padding: 8px 10px;
            font-size: 10px;
            text-transform: uppercase;
            color: var(--text-dark);
            border-bottom: 1px solid var(--border-color);
        }
        .detail-sub-table td {
            padding: 10px;
            border-bottom: 1px solid var(--border-color);
            color: var(--text-main);
            font-size: 12px;
        }
    """
    return page_shell(f"Detail: {registration.registration_id}", body, extra_css, extra_js)


def render_error_html(title, message) -> str:
    body = f"""
    <div class="card" style="text-align: center; border-color: rgba(239, 68, 68, 0.3);">
        <div style="font-size: 50px; margin-bottom: 15px;">❌</div>
        <h1 style="font-size: 24px; font-family: 'Space Grotesk', sans-serif; margin-bottom: 10px; color: var(--danger);">{escape_html(title)}</h1>
        <p style="color: var(--text-muted); font-size: 15px; margin-bottom: 25px; line-height: 1.5;">
            {escape_html(message)}
        </p>
        <button onclick="window.history.back()" class="btn btn-secondary">Go Back ↩</button>
    </div>
    """
    return page_shell(title, body)


def render_problem_html(reason: str = "Unexpected issue", details: str = "Something went wrong while loading this page.") -> str:
    safe_reason = escape_html(reason)
    safe_details = escape_html(details)

    body = f"""
    <main class="problem-shell" role="alert" aria-live="polite">
      <section class="problem-card">
        <div class="problem-orb">!</div>
        <p class="eyebrow">Event Registration Support</p>
        <h1 style="font-family: 'Space Grotesk', sans-serif; font-size: clamp(24px, 5vw, 32px); margin-bottom: 10px; color: #ffffff;">Something went wrong</h1>
        <p class="lead">Don’t worry, your issue can be fixed.</p>

        <div class="problem-reason">
          <strong>Reason:</strong> {safe_reason}
        </div>

        <p class="problem-details">{safe_details}</p>

        <div class="contact-card">
          <p>Need help? Contact Likith:</p>
          <a href="mailto:likith.anumakonda@gmail.com">likith.anumakonda@gmail.com</a>
        </div>

        <div class="action-row">
          <button class="neo-btn neo-btn-secondary" onclick="history.back()">← Back</button>
          <a class="neo-btn neo-btn-primary" href="/form">Go to Form</a>
          <button class="neo-btn neo-btn-secondary" onclick="location.reload()">Reload Page</button>
          <a class="neo-btn neo-btn-warning" href="mailto:likith.anumakonda@gmail.com?subject=Event%20Registration%20Issue">Contact Likith</a>
        </div>
      </section>
    </main>
    """

    extra_css = """
    .problem-shell {
        width: 100%;
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 16px;
    }
    .problem-card {
        background-color: var(--surface-2);
        border: 1px solid rgba(239, 68, 68, 0.2);
        border-radius: var(--radius-lg);
        padding: var(--space-6);
        width: 100%;
        max-width: 720px;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.4);
        backdrop-filter: blur(12px);
        text-align: center;
        animation: fadeIn 0.4s ease-out;
        position: relative;
        overflow: hidden;
    }
    .problem-orb {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        background: radial-gradient(circle, rgba(239,68,68,0.2) 0%, rgba(239,68,68,0.05) 100%);
        border: 2px solid var(--danger);
        color: var(--danger);
        font-size: 38px;
        font-weight: 800;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 20px auto;
        box-shadow: 0 0 30px rgba(239,68,68,0.25);
        animation: pulseWarning 2s infinite ease-in-out;
    }
    @keyframes pulseWarning {
        0%, 100% { transform: scale(1); box-shadow: 0 0 30px rgba(239,68,68,0.25); }
        50% { transform: scale(1.05); box-shadow: 0 0 45px rgba(239,68,68,0.45); }
    }
    .eyebrow {
        text-transform: uppercase;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.15em;
        color: var(--text-dark);
        margin-bottom: 8px;
    }
    .lead {
        font-size: 16px;
        color: var(--text-muted);
        margin-bottom: 25px;
    }
    .problem-reason {
        background-color: rgba(239, 68, 68, 0.08);
        border: 1px dashed rgba(239, 68, 68, 0.25);
        border-radius: var(--radius-sm);
        padding: var(--space-3);
        color: var(--text);
        font-size: 14px;
        margin-bottom: 20px;
        display: inline-block;
        max-width: 100%;
        word-break: break-word;
    }
    .problem-details {
        font-size: 14px;
        color: var(--muted);
        line-height: 1.6;
        margin-bottom: 30px;
        max-width: 550px;
        margin-left: auto;
        margin-right: auto;
    }
    .contact-card {
        border-top: 1px solid var(--border);
        padding-top: 20px;
        margin-bottom: 30px;
        font-size: 13px;
        color: var(--text-dark);
    }
    .contact-card a {
        color: var(--warning);
        text-decoration: none;
        font-weight: 600;
        font-size: 15px;
        display: inline-block;
        margin-top: 4px;
        transition: color 0.2s ease;
    }
    .contact-card a:hover {
        color: #ffffff;
        text-decoration: underline;
    }
    .action-row {
        display: flex;
        flex-direction: column;
        gap: 12px;
    }
    @media (min-width: 640px) {
        .action-row {
            flex-direction: row;
            justify-content: center;
            flex-wrap: wrap;
            gap: 12px;
        }
        .action-row .neo-btn {
            width: auto !important;
        }
    }
    """

    return page_shell("Problem - Event Registration", body, extra_css)

