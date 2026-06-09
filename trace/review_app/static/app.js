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

function setupSelectableTextLinks() {
  document.addEventListener(
    "click",
    (event) => {
      if (!event.target.closest("[data-selectable-text]")) {
        return;
      }
      const selection = window.getSelection ? window.getSelection() : null;
      if (selection && selection.toString().trim()) {
        event.preventDefault();
        event.stopPropagation();
      }
    },
    true,
  );

  document.addEventListener("dragstart", (event) => {
    if (event.target.closest("[data-selectable-text]")) {
      event.preventDefault();
    }
  });
}

function setupResourceTabs() {
  const nav = document.querySelector("[data-resource-tabs]");
  if (!nav) {
    return;
  }

  const tabs = Array.from(nav.querySelectorAll("[data-resource-tab]"));
  const sections = tabs
    .map((tab) => document.getElementById(tab.getAttribute("data-resource-tab") || ""))
    .filter(Boolean);
  if (!tabs.length || !sections.length) {
    return;
  }

  function setActive(sectionId) {
    tabs.forEach((tab) => {
      const active = tab.getAttribute("data-resource-tab") === sectionId;
      tab.classList.toggle("active", active);
      tab.setAttribute("aria-current", active ? "location" : "false");
    });
  }

  function currentSectionId() {
    const anchorY = Math.min(window.innerHeight * 0.32, 240);
    let current = sections[0];
    for (const section of sections) {
      if (section.getBoundingClientRect().top <= anchorY) {
        current = section;
      } else {
        break;
      }
    }
    return current.id;
  }

  let frame = 0;
  function scheduleUpdate() {
    if (frame) {
      return;
    }
    frame = window.requestAnimationFrame(() => {
      frame = 0;
      setActive(currentSectionId());
    });
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      setActive(tab.getAttribute("data-resource-tab") || "");
    });
  });
  window.addEventListener("scroll", scheduleUpdate, { passive: true });
  window.addEventListener("resize", scheduleUpdate);
  window.addEventListener("hashchange", scheduleUpdate);
  scheduleUpdate();
}

function setupIllustrationObjectReviewForms() {
  const forms = Array.from(document.querySelectorAll("[data-illustration-review-form]"));
  if (!forms.length) {
    return;
  }

  const decisionClasses = ["approve", "remove", "improve", "unreviewed"];

  function setSelectedDecision(form, decision) {
    form.querySelectorAll(".illustration-object-decision-row label").forEach((label) => {
      const input = label.querySelector('input[name="decision"]');
      const selected = input && input.value === decision;
      label.classList.toggle("selected", Boolean(selected));
    });
  }

  function updateCount(decision, delta) {
    const counter = document.querySelector(`[data-illustration-review-count="${decision}"]`);
    if (!counter) {
      return;
    }
    const current = Number.parseInt(counter.textContent || "0", 10);
    counter.textContent = String(Math.max(0, (Number.isFinite(current) ? current : 0) + delta));
  }

  function updateCardDecision(card, decision, statusLabel) {
    const previous = card.getAttribute("data-decision") || "unreviewed";
    if (previous !== decision) {
      updateCount(previous, -1);
      updateCount(decision, 1);
    }
    card.setAttribute("data-decision", decision);
    decisionClasses.forEach((name) => {
      card.classList.toggle(`decision-${name}`, name === decision);
    });

    const status = card.querySelector("[data-illustration-object-status]");
    if (status) {
      decisionClasses.forEach((name) => status.classList.remove(name));
      status.classList.add(decision);
      status.textContent = statusLabel || decision;
    }
    const grid = card.closest(".illustration-object-grid");
    const activeFilter = grid ? grid.getAttribute("data-selected-decision-filter") || "" : "";
    if (activeFilter && activeFilter !== decision) {
      updateCount("shown", -1);
      card.remove();
    }
  }

  forms.forEach((form) => {
    form.querySelectorAll('input[name="decision"]').forEach((input) => {
      input.addEventListener("change", () => {
        setSelectedDecision(form, input.value);
      });
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = form.querySelector('button[type="submit"]');
      const originalText = button ? button.textContent : "";
      if (button) {
        button.disabled = true;
        button.textContent = "Saving...";
      }

      try {
        const response = await fetch(form.action, {
          method: "POST",
          body: new FormData(form),
          headers: {
            Accept: "application/json",
            "X-Requested-With": "fetch",
          },
        });
        if (!response.ok) {
          throw new Error(`save failed: ${response.status}`);
        }
        const payload = await response.json();
        const card = form.closest("[data-illustration-object-card]");
        if (card) {
          updateCardDecision(card, payload.decision || "unreviewed", payload.status_label || "Unreviewed");
        }
        if (payload.review) {
          const saved = form.querySelector("[data-illustration-review-saved]");
          if (saved && payload.review.updated_at) {
            saved.hidden = false;
            saved.textContent = `Last saved ${payload.review.updated_at}`;
          }
          const updatedBy = form.querySelector('input[name="updated_by"]');
          if (updatedBy && payload.review.updated_by !== undefined) {
            updatedBy.value = payload.review.updated_by || "";
          }
        }
        if (button) {
          button.textContent = "Saved";
          window.setTimeout(() => {
            button.textContent = originalText || "Save";
          }, 900);
        }
      } catch (error) {
        console.error(error);
        if (button) {
          button.textContent = "Save failed";
          window.setTimeout(() => {
            button.textContent = originalText || "Save";
          }, 1400);
        }
      } finally {
        if (button) {
          window.setTimeout(() => {
            button.disabled = false;
          }, 120);
        }
      }
    });
  });
}

function setupThreeDObjectReviewForms() {
  const forms = Array.from(document.querySelectorAll("[data-three-d-review-form]"));
  if (!forms.length) {
    return;
  }

  const decisionClasses = ["approve", "remove", "improve", "unreviewed"];

  function setSelectedDecision(form, decision) {
    form.querySelectorAll(".three-d-object-decision-row label").forEach((label) => {
      const input = label.querySelector('input[name="decision"]');
      const selected = input && input.value === decision;
      label.classList.toggle("selected", Boolean(selected));
    });
  }

  function updateCount(decision, delta) {
    const counter = document.querySelector(`[data-three-d-review-count="${decision}"]`);
    if (!counter) {
      return;
    }
    const current = Number.parseInt(counter.textContent || "0", 10);
    counter.textContent = String(Math.max(0, (Number.isFinite(current) ? current : 0) + delta));
  }

  function updateCardDecision(card, decision, statusLabel) {
    const previous = card.getAttribute("data-decision") || "unreviewed";
    if (previous !== decision) {
      updateCount(previous, -1);
      updateCount(decision, 1);
    }
    card.setAttribute("data-decision", decision);
    decisionClasses.forEach((name) => {
      card.classList.toggle(`decision-${name}`, name === decision);
    });

    const status = card.querySelector("[data-three-d-object-status]");
    if (status) {
      decisionClasses.forEach((name) => status.classList.remove(name));
      status.classList.add(decision);
      status.textContent = statusLabel || decision;
    }
    const grid = card.closest(".three-d-object-grid");
    const activeFilter = grid ? grid.getAttribute("data-selected-decision-filter") || "" : "";
    if (activeFilter && activeFilter !== decision) {
      updateCount("shown", -1);
      card.remove();
    }
  }

  forms.forEach((form) => {
    form.querySelectorAll('input[name="decision"]').forEach((input) => {
      input.addEventListener("change", () => {
        setSelectedDecision(form, input.value);
      });
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = form.querySelector('button[type="submit"]');
      const originalText = button ? button.textContent : "";
      if (button) {
        button.disabled = true;
        button.textContent = "Saving...";
      }

      try {
        const response = await fetch(form.action, {
          method: "POST",
          body: new FormData(form),
          headers: {
            Accept: "application/json",
            "X-Requested-With": "fetch",
          },
        });
        if (!response.ok) {
          throw new Error(`save failed: ${response.status}`);
        }
        const payload = await response.json();
        const card = form.closest("[data-three-d-object-card]");
        if (card) {
          updateCardDecision(card, payload.decision || "unreviewed", payload.status_label || "Unreviewed");
        }
        if (payload.review) {
          const saved = form.querySelector("[data-three-d-review-saved]");
          if (saved && payload.review.updated_at) {
            saved.hidden = false;
            saved.textContent = `Last saved ${payload.review.updated_at}`;
          }
          const updatedBy = form.querySelector('input[name="updated_by"]');
          if (updatedBy && payload.review.updated_by !== undefined) {
            updatedBy.value = payload.review.updated_by || "";
          }
        }
        if (button) {
          button.textContent = "Saved";
          window.setTimeout(() => {
            button.textContent = originalText || "Save";
          }, 900);
        }
      } catch (error) {
        console.error(error);
        if (button) {
          button.textContent = "Save failed";
          window.setTimeout(() => {
            button.textContent = originalText || "Save";
          }, 1400);
        }
      } finally {
        if (button) {
          window.setTimeout(() => {
            button.disabled = false;
          }, 120);
        }
      }
    });
  });
}

setupThemeSwitch();
setupSearchSuggestions();
setupPreviewSwitch();
setupOpenFeedbackFilter();
setupTaskFeedbackToggle();
setupSelectableTextLinks();
setupResourceTabs();
setupIllustrationObjectReviewForms();
setupThreeDObjectReviewForms();
