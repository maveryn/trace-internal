function setupThemeSwitch() {
  const root = document.documentElement;
  const buttons = Array.from(document.querySelectorAll("[data-theme-choice]"));
  if (!buttons.length) {
    return;
  }

  function normalizeTheme(value) {
    return value === "light" || value === "dark" ? value : "dark";
  }

  function applyTheme(theme) {
    const resolved = normalizeTheme(theme);
    root.dataset.theme = resolved;
    try {
      window.localStorage.setItem("trace-review-theme", resolved);
    } catch {
      /* Ignore storage failures; the current page still gets the selected theme. */
    }
    buttons.forEach((button) => {
      const active = button.getAttribute("data-theme-choice") === resolved;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  let storedTheme = "dark";
  try {
    storedTheme = normalizeTheme(window.localStorage.getItem("trace-review-theme"));
  } catch {
    storedTheme = "dark";
  }
  applyTheme(root.dataset.theme || storedTheme);

  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      applyTheme(button.getAttribute("data-theme-choice"));
    });
  });
}

document.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-reload]");
  if (!button) {
    return;
  }
  event.preventDefault();
  button.disabled = true;
  button.textContent = "Reloading...";
  const base = window.TRACE_REVIEW_BASE || "";
  try {
    const response = await fetch(`${base}/api/reload`, { method: "POST" });
    if (!response.ok) {
      throw new Error(`reload failed: ${response.status}`);
    }
    window.location.reload();
  } catch (error) {
    button.textContent = "Reload failed";
    console.error(error);
  }
});

function setupSearchSuggestions() {
  const input = document.getElementById("review-search");
  const suggestions = document.getElementById("search-suggestions");
  if (!input || !suggestions) {
    return;
  }

  const suggestUrl = input.getAttribute("data-suggest-url");
  if (!suggestUrl) {
    return;
  }

  let results = [];
  let selectedIndex = -1;
  let timer = null;
  let controller = null;

  function hideSuggestions() {
    results = [];
    selectedIndex = -1;
    suggestions.replaceChildren();
    suggestions.hidden = true;
  }

  function setSelected(index) {
    selectedIndex = index;
    const rows = Array.from(suggestions.querySelectorAll(".suggestion-row"));
    rows.forEach((row, rowIndex) => {
      const active = rowIndex === selectedIndex;
      row.classList.toggle("active", active);
      row.setAttribute("aria-selected", active ? "true" : "false");
      if (active) {
        row.scrollIntoView({ block: "nearest" });
      }
    });
  }

  function navigateTo(result) {
    if (result && result.url) {
      window.location.href = result.url;
    }
  }

  function renderSuggestions(nextResults) {
    results = Array.isArray(nextResults) ? nextResults : [];
    selectedIndex = -1;
    suggestions.replaceChildren();

    if (!results.length) {
      suggestions.hidden = true;
      return;
    }

    results.forEach((result, index) => {
      const row = document.createElement("button");
      row.type = "button";
      row.className = "suggestion-row";
      row.setAttribute("role", "option");
      row.setAttribute("aria-selected", "false");

      const type = document.createElement("span");
      type.className = "suggestion-type";
      type.textContent = result.type || "match";

      const text = document.createElement("span");
      const label = document.createElement("span");
      label.className = "suggestion-label";
      label.textContent = result.label || "";
      const subtitle = document.createElement("span");
      subtitle.className = "suggestion-subtitle";
      subtitle.textContent = result.subtitle || "";
      text.append(label, subtitle);

      row.append(type, text);
      row.addEventListener("mousedown", (event) => event.preventDefault());
      row.addEventListener("mouseenter", () => setSelected(index));
      row.addEventListener("click", () => navigateTo(result));
      suggestions.append(row);
    });

    suggestions.hidden = false;
  }

  async function fetchSuggestions() {
    const query = input.value.trim();
    if (query.length < 2) {
      hideSuggestions();
      return;
    }

    if (controller) {
      controller.abort();
    }
    controller = new AbortController();

    try {
      const url = `${suggestUrl}?q=${encodeURIComponent(query)}`;
      const response = await fetch(url, { signal: controller.signal });
      if (!response.ok) {
        throw new Error(`suggest failed: ${response.status}`);
      }
      const payload = await response.json();
      if (input.value.trim() !== query) {
        return;
      }
      renderSuggestions(payload.results || []);
    } catch (error) {
      if (error.name !== "AbortError") {
        hideSuggestions();
        console.error(error);
      }
    }
  }

  function scheduleFetch() {
    window.clearTimeout(timer);
    timer = window.setTimeout(fetchSuggestions, 120);
  }

  input.addEventListener("input", scheduleFetch);
  input.addEventListener("focus", () => {
    if (input.value.trim().length >= 2) {
      fetchSuggestions();
    }
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      hideSuggestions();
      return;
    }
    if (!results.length) {
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setSelected((selectedIndex + 1) % results.length);
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setSelected(selectedIndex <= 0 ? results.length - 1 : selectedIndex - 1);
      return;
    }
    if (event.key === "Enter" && selectedIndex >= 0) {
      event.preventDefault();
      navigateTo(results[selectedIndex]);
    }
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest(".global-search")) {
      hideSuggestions();
    }
  });
}

function setupPreviewSwitch() {
  const root = document.querySelector("[data-preview-root]");
  if (!root) {
    return;
  }

  const buttons = Array.from(document.querySelectorAll("[data-preview-switch]"));

  function normalizeView(value) {
    return value === "images" ? "images" : "rows";
  }

  function findVisibleSampleUid() {
    const activeView = normalizeView(root.getAttribute("data-active-view"));
    const panel = root.querySelector(`[data-preview-panel="${activeView}"]`);
    if (!panel) {
      return "";
    }
    const cards = Array.from(panel.querySelectorAll("[data-sample-uid]"));
    const anchorY = Math.min(window.innerHeight * 0.28, 220);
    let best = null;
    for (const card of cards) {
      const rect = card.getBoundingClientRect();
      if (rect.bottom <= 0 || rect.top >= window.innerHeight) {
        continue;
      }
      const score = Math.abs(rect.top - anchorY);
      if (!best || score < best.score) {
        best = { uid: card.getAttribute("data-sample-uid") || "", score };
      }
    }
    return best ? best.uid : "";
  }

  function updateLinks(view) {
    const nextUrl = new URL(window.location.href);
    nextUrl.searchParams.set("view", view);
    window.history.replaceState(null, "", nextUrl);
    const base = window.TRACE_REVIEW_BASE || "";
    let nextPathname = nextUrl.pathname;
    if (base && (nextPathname === base || nextPathname.startsWith(`${base}/`))) {
      nextPathname = nextPathname.slice(base.length) || "/";
    }
    const nextPath = `${nextPathname}${nextUrl.search}${nextUrl.hash}`;

    document.querySelectorAll('input[name="next"]').forEach((input) => {
      input.value = nextPath;
    });

    document.querySelectorAll('a[href*="view="]').forEach((link) => {
      const rawHref = link.getAttribute("href");
      if (!rawHref) {
        return;
      }
      const url = new URL(rawHref, window.location.origin);
      url.searchParams.set("view", view);
      link.setAttribute("href", `${url.pathname}${url.search}${url.hash}`);
    });
  }

  function applyView(view, sampleUid) {
    const resolved = normalizeView(view);
    root.setAttribute("data-active-view", resolved);
    buttons.forEach((button) => {
      const active = button.getAttribute("data-preview-switch") === resolved;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });
    updateLinks(resolved);
    if (sampleUid) {
      window.requestAnimationFrame(() => {
        const target = root.querySelector(`[data-preview-panel="${resolved}"] [data-sample-uid="${sampleUid}"]`);
        if (target) {
          target.scrollIntoView({ block: "nearest" });
        }
      });
    }
  }

  applyView(root.getAttribute("data-active-view"), "");

  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      const nextView = normalizeView(button.getAttribute("data-preview-switch"));
      const currentView = normalizeView(root.getAttribute("data-active-view"));
      if (nextView === currentView) {
        return;
      }
      applyView(nextView, findVisibleSampleUid());
    });
  });
}

function setupOpenFeedbackFilter() {
  const root = document.querySelector("[data-preview-root]");
  const buttons = Array.from(document.querySelectorAll("[data-open-feedback-filter]"));
  if (!root || !buttons.length) {
    return;
  }

  function setEnabled(enabled) {
    root.setAttribute("data-open-feedback-only", enabled ? "true" : "false");
    buttons.forEach((button) => {
      button.classList.toggle("active", enabled);
      button.setAttribute("aria-pressed", enabled ? "true" : "false");
    });
  }

  setEnabled(false);
  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      setEnabled(root.getAttribute("data-open-feedback-only") !== "true");
    });
  });
}

function setupTaskFeedbackToggle() {
  const toggle = document.querySelector("[data-task-feedback-toggle]");
  const form = document.querySelector("[data-task-feedback-form]");
  if (!toggle || !form) {
    return;
  }
  const close = form.querySelector("[data-task-feedback-close]");
  const textarea = form.querySelector("textarea");

  function setOpen(open) {
    form.hidden = !open;
    document.body.classList.toggle("task-feedback-open", open);
    toggle.classList.toggle("active", open);
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    if (open && textarea) {
      window.setTimeout(() => textarea.focus(), 0);
    }
  }

  toggle.addEventListener("click", (event) => {
    event.preventDefault();
    setOpen(form.hidden);
  });

  if (close) {
    close.addEventListener("click", (event) => {
      event.preventDefault();
      setOpen(false);
    });
  }

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !form.hidden) {
      setOpen(false);
    }
  });

  document.addEventListener("click", (event) => {
    if (form.hidden) {
      return;
    }
    if (event.target.closest("[data-task-feedback-form]")) {
      return;
    }
    if (event.target.closest("[data-task-feedback-toggle]")) {
      return;
    }
    const sampleLink = event.target.closest(".sample-row a, .image-only-card a");
    if (sampleLink) {
      event.preventDefault();
    }
    setOpen(false);
  });
}

setupThemeSwitch();
setupSearchSuggestions();
setupPreviewSwitch();
setupOpenFeedbackFilter();
setupTaskFeedbackToggle();
