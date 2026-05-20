import os

HTML_FILES = [
    "index.html",
    "form.html",
    "thank-you.html",
    "view-response.html",
    "edit-response.html",
    "status.html",
    "admin-login.html",
    "admin-dashboard.html",
    "admin-detail.html",
    "problem.html",
    "expired-token.html",
    "invalid-token.html"
]

frontend_dir = "/Users/likithnaidu/Desktop/forms-project/frontend"

# The replacement block for pages that do backend operations
replacement_code = """    const CONFIG = {
      BACKEND_URL:
        window.location.hostname === "localhost" ||
        window.location.hostname === "127.0.0.1"
          ? "http://localhost:8000"
          : "https://forms-project-qcdc.onrender.com"
    };

    if (
      !window.location.hostname.includes("localhost") &&
      !window.location.hostname.includes("127.0.0.1") &&
      CONFIG.BACKEND_URL.includes("localhost")
    ) {
      window.location.href = "/problem.html?reason=production_backend_url_misconfigured";
    }

    const BACKEND_URL = CONFIG.BACKEND_URL;"""

# The block for static pages that might not need BACKEND_URL but require the safety check
static_replacement_code = """    const CONFIG = {
      BACKEND_URL:
        window.location.hostname === "localhost" ||
        window.location.hostname === "127.0.0.1"
          ? "http://localhost:8000"
          : "https://forms-project-qcdc.onrender.com"
    };

    if (
      !window.location.hostname.includes("localhost") &&
      !window.location.hostname.includes("127.0.0.1") &&
      CONFIG.BACKEND_URL.includes("localhost")
    ) {
      window.location.href = "/problem.html?reason=production_backend_url_misconfigured";
    }"""

for filename in HTML_FILES:
    file_path = os.path.join(frontend_dir, filename)
    if not os.path.exists(file_path):
        print(f"Skipping non-existent file: {filename}")
        continue
        
    print(f"Patching {filename}...")
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    if 'const BACKEND_URL = "https://forms-project-qcdc.onrender.com";' in content:
        content = content.replace(
            'const BACKEND_URL = "https://forms-project-qcdc.onrender.com";',
            replacement_code
        )
    elif "const BACKEND_URL = 'https://forms-project-qcdc.onrender.com';" in content:
        content = content.replace(
            "const BACKEND_URL = 'https://forms-project-qcdc.onrender.com';",
            replacement_code
        )
    else:
        # Static page, look for the first <script> tag and insert right after it
        if "<script>" in content:
            content = content.replace(
                "<script>",
                f"<script>\n{static_replacement_code}"
            )
            
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
print("All HTML files patched successfully!")
