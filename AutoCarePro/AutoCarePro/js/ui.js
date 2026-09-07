/* ==========================================================================
   AutoCare Pro — ui.js
   The presentation toolkit: reusable markup builders plus the modal, toast
   and confirmation systems. Nothing here reads the database directly — pages
   pass in the data they have already computed.
   ========================================================================== */

window.AC = window.AC || {};

AC.ui = (function () {
  "use strict";

  const U = AC.utils;
  const I = AC.icons;

  /* ====================================================== markup builders == */

  /**
   * @param {object} cfg
   * @param {"number"|"money"|"pad"} [cfg.format] how the count-up renders
   */
  function metricCard({ label, value, foot, icon, tone, unit, counter = true, id, format = "number" }) {
    const toneClass = tone ? ` is-${tone}` : "";
    const idAttr = id ? ` id="${id}"` : "";
    const fmt = format === "money" ? ' data-money="true"' : format === "pad" ? ' data-pad="true"' : "";
    const dataCount = counter ? ` data-count="${Number(value) || 0}"${fmt}` : "";
    return `
      <article class="card metric-card card--interactive">
        <div class="card__scanline"></div>
        <div class="metric${toneClass}">
          <span class="metric__label">${U.esc(label)}</span>
          <span class="metric__value counter"${idAttr}${dataCount}>${U.esc(
      counter ? "0" : value
    )}${unit ? `<span class="metric__unit">${U.esc(unit)}</span>` : ""}</span>
          ${foot ? `<span class="metric__foot">${U.esc(foot)}</span>` : ""}
        </div>
        ${icon ? `<span class="metric__icon">${I.get(icon, { size: 16 })}</span>` : ""}
      </article>`;
  }

  function statusPill(label, tone = "muted", opts = {}) {
    const cls = ["pill", `pill--${tone}`];
    if (opts.live) cls.push("pill--live");
    if (opts.plain) cls.push("pill--plain");
    return `<span class="${cls.join(" ")}">${U.esc(label)}</span>`;
  }

  /**
   * Progress bar. The fill starts at 0 and is animated to its real width by
   * `activateBars()` after the markup is in the DOM.
   */
  function progressBar({ label, value, max = 100, tone = "", suffix = "%", hint }) {
    const pct = U.clamp((Number(value) / max) * 100, 0, 100);
    return `
      <div class="bar${tone ? ` bar--${tone}` : ""}">
        <div class="bar__head">
          <span class="bar__label">${U.esc(label)}</span>
          <span class="bar__value">${U.esc(Math.round(Number(value)))}${U.esc(suffix)}</span>
        </div>
        <div class="bar__track">
          <div class="bar__fill" data-width="${pct}"></div>
        </div>
        ${hint ? `<span class="field__hint">${U.esc(hint)}</span>` : ""}
      </div>`;
  }

  function emptyState({ icon = "layers", title, text, actionLabel, actionEvent, actionAttrs = "" }) {
    return `
      <div class="empty">
        <span class="empty__icon">${I.get(icon, { size: 24 })}</span>
        <h3 class="empty__title">${U.esc(title)}</h3>
        <p class="empty__text">${U.esc(text)}</p>
        ${
          actionLabel
            ? `<button class="btn btn--primary" data-action="${U.esc(actionEvent)}" ${actionAttrs}>
                 ${I.get("plus", { size: 16 })}<span>${U.esc(actionLabel)}</span>
               </button>`
            : ""
        }
      </div>`;
  }

  function banner(text, tone = "info", icon = "info") {
    return `<div class="banner banner--${tone}">${I.get(icon, { size: 17 })}<span>${text}</span></div>`;
  }

  function alertRow(alert) {
    const action = alert.action
      ? `<button class="btn btn--ghost btn--sm alert__action" data-alert-action="${U.esc(
          alert.id
        )}">${U.esc(alert.action.label)}</button>`
      : "";
    return `
      <div class="alert alert--${U.esc(alert.priority)}">
        <span class="alert__icon">${I.get(alert.icon || "info", { size: 15 })}</span>
        <div class="alert__body">
          <div class="alert__title">${U.esc(alert.title)}</div>
          <div class="alert__meta">${U.esc(alert.meta)}</div>
        </div>
        ${action}
      </div>`;
  }

  const demoFlag = () => `<span class="demo-flag">${I.get("database", { size: 11 })} Demo data</span>`;

  function sectionHead(title, hint, actionsHtml = "") {
    return `
      <div class="section-head">
        <div>
          <h2>${U.esc(title)}</h2>
          ${hint ? `<div class="section-head__hint">${U.esc(hint)}</div>` : ""}
        </div>
        ${actionsHtml}
      </div>`;
  }

  /* ---- form field builders ------------------------------------------------ */

  function field({ name, label, type = "text", value = "", required = false, hint, attrs = "", full = false }) {
    return `
      <div class="field${full ? " field--full" : ""}">
        <label for="f-${name}">${U.esc(label)}${required ? ' <span class="req">*</span>' : ""}</label>
        <input class="input" id="f-${name}" name="${name}" type="${type}" value="${U.esc(value)}" ${attrs} />
        ${hint ? `<span class="field__hint">${U.esc(hint)}</span>` : ""}
        <span class="field__error" data-error-for="${name}"></span>
      </div>`;
  }

  function selectField({ name, label, options, value = "", required = false, hint, full = false }) {
    const opts = options
      .map(
        (o) =>
          `<option value="${U.esc(o.value)}"${String(o.value) === String(value) ? " selected" : ""}>${U.esc(
            o.label
          )}</option>`
      )
      .join("");
    return `
      <div class="field${full ? " field--full" : ""}">
        <label for="f-${name}">${U.esc(label)}${required ? ' <span class="req">*</span>' : ""}</label>
        <select class="select" id="f-${name}" name="${name}">${opts}</select>
        ${hint ? `<span class="field__hint">${U.esc(hint)}</span>` : ""}
        <span class="field__error" data-error-for="${name}"></span>
      </div>`;
  }

  function textareaField({ name, label, value = "", hint, full = true }) {
    return `
      <div class="field${full ? " field--full" : ""}">
        <label for="f-${name}">${U.esc(label)}</label>
        <textarea class="textarea" id="f-${name}" name="${name}" rows="3">${U.esc(value)}</textarea>
        ${hint ? `<span class="field__hint">${U.esc(hint)}</span>` : ""}
        <span class="field__error" data-error-for="${name}"></span>
      </div>`;
  }

  function switchField({ name, label, checked = false }) {
    return `
      <label class="switch">
        <input type="checkbox" name="${name}" ${checked ? "checked" : ""} />
        <span class="switch__track"></span>
        <span>${U.esc(label)}</span>
      </label>`;
  }

  /* ========================================================= animation ==== */

  /** Kick off every count-up and progress bar inside `root`. */
  function activate(root = document) {
    U.$$("[data-count]", root).forEach((el) => {
      const target = Number(el.dataset.count) || 0;
      const unitEl = el.querySelector(".metric__unit");
      const unitHtml = unitEl ? unitEl.outerHTML : "";
      const pad = el.dataset.pad === "true";
      const money = el.dataset.money === "true";
      const format = money
        ? U.formatCurrency
        : pad
        ? (n) => U.pad2(n)
        : U.formatNumber;
      const holder = document.createElement("span");
      el.textContent = "";
      el.appendChild(holder);
      if (unitHtml) el.insertAdjacentHTML("beforeend", unitHtml);
      U.countUp(holder, target, { format });
    });

    // Two frames: let layout settle so the transition actually runs.
    U.raf(() =>
      U.raf(() => {
        U.$$(".bar__fill[data-width]", root).forEach((el) => {
          el.style.width = `${el.dataset.width}%`;
        });
      })
    );
  }

  /* ============================================================ toasts ==== */

  const TOAST_ICONS = { success: "check", error: "alert", warning: "alert", info: "info" };

  function toast(message, { title, type = "success", duration = 3600 } = {}) {
    const stack = U.$("#toastStack");
    if (!stack) return;
    const el = document.createElement("div");
    el.className = `toast toast--${type}`;
    el.setAttribute("role", type === "error" ? "alert" : "status");
    el.innerHTML = `
      <span class="toast__icon">${I.get(TOAST_ICONS[type] || "info", { size: 18 })}</span>
      <div class="toast__body">
        <div class="toast__title">${U.esc(title || defaultTitle(type))}</div>
        <div class="toast__msg">${U.esc(message)}</div>
      </div>
      <button class="icon-btn" aria-label="Dismiss notification" style="width:26px;height:26px">
        ${I.get("close", { size: 14 })}
      </button>`;

    const dismiss = () => {
      el.classList.add("is-out");
      setTimeout(() => el.remove(), 200);
    };
    el.querySelector("button").addEventListener("click", dismiss);
    stack.appendChild(el);
    if (duration) setTimeout(dismiss, duration);
  }

  const defaultTitle = (type) =>
    ({ success: "Done", error: "Something went wrong", warning: "Heads up", info: "Note" }[type] || "Note");

  /* ============================================================= modal ==== */

  let activeModal = null;
  let lastFocused = null;

  /**
   * Open a modal.
   * @param {object} cfg { title, subtitle, body, footer, size, onMount, onSubmit }
   * @returns {HTMLElement} the modal element
   */
  function openModal(cfg) {
    closeModal(true);
    lastFocused = document.activeElement;

    const root = U.$("#modalRoot");
    root.hidden = false;
    root.innerHTML = `
      <div class="modal__backdrop" data-close-modal></div>
      <div class="modal ${cfg.size ? `modal--${cfg.size}` : ""}" role="dialog" aria-modal="true"
           aria-labelledby="modalTitle">
        <header class="modal__head">
          <div>
            <h2 class="modal__title" id="modalTitle">${U.esc(cfg.title)}</h2>
            ${cfg.subtitle ? `<div class="modal__sub">${U.esc(cfg.subtitle)}</div>` : ""}
          </div>
          <button class="icon-btn" data-close-modal aria-label="Close dialog">
            ${I.get("close", { size: 18 })}
          </button>
        </header>
        <div class="modal__body">${cfg.body || ""}</div>
        ${cfg.footer ? `<footer class="modal__foot">${cfg.footer}</footer>` : ""}
      </div>`;

    activeModal = root.querySelector(".modal");
    document.body.style.overflow = "hidden";

    root.querySelectorAll("[data-close-modal]").forEach((el) =>
      el.addEventListener("click", () => closeModal())
    );

    if (typeof cfg.onMount === "function") cfg.onMount(activeModal);

    // Focus the first meaningful control.
    const focusable = activeModal.querySelector(
      "input:not([type=hidden]), select, textarea, button:not([data-close-modal])"
    );
    (focusable || activeModal.querySelector("[data-close-modal]")).focus();

    activeModal.addEventListener("keydown", trapFocus);
    return activeModal;
  }

  function trapFocus(e) {
    if (e.key !== "Tab" || !activeModal) return;
    const items = Array.from(
      activeModal.querySelectorAll(
        'a[href], button:not([disabled]), input:not([type=hidden]):not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
    ).filter((el) => el.offsetParent !== null);
    if (!items.length) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }

  function closeModal(immediate = false) {
    const root = U.$("#modalRoot");
    if (!root || root.hidden) return;
    const modal = root.querySelector(".modal");
    const finish = () => {
      root.hidden = true;
      root.innerHTML = "";
      activeModal = null;
      document.body.style.overflow = "";
      if (lastFocused && document.contains(lastFocused)) lastFocused.focus();
    };
    if (immediate || U.prefersReducedMotion() || !modal) return finish();
    modal.classList.add("is-closing");
    setTimeout(finish, 130);
  }

  /** Promise-based confirmation dialog used before every destructive action. */
  function confirm({ title, message, confirmLabel = "Delete", tone = "danger" }) {
    return new Promise((resolve) => {
      openModal({
        title,
        size: "sm",
        body: `<p style="color:var(--text-secondary);line-height:1.6">${U.esc(message)}</p>`,
        footer: `
          <button class="btn btn--ghost" data-confirm="no">Cancel</button>
          <button class="btn btn--${tone}" data-confirm="yes">${U.esc(confirmLabel)}</button>`,
        onMount(modal) {
          modal.querySelector('[data-confirm="no"]').addEventListener("click", () => {
            closeModal();
            resolve(false);
          });
          modal.querySelector('[data-confirm="yes"]').addEventListener("click", () => {
            closeModal();
            resolve(true);
          });
        },
      });
    });
  }

  /* ============================================================== forms === */

  /** Collect a form's values into a plain object. */
  function formValues(form) {
    const out = {};
    new FormData(form).forEach((v, k) => {
      out[k] = typeof v === "string" ? v.trim() : v;
    });
    form.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
      out[cb.name] = cb.checked;
    });
    return out;
  }

  /** Paint validation errors returned by AC.validation onto a form. */
  function showErrors(form, errors) {
    form.querySelectorAll("[data-error-for]").forEach((el) => {
      el.textContent = "";
    });
    form.querySelectorAll(".input, .select, .textarea").forEach((el) =>
      el.removeAttribute("aria-invalid")
    );

    const keys = Object.keys(errors);
    keys.forEach((key) => {
      const slot = form.querySelector(`[data-error-for="${key}"]`);
      if (slot) slot.textContent = errors[key];
      const input = form.querySelector(`[name="${key}"]`);
      if (input) input.setAttribute("aria-invalid", "true");
    });

    if (keys.length) {
      const first = form.querySelector(`[name="${keys[0]}"]`);
      if (first) first.focus();
    }
  }

  /* ========================================================== utilities === */

  const toneForStatus = (status) =>
    ({ overdue: "critical", "due-soon": "warning", upcoming: "success", unknown: "muted" }[status] ||
    "muted");

  /** Escape-key handling for modal + palette lives in app.js; exposed here. */
  const isModalOpen = () => Boolean(activeModal);

  return {
    metricCard,
    statusPill,
    progressBar,
    emptyState,
    banner,
    alertRow,
    demoFlag,
    sectionHead,
    field,
    selectField,
    textareaField,
    switchField,
    activate,
    toast,
    openModal,
    closeModal,
    confirm,
    formValues,
    showErrors,
    toneForStatus,
    isModalOpen,
  };
})();
