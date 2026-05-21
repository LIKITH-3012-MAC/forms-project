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
