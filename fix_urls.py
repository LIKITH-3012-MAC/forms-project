import os
import re

FRONTEND_DIR = "/Users/likithnaidu/Desktop/forms-project/frontend"

CONFIG_SCRIPT = """<script>
  const CONFIG = {
    BACKEND_URL:
      window.location.hostname === "localhost" ||
      window.location.hostname === "127.0.0.1"
        ? "http://localhost:8000"
        : "https://YOUR-RENDER-BACKEND-DOMAIN.onrender.com"
  };

  if (
    !window.location.hostname.includes("localhost") &&
    CONFIG.BACKEND_URL.includes("localhost")
  ) {
    window.location.href = "/problem.html?reason=production_backend_url_misconfigured";
  }
</script>"""

for filename in os.listdir(FRONTEND_DIR):
    if not filename.endswith(".html"):
        continue
    filepath = os.path.join(FRONTEND_DIR, filename)
    with open(filepath, "r") as f:
        content = f.read()

    # 1. Insert CONFIG block
    if "const CONFIG = {" not in content:
        # Insert right after <head>
        content = content.replace("<head>", f"<head>\n  {CONFIG_SCRIPT}")

    # 2. Fix fetch URLs
    # Case 1: fetch("http://localhost:8000/api/...")
    # We replace "http://localhost:8000 with `${CONFIG.BACKEND_URL} if we convert to backticks.
    # Alternatively, replace "http://localhost:8000" with CONFIG.BACKEND_URL (as string concat).
    
    # We will use string concatenation to be safe: CONFIG.BACKEND_URL + "/api..."
    content = re.sub(r'["\']http://localhost:8000', 'CONFIG.BACKEND_URL + "', content)
    content = re.sub(r'["\']http://127.0.0.1:8000', 'CONFIG.BACKEND_URL + "', content)

    # Clean up double string concat if it happens: CONFIG.BACKEND_URL + "" + ...
    content = content.replace('CONFIG.BACKEND_URL + ""', 'CONFIG.BACKEND_URL')

    # 3. Fix frontend HREFs and window.location
    content = re.sub(r'["\']http://localhost:5500/', '"/', content)
    content = re.sub(r'["\']http://127.0.0.1:5500/', '"/', content)

    with open(filepath, "w") as f:
        f.write(content)

print("Frontend files updated.")
