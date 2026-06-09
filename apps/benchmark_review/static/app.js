(() => {
  const root = document.documentElement;
  const storageKey = "trace-benchmark-review-theme";

  function applyTheme(theme) {
    const value = theme === "light" ? "light" : "dark";
    root.dataset.theme = value;
    document.querySelectorAll("[data-theme-choice]").forEach((button) => {
      button.setAttribute("aria-pressed", button.dataset.themeChoice === value ? "true" : "false");
    });
    try {
      window.localStorage.setItem(storageKey, value);
    } catch {}
  }

  let initial = "dark";
  try {
    initial = window.localStorage.getItem(storageKey) || "dark";
  } catch {}
  applyTheme(initial);

  document.querySelectorAll("[data-theme-choice]").forEach((button) => {
    button.addEventListener("click", () => applyTheme(button.dataset.themeChoice));
  });

  setupSampleShuffle();

  const input = document.getElementById("benchmark-search");
  const box = document.getElementById("search-suggestions");
  if (!input || !box || !input.dataset.suggestUrl) return;

  let controller = null;
  input.addEventListener("input", async () => {
    const q = input.value.trim();
    if (controller) controller.abort();
    if (!q) {
      box.hidden = true;
      box.innerHTML = "";
      return;
    }
    controller = new AbortController();
    try {
      const response = await fetch(`${input.dataset.suggestUrl}?q=${encodeURIComponent(q)}`, {
        signal: controller.signal,
      });
      const payload = await response.json();
      const rows = payload.results || [];
      if (!rows.length) {
        box.hidden = true;
        box.innerHTML = "";
        return;
      }
      box.innerHTML = rows
        .map((row) => `<a href="${row.url}"><strong>${escapeHtml(row.label)}</strong><small>${escapeHtml(row.type)} - ${escapeHtml(row.detail || "")}</small></a>`)
        .join("");
      box.hidden = false;
    } catch (error) {
      if (error.name !== "AbortError") {
        box.hidden = true;
      }
    }
  });

  document.addEventListener("click", (event) => {
    if (!box.contains(event.target) && event.target !== input) {
      box.hidden = true;
    }
  });

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function setupSampleShuffle() {
    const toggle = document.querySelector("[data-row-order-toggle]");
    const table = document.querySelector("[data-sample-table]");
    if (!toggle || !table) {
      return;
    }

    const buttons = Array.from(toggle.querySelectorAll("[data-row-order]"));
    const originalRows = Array.from(table.querySelectorAll(".sample-row"));
    if (originalRows.length < 2) {
      buttons.forEach((button) => {
        button.disabled = true;
      });
      return;
    }

    function setRows(rows) {
      const fragment = document.createDocumentFragment();
      rows.forEach((row) => fragment.appendChild(row));
      table.appendChild(fragment);
    }

    function shuffledRows() {
      const rows = Array.from(originalRows);
      for (let index = rows.length - 1; index > 0; index -= 1) {
        const swapIndex = Math.floor(Math.random() * (index + 1));
        [rows[index], rows[swapIndex]] = [rows[swapIndex], rows[index]];
      }
      return rows;
    }

    function setOrder(order) {
      const shuffled = order === "shuffle";
      buttons.forEach((button) => {
        button.setAttribute("aria-checked", button.dataset.rowOrder === order ? "true" : "false");
      });
      setRows(shuffled ? shuffledRows() : originalRows);
    }

    buttons.forEach((button) => {
      button.addEventListener("click", () => {
        setOrder(button.dataset.rowOrder === "shuffle" ? "shuffle" : "original");
      });
    });
  }
})();
