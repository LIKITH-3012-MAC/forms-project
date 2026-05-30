/* Premium Theme Toggle System Script */

function setupThemeToggle() {
  const btn = document.getElementById("themeToggle");
  const icon = document.getElementById("themeIcon");

  if (!btn || !icon) return;

  function syncIcon() {
    const current = document.documentElement.getAttribute("data-theme") || "dark";
    icon.textContent = current === "light" ? "🌙" : "☀️";
    
    const ariaText = current === "light" ? "Switch to dark mode" : "Switch to light mode";
    btn.setAttribute("aria-label", ariaText);
    btn.setAttribute("title", ariaText);
  }

  syncIcon();

  btn.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme") || "dark";
    const next = current === "dark" ? "light" : "dark";

    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem("event-theme", next);

    const metaTheme = document.querySelector("meta[name='theme-color']");
    if (metaTheme) {
      metaTheme.setAttribute("content", next === "light" ? "#f8fafc" : "#020617");
    }

    syncIcon();
    
    // Dispatch a custom event for widgets (like charts) to adapt programmatically
    document.dispatchEvent(new CustomEvent("themechanged", { detail: { theme: next } }));
  });
}

// Bind to early DOM readiness
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", setupThemeToggle);
} else {
  setupThemeToggle();
}


/* Button State Management & Fetch Utility Extensions */

function setButtonLoading(button, loadingText = "Processing...") {
  if (!button) return;

  if (!button.dataset.originalHtml) {
    button.dataset.originalHtml = button.innerHTML;
  }

  button.disabled = true;
  button.setAttribute("aria-busy", "true");
  button.classList.add("is-loading");

  button.innerHTML = `
    <span class="spinner" aria-hidden="true"></span>
    <span>${loadingText}</span>
  `;
}

function resetButton(button) {
  if (!button) return;

  button.disabled = false;
  button.removeAttribute("aria-busy");
  button.classList.remove("is-loading");

  if (button.dataset.originalHtml) {
    button.innerHTML = button.dataset.originalHtml;
  }
}

function markButtonSuccess(button, text = "Done ✅") {
  if (!button) return;

  button.classList.remove("is-loading");
  button.classList.add("is-success");
  button.innerHTML = `<span>${text}</span>`;

  setTimeout(() => {
    button.classList.remove("is-success");
    resetButton(button);
  }, 900);
}

function markButtonError(button, text = "Try Again") {
  if (!button) return;

  button.classList.remove("is-loading");
  button.classList.add("is-error");
  button.innerHTML = `<span>${text}</span>`;

  setTimeout(() => {
    button.classList.remove("is-error");
    resetButton(button);
  }, 1200);
}

async function apiFetch(path, options = {}, timeoutMs = 15000) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  const backendUrl = typeof CONFIG !== "undefined" && CONFIG.BACKEND_URL 
    ? CONFIG.BACKEND_URL 
    : (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" 
       ? "http://localhost:8000" 
       : "https://forms-project-p7np.onrender.com");

  try {
    const res = await fetch(`${backendUrl}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...(options.headers || {})
      }
    });

    const contentType = res.headers.get("content-type") || "";
    const data = contentType.includes("application/json")
      ? await res.json()
      : await res.text();

    if (!res.ok) {
      const message = typeof data === "object"
        ? data.message || data.detail || "Request failed"
        : "Request failed";
      const error = new Error(message);
      error.status = res.status;
      throw error;
    }

    return data;
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("Request timed out. Please try again.");
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

async function apiFetchWithRetry(path, options = {}) {
  try {
    return await apiFetch(path, options, 15000);
  } catch (err) {
    if (!options.method || options.method === "GET") {
      await new Promise(resolve => setTimeout(resolve, 800));
      return await apiFetch(path, options, 15000);
    }
    throw err;
  }
}

