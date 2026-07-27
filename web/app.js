/**
 * ChickenButt transcript page — presentation only.
 *
 * Streaming (assistant): open a real code card as soon as ``` arrives, then
 * fill it token-by-token (Grok-style). Prose stays plain/fast until fence or done.
 * Final message_done: full Markdown polish via marked.
 */
(function () {
  "use strict";

  const messagesEl = document.getElementById("messages");
  const emptyEl = document.getElementById("empty");
  const nodes = new Map();

  let stickToBottom = true;

  function postIntent(payload) {
    try {
      if (
        window.webkit &&
        window.webkit.messageHandlers &&
        window.webkit.messageHandlers.chickenbutt
      ) {
        window.webkit.messageHandlers.chickenbutt.postMessage(payload);
        return;
      }
    } catch (_) { /* fall through */ }
    try {
      if (window.chickenbutt && typeof window.chickenbutt.postMessage === "function") {
        window.chickenbutt.postMessage(JSON.stringify(payload));
      }
    } catch (_) { /* ignore */ }
  }

  function configureMarked() {
    if (typeof marked === "undefined") return;
    marked.setOptions({ gfm: true, breaks: false });
    marked.use({
      renderer: {
        code(token) {
          let code = "";
          let lang = "code";
          if (token && typeof token === "object") {
            code = token.text != null ? token.text : String(token.raw || "");
            lang = (token.lang || "").trim().split(/\s+/)[0] || "code";
          } else {
            code = String(token == null ? "" : token);
            lang = arguments[1]
              ? String(arguments[1]).trim().split(/\s+/)[0]
              : "code";
            if (!lang) lang = "code";
          }
          return codeBlockHtml(lang, code.replace(/\n$/, ""));
        },
      },
    });
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
  function escapeAttr(s) {
    return escapeHtml(s).replace(/'/g, "&#39;");
  }

  /** Collapsed preview threshold (px). Longer blocks get Expand. */
  const CODE_COLLAPSE_PX = 200;

  /* Adwaita-like 16×16 symbolic SVGs (presentation only; labels via aria/title) */
  const ICONS = {
    copy:
      '<svg class="icon" viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M4 1.5A1.5 1.5 0 0 0 2.5 3v8A1.5 1.5 0 0 0 4 12.5h5A1.5 1.5 0 0 0 10.5 11V3A1.5 1.5 0 0 0 9 1.5H4zm0 1h5a.5.5 0 0 1 .5.5v8a.5.5 0 0 1-.5.5H4a.5.5 0 0 1-.5-.5V3A.5.5 0 0 1 4 2.5zm3 11A1.5 1.5 0 0 0 8.5 15H12A1.5 1.5 0 0 0 13.5 13.5v-7A1.5 1.5 0 0 0 12 5h-.5v1H12a.5.5 0 0 1 .5.5v7a.5.5 0 0 1-.5.5H8.5a.5.5 0 0 1-.5-.5V13H7z"/></svg>',
    edit:
      '<svg class="icon" viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M11.85 1.15a1.5 1.5 0 0 1 2.12 2.12l-.7.7-2.12-2.12.7-.7zm-1.06 1.77 2.12 2.12-7.04 7.04H3.75v-2.12l7.04-7.04zM2.5 12.5h11v1.5h-11v-1.5z"/></svg>',
    // Circular two-arrow sync / repeat — “do this again” (regenerate)
    refresh:
      '<svg class="icon" viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M13.5 8A5.5 5.5 0 0 1 4.3 11.7l-.8.8L2 11l3.5-1 .8 3.4-1.3-1.3A4 4 0 1 0 8 4V2.5A5.5 5.5 0 0 1 13.5 8zM2.5 8A5.5 5.5 0 0 1 11.7 4.3l.8-.8L14 5l-3.5 1-.8-3.4 1.3 1.3A4 4 0 1 0 8 11.5V13A5.5 5.5 0 0 1 2.5 8z"/></svg>',
    play:
      '<svg class="icon" viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M4.5 2.5v11l9-5.5-9-5.5z"/></svg>',
    trash:
      '<svg class="icon" viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M6 1.5h4l.5 1H14v1.5H2V2.5h3.5L6 1.5zM3.5 5h9l-.7 9.1A1.5 1.5 0 0 1 10.3 15.5H5.7a1.5 1.5 0 0 1-1.5-1.4L3.5 5zm2 1.5v7h1.5v-7H5.5zm3.5 0v7H10.5v-7H9z"/></svg>',
    expand:
      '<svg class="icon" viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M3 3h4v1.5H4.5V7H3V3zm6 0h4v4h-1.5V4.5H9V3zM3 9h1.5v2.5H7V13H3V9zm8.5 0H13v4H9v-1.5h2.5V9z"/></svg>',
    collapse:
      '<svg class="icon" viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M6 2H4.5v2.5H2V6h4V2zm6 0H8v4h4V4.5h-2.5V2zM6 10H2v1.5h2.5V14H6v-4zm4 0v4h1.5v-2.5H14V10h-4z"/></svg>',
    more:
      '<svg class="icon" viewBox="0 0 16 16" aria-hidden="true"><circle fill="currentColor" cx="3.5" cy="8" r="1.5"/><circle fill="currentColor" cx="8" cy="8" r="1.5"/><circle fill="currentColor" cx="12.5" cy="8" r="1.5"/></svg>',
    // Checkmark (Adwaita-like object-select / emblem-ok)
    check:
      '<svg class="icon" viewBox="0 0 16 16" aria-hidden="true"><path fill="currentColor" d="M6.5 11.5 3 8l1.2-1.2L6.5 9.1l5.3-5.3L13 5l-6.5 6.5z"/></svg>',
  };

  function iconButton(opts) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "icon-btn" + (opts.destructive ? " icon-btn-destructive" : "");
    if (opts.extraClass) btn.className += " " + opts.extraClass;
    btn.innerHTML = ICONS[opts.icon] || "";
    btn.setAttribute("aria-label", opts.label);
    btn.title = opts.label;
    btn.dataset.action = opts.action || "";
    if (opts.hidden) btn.hidden = true;
    if (opts.attrs) {
      Object.keys(opts.attrs).forEach((k) => btn.setAttribute(k, opts.attrs[k]));
    }
    return btn;
  }

  function codeBlockHtml(lang, code) {
    const escaped = escapeHtml(code);
    // Icon SVGs are injected by wireCodeUi() after this HTML has passed
    // through the sanitizer (see renderMarkdown()) rather than embedded here,
    // since an inline <svg> baked into marked's output wouldn't survive the
    // HTML-only sanitize profile.
    return (
      `<pre data-lang="${escapeAttr(lang)}">` +
      `<div class="code-head"><span class="code-lang">${escapeHtml(lang || "code")}</span>` +
      `<div class="code-head-actions">` +
      `<button type="button" class="icon-btn" data-expand hidden aria-label="Expand code" title="Expand code"></button>` +
      `<button type="button" class="icon-btn" data-copy aria-label="Copy code" title="Copy code"></button>` +
      `</div></div>` +
      `<code class="language-${escapeAttr(lang || "code")}">${escaped}</code></pre>`
    );
  }

  function highlightCodeEl(codeEl, lang) {
    if (!codeEl || typeof hljs === "undefined") return;
    try {
      // Reset previous highlight markup
      const plain = codeEl.textContent;
      codeEl.textContent = plain;
      codeEl.className = "language-" + (lang || "code");
      if (lang && hljs.getLanguage(lang)) {
        const result = hljs.highlight(plain, { language: lang, ignoreIllegals: true });
        codeEl.innerHTML = result.value;
        codeEl.classList.add("hljs");
      } else {
        hljs.highlightElement(codeEl);
      }
    } catch (_) {
      try {
        hljs.highlightElement(codeEl);
      } catch (_) { /* ignore */ }
    }
  }

  function highlightAllIn(root) {
    if (!root || typeof hljs === "undefined") return;
    root.querySelectorAll("pre code").forEach((codeEl) => {
      const pre = codeEl.closest("pre");
      const lang = (pre && pre.dataset.lang) || "";
      highlightCodeEl(codeEl, lang);
    });
  }

  function setHljsTheme(light) {
    const dark = document.getElementById("hljs-theme-dark");
    const lite = document.getElementById("hljs-theme-light");
    if (dark) dark.disabled = !!light;
    if (lite) lite.disabled = !light;
  }

  /**
   * Brand mark for empty/greeting state.
   * Use tight icon SVGs (16x16 viewBox) — full logos are 1920x1080 with tiny art.
   * light-icon = white chick on dark UI; dark-icon = black chick on light UI.
   */
  function syncEmptyBrandIcon() {
    const img = document.getElementById("empty-icon");
    if (!img) return;
    const lightUi = document.body.classList.contains("theme-light");
    img.src = lightUi
      ? "../icons/chickenbutt-dark-icon.svg"
      : "../icons/chickenbutt-light-icon.svg";
  }

  // Single sanitization boundary for model-derived HTML. marked.parse()
  // does not sanitize its output (by its own documentation); every caller
  // of renderMarkdown() relies on this to be the only place raw model text
  // becomes innerHTML. HTML-only profile: no SVG/MathML needed from model
  // output, and it keeps SVG-based script vectors out entirely. Remote
  // content (img/iframe/object/embed/video/audio/source/picture) is
  // forbidden outright for this pass.
  const SANITIZE_CONFIG = {
    USE_PROFILES: { html: true },
    FORBID_TAGS: [
      "img", "iframe", "object", "embed", "video", "audio", "source",
      "picture", "svg", "math", "style", "script",
    ],
    FORBID_ATTR: ["style", "srcdoc"],
  };

  function sanitizeHtml(rawHtml) {
    // DOMPurify.isSupported is how the library itself reports whether the
    // current environment can actually sanitize — on an unsupported browser
    // sanitize() can return the input untouched instead of throwing, so a
    // present-and-non-throwing DOMPurify is not sufficient on its own.
    if (
      typeof DOMPurify === "undefined" ||
      DOMPurify.isSupported !== true
    ) {
      throw new Error("DOMPurify unavailable or unsupported");
    }
    return DOMPurify.sanitize(rawHtml, SANITIZE_CONFIG);
  }

  function renderMarkdown(text) {
    const src = text || "";
    try {
      if (typeof marked === "undefined") throw new Error("marked unavailable");
      return sanitizeHtml(marked.parse(src));
    } catch (_) {
      // Fail closed: never return unsanitized marked output.
      return `<p>${escapeHtml(src).replace(/\n/g, "<br>")}</p>`;
    }
  }

  function nearBottom(el, px) {
    return el.scrollHeight - el.scrollTop - el.clientHeight < (px || 80);
  }

  function scrollIfPinned() {
    if (!stickToBottom) return;
    const root = document.getElementById("root");
    root.scrollTop = root.scrollHeight;
  }

  document.getElementById("root").addEventListener(
    "scroll",
    () => {
      stickToBottom = nearBottom(document.getElementById("root"));
    },
    { passive: true }
  );

  function showMessages() {
    emptyEl.hidden = true;
    messagesEl.hidden = false;
  }

  function showEmpty() {
    emptyEl.hidden = false;
    messagesEl.hidden = true;
    messagesEl.innerHTML = "";
    nodes.clear();
  }

  function setEmptyState(title, sub) {
    const titleEl = emptyEl.querySelector(".empty-title");
    const subEl = emptyEl.querySelector(".empty-sub");
    if (titleEl && title != null) titleEl.textContent = title;
    if (subEl && sub != null) subEl.textContent = sub;
    // Only show empty chrome when there are no messages
    if (!messagesEl.hidden && messagesEl.children.length > 0) return;
    showEmpty();
  }

  function timeNow() {
    try {
      return new Date().toLocaleTimeString([], {
        hour: "numeric",
        minute: "2-digit",
      });
    } catch (_) {
      return "";
    }
  }

  function copyToClipboard(text, btn) {
    const done = () => {
      if (!btn) return;
      // Flash checkmark instead of replacing label text (icons stay icons)
      const prevHtml = btn.innerHTML;
      const prevLabel = btn.getAttribute("aria-label") || "";
      const prevTitle = btn.title || "";
      btn.innerHTML = ICONS.check;
      btn.classList.add("icon-btn-success");
      btn.setAttribute("aria-label", "Copied");
      btn.title = "Copied";
      if (btn._copyResetTimer) clearTimeout(btn._copyResetTimer);
      btn._copyResetTimer = setTimeout(() => {
        btn.innerHTML = prevHtml;
        btn.classList.remove("icon-btn-success");
        if (prevLabel) btn.setAttribute("aria-label", prevLabel);
        btn.title = prevTitle;
        btn._copyResetTimer = null;
      }, 1400);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard
        .writeText(text)
        .then(done)
        .catch(() => {
          postIntent({ type: "copy_text", text: text || "" });
          done();
        });
    } else {
      postIntent({ type: "copy_text", text: text || "" });
      done();
    }
  }

  /**
   * Semantic plain text for Copy — excludes code-card headers (lang / Expand / Copy)
   * and any buttons. Action bars live outside .md-body so they are already omitted.
   */
  function plainTextFromMessage(n) {
    if (!n) return "";
    if (!n.body) return n.raw || "";
    const clone = n.body.cloneNode(true);
    clone.querySelectorAll(".code-head").forEach((el) => el.remove());
    clone.querySelectorAll("button").forEach((el) => el.remove());
    clone.querySelectorAll(".edit-controls").forEach((el) => el.remove());
    clone.querySelectorAll(".edit-area").forEach((el) => el.remove());
    let text = clone.innerText != null ? clone.innerText : clone.textContent || "";
    // Normalize excessive blank lines from block margins
    text = String(text).replace(/[ \t]+\n/g, "\n").replace(/\n{3,}/g, "\n\n");
    return text.replace(/^\n+|\n+$/g, "");
  }

  // Expose for automated tests (file:// / node-less)
  window.chickenbuttPlainTextFromMessage = plainTextFromMessage;

  function setExpandButtonState(btn, collapsed) {
    if (!btn) return;
    btn.innerHTML = collapsed ? ICONS.expand : ICONS.collapse;
    const label = collapsed ? "Expand code" : "Collapse code";
    btn.setAttribute("aria-label", label);
    btn.title = label;
    btn.setAttribute("aria-expanded", collapsed ? "false" : "true");
  }

  function wireCodeCopy(root) {
    root.querySelectorAll("pre [data-copy]").forEach((btn) => {
      if (btn._cbBound) return;
      btn._cbBound = true;
      if (!btn.getAttribute("aria-label")) {
        btn.setAttribute("aria-label", "Copy code");
        btn.title = "Copy code";
      }
      if (!btn.classList.contains("icon-btn")) btn.classList.add("icon-btn");
      if (!btn.querySelector("svg")) btn.innerHTML = ICONS.copy;
      btn.addEventListener("click", () => {
        const pre = btn.closest("pre");
        const code = pre ? pre.querySelector("code") : null;
        copyToClipboard(code ? code.textContent : "", btn);
      });
    });
  }

  function wireCodeExpand(root) {
    root.querySelectorAll("pre").forEach((pre) => {
      const code = pre.querySelector("code");
      if (!code) return;
      let expandBtn = pre.querySelector("[data-expand]");
      if (!expandBtn) {
        const actions =
          pre.querySelector(".code-head-actions") ||
          pre.querySelector(".code-head");
        if (!actions) return;
        expandBtn = iconButton({
          icon: "expand",
          label: "Expand code",
          action: "expand",
          hidden: true,
          attrs: { "data-expand": "" },
        });
        const copyBtn = actions.querySelector("[data-copy]");
        if (copyBtn) actions.insertBefore(expandBtn, copyBtn);
        else actions.appendChild(expandBtn);
      }
      if (!expandBtn.querySelector("svg")) expandBtn.innerHTML = ICONS.expand;
      if (!expandBtn._cbBound) {
        expandBtn._cbBound = true;
        expandBtn.addEventListener("click", () => {
          const collapsed = pre.classList.toggle("is-collapsed");
          setExpandButtonState(expandBtn, collapsed);
          if (collapsed) delete pre.dataset.userExpanded;
          else pre.dataset.userExpanded = "1";
        });
      }
      // Measure natural height (temporarily uncollapse)
      pre.classList.remove("is-collapsed");
      const h = code.scrollHeight;
      if (h > CODE_COLLAPSE_PX) {
        expandBtn.hidden = false;
        if (pre.dataset.userExpanded === "1") {
          setExpandButtonState(expandBtn, false);
        } else {
          pre.classList.add("is-collapsed");
          setExpandButtonState(expandBtn, true);
        }
      } else {
        expandBtn.hidden = true;
        pre.classList.remove("is-collapsed");
      }
    });
  }

  function wireCodeUi(root) {
    wireCodeCopy(root);
    // Measure after layout
    requestAnimationFrame(() => wireCodeExpand(root));
  }

  function makeActionBar(id, role) {
    const bar = document.createElement("div");
    bar.className = "msg-actions" + (role === "user" ? " msg-actions-user" : "");
    bar.dataset.for = id;
    bar.setAttribute("role", "toolbar");
    bar.setAttribute(
      "aria-label",
      role === "user" ? "Message actions" : "Response actions"
    );

    function bind(btn, handler) {
      btn.addEventListener("click", (ev) => {
        ev.preventDefault();
        ev.stopPropagation();
        const n = nodes.get(id);
        if (!n) return;
        handler(n, btn);
      });
      bar.appendChild(btn);
    }

    const copyLabel = role === "user" ? "Copy message" : "Copy response";

    // Primary: Copy
    bind(
      iconButton({ icon: "copy", label: copyLabel, action: "copy_plain" }),
      (n, btn) => copyToClipboard(plainTextFromMessage(n), btn)
    );

    if (role === "user") {
      // Copy · Edit · Regenerate · Delete
      bind(
        iconButton({ icon: "edit", label: "Edit message", action: "edit_message" }),
        () => beginUserEdit(id)
      );
      bind(
        iconButton({
          icon: "refresh",
          label: "Regenerate response",
          action: "regenerate",
        }),
        () => postIntent({ type: "regenerate", id: id })
      );
      bind(
        iconButton({
          icon: "trash",
          label: "Delete message",
          action: "delete_message",
          destructive: true,
        }),
        () => postIntent({ type: "delete_message", id: id })
      );
      return bar;
    }

    // Assistant: Copy · Regenerate · Continue · Delete · More
    bind(
      iconButton({
        icon: "refresh",
        label: "Regenerate response",
        action: "regenerate",
      }),
      () => postIntent({ type: "regenerate", id: id })
    );
    bind(
      iconButton({
        icon: "play",
        label: "Continue generating",
        action: "continue",
      }),
      () => postIntent({ type: "continue", id: id })
    );
    bind(
      iconButton({
        icon: "trash",
        label: "Delete message",
        action: "delete_message",
        destructive: true,
      }),
      () => postIntent({ type: "delete_message", id: id })
    );

    // ⋯ secondary: Copy as Markdown (+ future uncommon actions) — menu below dots
    const moreWrap = document.createElement("div");
    moreWrap.className = "msg-overflow";
    const moreBtn = iconButton({
      icon: "more",
      label: "More actions",
      action: "more",
    });
    // Prefer aria-label only; avoid native title tooltip ghosting over open menu
    moreBtn.removeAttribute("title");
    moreBtn.setAttribute("aria-haspopup", "menu");
    moreBtn.setAttribute("aria-expanded", "false");
    const menu = document.createElement("div");
    menu.className = "msg-overflow-menu";
    menu.setAttribute("role", "menu");
    menu.hidden = true;

    function closeThisMenu() {
      menu.hidden = true;
      moreBtn.setAttribute("aria-expanded", "false");
      bar.classList.remove("is-menu-open");
    }

    function closeAllMenus() {
      document.querySelectorAll(".msg-overflow-menu").forEach((m) => {
        m.hidden = true;
      });
      document.querySelectorAll(".msg-overflow .icon-btn").forEach((b) => {
        b.setAttribute("aria-expanded", "false");
      });
      document.querySelectorAll(".msg-actions.is-menu-open").forEach((el) => {
        el.classList.remove("is-menu-open");
      });
    }

    const mdItem = document.createElement("button");
    mdItem.type = "button";
    mdItem.className = "msg-overflow-item";
    mdItem.setAttribute("role", "menuitem");
    mdItem.textContent = "Copy as Markdown";
    mdItem.addEventListener("click", (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      const n = nodes.get(id);
      closeThisMenu();
      if (!n) return;
      copyToClipboard(n.raw || "", null);
    });
    menu.appendChild(mdItem);

    moreBtn.addEventListener("click", (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      const willOpen = menu.hidden;
      closeAllMenus();
      if (willOpen) {
        menu.hidden = false;
        moreBtn.setAttribute("aria-expanded", "true");
        bar.classList.add("is-menu-open");
      }
    });

    // Outside click / Escape close — avoids ghost menus when pointer leaves
    if (!window._chickenbuttOverflowBound) {
      window._chickenbuttOverflowBound = true;
      document.addEventListener(
        "pointerdown",
        (ev) => {
          const t = ev.target;
          if (t && t.closest && t.closest(".msg-overflow")) return;
          document.querySelectorAll(".msg-overflow-menu").forEach((m) => {
            m.hidden = true;
          });
          document.querySelectorAll(".msg-overflow .icon-btn").forEach((b) => {
            b.setAttribute("aria-expanded", "false");
          });
          document.querySelectorAll(".msg-actions.is-menu-open").forEach((el) => {
            el.classList.remove("is-menu-open");
          });
        },
        true
      );
      document.addEventListener("keydown", (ev) => {
        if (ev.key !== "Escape") return;
        document.querySelectorAll(".msg-overflow-menu").forEach((m) => {
          m.hidden = true;
        });
        document.querySelectorAll(".msg-overflow .icon-btn").forEach((b) => {
          b.setAttribute("aria-expanded", "false");
        });
        document.querySelectorAll(".msg-actions.is-menu-open").forEach((el) => {
          el.classList.remove("is-menu-open");
        });
      });
    }

    moreWrap.appendChild(moreBtn);
    moreWrap.appendChild(menu);
    bar.appendChild(moreWrap);
    return bar;
  }

  function setActionsVisible(id, visible) {
    const n = nodes.get(id);
    if (!n || !n.actions) return;
    n.actions.hidden = !visible;
    if (n.row) n.row.classList.toggle("streaming-row", !visible);
  }

  function beginUserEdit(id) {
    const n = nodes.get(id);
    if (!n || n.role !== "user" || n.editing) return;
    n.editing = true;
    setActionsVisible(id, false);
    const original = n.raw || "";
    n.body.innerHTML = "";
    const ta = document.createElement("textarea");
    ta.className = "edit-area";
    ta.value = original;
    ta.rows = Math.min(12, Math.max(2, original.split("\n").length + 1));
    n.body.appendChild(ta);

    const controls = document.createElement("div");
    controls.className = "edit-controls";
    const save = document.createElement("button");
    save.type = "button";
    save.className = "edit-save";
    save.textContent = "Save & submit";
    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.className = "edit-cancel";
    cancel.textContent = "Cancel";
    controls.appendChild(cancel);
    controls.appendChild(save);
    n.body.appendChild(controls);
    ta.focus();
    ta.setSelectionRange(ta.value.length, ta.value.length);

    const endEdit = (text) => {
      n.editing = false;
      n.raw = text;
      n.body.innerHTML = "";
      n.body.textContent = text;
      setActionsVisible(id, true);
    };

    cancel.addEventListener("click", (ev) => {
      ev.preventDefault();
      endEdit(original);
    });
    save.addEventListener("click", (ev) => {
      ev.preventDefault();
      const next = (ta.value || "").trim();
      if (!next) {
        ta.focus();
        return;
      }
      endEdit(next);
      postIntent({ type: "edit_resend", id: id, text: next });
    });
    ta.addEventListener("keydown", (ev) => {
      if (ev.key === "Escape") {
        ev.preventDefault();
        endEdit(original);
      } else if (ev.key === "Enter" && (ev.metaKey || ev.ctrlKey)) {
        ev.preventDefault();
        save.click();
      }
    });
  }

  /* ---------- structural stream builder (Grok-style code shells) ---------- */

  function createCodeShell(lang) {
    const pre = document.createElement("pre");
    pre.dataset.lang = lang || "code";
    pre.classList.add("streaming-code");

    const head = document.createElement("div");
    head.className = "code-head";

    const langSpan = document.createElement("span");
    langSpan.className = "code-lang";
    langSpan.textContent = lang || "code";

    const actions = document.createElement("div");
    actions.className = "code-head-actions";

    const expandBtn = iconButton({
      icon: "expand",
      label: "Expand code",
      action: "expand",
      hidden: true,
      attrs: { "data-expand": "" },
    });

    const btn = iconButton({
      icon: "copy",
      label: "Copy code",
      action: "copy_code",
      attrs: { "data-copy": "" },
    });

    actions.appendChild(expandBtn);
    actions.appendChild(btn);
    head.appendChild(langSpan);
    head.appendChild(actions);

    const code = document.createElement("code");
    code.className = "language-" + (lang || "code");

    pre.appendChild(head);
    pre.appendChild(code);
    wireCodeCopy(pre);
    return { pre, code, langSpan };
  }

  function ensureStream(n) {
    if (n.stream) return n.stream;
    n.body.innerHTML = "";
    n.stream = {
      mode: "prose", // prose | code
      carry: "",
      proseEl: null,
      code: null, // { pre, code, langSpan }
    };
    return n.stream;
  }

  function ensureProseEl(n) {
    const s = ensureStream(n);
    if (s.proseEl && s.proseEl.isConnected) return s.proseEl;
    const el = document.createElement("div");
    el.className = "stream-prose";
    n.body.appendChild(el);
    s.proseEl = el;
    return el;
  }

  function openCode(n, lang) {
    const s = ensureStream(n);
    s.mode = "code";
    s.proseEl = null; // next prose gets a new div after the code card
    const shell = createCodeShell(lang || "code");
    n.body.appendChild(shell.pre);
    s.code = shell;
    // cursor on code while filling
    n.bubble.classList.add("streaming");
    n.bubble.classList.add("in-code");
  }

  function closeCode(n) {
    const s = ensureStream(n);
    if (s.code && s.code.pre) {
      s.code.pre.classList.remove("streaming-code");
      // IDE-style colors once the fence closes
      const lang = s.code.pre.dataset.lang || "";
      highlightCodeEl(s.code.code, lang);
    }
    s.code = null;
    s.mode = "prose";
    n.bubble.classList.remove("in-code");
  }

  function appendProseText(n, text) {
    if (!text) return;
    const el = ensureProseEl(n);
    el.textContent += text;
  }

  function appendCodeText(n, text) {
    if (!text) return;
    const s = ensureStream(n);
    if (!s.code) openCode(n, "code");
    // Keep plain text while streaming; schedule a soft highlight refresh
    if (s.code.code.dataset.hljs === "1") {
      // strip prior highlight back to plain before append
      const plain = s.code.code.textContent;
      s.code.code.textContent = plain;
      s.code.code.dataset.hljs = "0";
    }
    s.code.code.textContent += text;
    s.code.pre.scrollTop = s.code.pre.scrollHeight;
    scheduleLiveHighlight(n);
  }

  function scheduleLiveHighlight(n) {
    const s = n.stream;
    if (!s || !s.code) return;
    if (s.hlTimer) clearTimeout(s.hlTimer);
    s.hlTimer = setTimeout(() => {
      s.hlTimer = null;
      if (!s.code || !s.code.code) return;
      const lang = s.code.pre.dataset.lang || "";
      highlightCodeEl(s.code.code, lang);
      s.code.code.dataset.hljs = "1";
    }, 120);
  }

  function handleCompleteLine(n, line) {
    // line includes trailing \n when from split
    const s = ensureStream(n);
    const stripped = line.replace(/\r?\n$/, "").trimEnd();
    const trimmed = stripped.trim();

    if (s.mode === "prose") {
      if (trimmed.startsWith("```")) {
        const lang = trimmed.slice(3).trim().split(/\s+/)[0] || "code";
        openCode(n, lang);
        return;
      }
      appendProseText(n, line.endsWith("\n") ? line : line + "\n");
      return;
    }

    // in code
    if (trimmed.startsWith("```")) {
      closeCode(n);
      return;
    }
    appendCodeText(n, line.endsWith("\n") ? line : line + "\n");
  }

  /**
   * Incremental stream: process only the new suffix of full raw text.
   * raw is the full message so far; we keep stream.processedLen.
   */
  function streamUpdate(n, fullText) {
    const s = ensureStream(n);
    n.raw = fullText || "";
    const prev = s.processedLen || 0;
    if (fullText.length < prev) {
      // reset if host rewound (shouldn't happen)
      n.body.innerHTML = "";
      n.stream = null;
      return streamUpdate(n, fullText);
    }
    const chunk = fullText.slice(prev);
    s.processedLen = fullText.length;
    if (!chunk) return;

    s.carry = (s.carry || "") + chunk;

    while (s.carry.indexOf("\n") !== -1) {
      const idx = s.carry.indexOf("\n");
      const line = s.carry.slice(0, idx + 1);
      s.carry = s.carry.slice(idx + 1);
      handleCompleteLine(n, line);
    }

    // Eager flush mid-line
    if (s.carry) {
      if (s.mode === "code") {
        // Hold if could be start of closing fence
        if (!s.carry.startsWith("`")) {
          appendCodeText(n, s.carry);
          s.carry = "";
        }
      } else {
        // Hold if could be start of opening fence
        if (!s.carry.trimStart().startsWith("`")) {
          appendProseText(n, s.carry);
          s.carry = "";
        }
      }
    }
  }

  function finalizeStream(n, fullText) {
    if (fullText != null) n.raw = fullText;
    // Flush carry
    const s = n.stream;
    if (s && s.carry) {
      if (s.mode === "code") {
        if (s.carry.trim().startsWith("```")) {
          s.carry = "";
          closeCode(n);
        } else {
          appendCodeText(n, s.carry);
          s.carry = "";
          closeCode(n);
        }
      } else if (s.carry.trim().startsWith("```")) {
        const lang = s.carry.trim().slice(3).trim().split(/\s+/)[0] || "code";
        s.carry = "";
        openCode(n, lang);
        closeCode(n);
      } else {
        appendProseText(n, s.carry);
        s.carry = "";
      }
    } else if (s && s.mode === "code") {
      closeCode(n);
    }

    // Full Markdown polish (bold, lists, proper structure) + syntax colors
    n.stream = null;
    n.bubble.classList.remove("streaming");
    n.bubble.classList.remove("in-code");
    if (n.row) n.row.classList.remove("streaming-row");
    n.body.innerHTML = renderMarkdown(n.raw || "");
    wireCodeUi(n.body);
    highlightAllIn(n.body);
    setActionsVisible(n.id || idOfNode(n), true);
  }

  function idOfNode(n) {
    if (!n) return "";
    if (n.id) return n.id;
    if (n.row) return n.row.dataset.id || "";
    return "";
  }

  /* ---------- message lifecycle ---------- */

  function addMessage(id, role, text, opts) {
    opts = opts || {};
    showMessages();
    if (nodes.has(id)) {
      updateMessage(id, text, opts);
      return;
    }
    const row = document.createElement("div");
    row.className = `row ${role}`;
    row.dataset.id = id;

    const col = document.createElement("div");
    col.className = "col";

    const bubble = document.createElement("div");
    bubble.className = "bubble" + (role === "assistant" ? " md" : "");
    if (opts.streaming) bubble.classList.add("streaming");
    if (opts.error) bubble.classList.add("error");

    const body = document.createElement("div");
    body.className = "md-body";
    bubble.appendChild(body);

    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = timeNow();

    col.appendChild(bubble);
    // Actions sit directly under the bubble (Grok / ChatGPT style)
    let actions = makeActionBar(id, role);
    col.appendChild(actions);
    col.appendChild(meta);

    row.appendChild(col);
    messagesEl.appendChild(row);

    const n = {
      id,
      row,
      bubble,
      body,
      role,
      raw: text || "",
      stream: null,
      actions,
      editing: false,
    };
    nodes.set(id, n);

    if (role === "user") {
      body.textContent = text || "";
      setActionsVisible(id, true);
    } else if (opts.streaming || opts.streaming === undefined) {
      if (text) streamUpdate(n, text);
      else ensureStream(n);
      bubble.classList.add("streaming");
      row.classList.add("streaming-row");
      setActionsVisible(id, false);
    } else {
      body.innerHTML = renderMarkdown(text || "");
      if (!opts.deferWire) wireCodeUi(body);
      highlightAllIn(body);
      setActionsVisible(id, true);
    }
    if (!opts.deferScroll) scrollIfPinned();
  }

  function updateMessage(id, text, opts) {
    const n = nodes.get(id);
    if (!n) {
      addMessage(id, (opts && opts.role) || "assistant", text, opts);
      return;
    }
    opts = opts || {};
    if (opts.error) n.bubble.classList.add("error");

    if (n.role === "user") {
      n.raw = text || "";
      n.body.textContent = n.raw;
      scrollIfPinned();
      return;
    }

    if (opts.streaming && !opts.finalize) {
      n.bubble.classList.add("streaming");
      if (n.row) n.row.classList.add("streaming-row");
      setActionsVisible(id, false);
      streamUpdate(n, text || "");
    } else {
      finalizeStream(n, text);
    }
    scrollIfPinned();
  }

  function messageDone(id, text) {
    const n = nodes.get(id);
    if (!n) return;
    finalizeStream(n, text != null ? text : n.raw);
    scrollIfPinned();
  }

  function messageReset(id, opts) {
    opts = opts || {};
    let n = nodes.get(id);
    if (!n) {
      addMessage(id, "assistant", "", { streaming: !!opts.streaming });
      n = nodes.get(id);
    }
    if (!n) return;
    n.raw = opts.text || "";
    n.stream = null;
    n.bubble.classList.remove("error");
    n.body.innerHTML = "";
    if (opts.streaming) {
      n.bubble.classList.add("streaming");
      if (n.row) n.row.classList.add("streaming-row");
      setActionsVisible(id, false);
      ensureStream(n);
      if (n.raw) streamUpdate(n, n.raw);
    } else {
      n.bubble.classList.remove("streaming");
      if (n.row) n.row.classList.remove("streaming-row");
      n.body.innerHTML = renderMarkdown(n.raw || "");
      wireCodeUi(n.body);
      highlightAllIn(n.body);
      setActionsVisible(id, true);
    }
    scrollIfPinned();
  }

  function messageRemoved(id) {
    const n = nodes.get(id);
    if (!n) return;
    if (n.row && n.row.parentNode) n.row.parentNode.removeChild(n.row);
    nodes.delete(id);
    if (nodes.size === 0) showEmpty();
  }

  // Host → page
  // message_delta sends *chunks*; we accumulate on n.raw
  window.chickenbuttApply = function (event) {
    if (!event || typeof event !== "object") return;
    switch (event.type) {
      case "conversation_reset":
        showEmpty();
        if (event.messages && event.messages.length) {
          event.messages.forEach((m) => {
            addMessage(m.id, m.role, m.content || m.text || "", {
              streaming: false,
              // Restoring N messages must not force a scroll-height
              // layout read N times — one pinned scroll after the whole
              // batch below is enough and lands in the same place.
              deferScroll: true,
              // Same reasoning for wireCodeUi's own layout reads: wire
              // every restored code block in one pass over the container
              // below instead of once per message.
              deferWire: true,
            });
          });
          wireCodeUi(messagesEl);
        } else if (event.empty_title || event.empty_sub) {
          setEmptyState(
            event.empty_title || "Start a conversation",
            event.empty_sub || ""
          );
        }
        stickToBottom = true;
        scrollIfPinned();
        break;
      case "empty_state":
        setEmptyState(
          event.title || "Start a conversation",
          event.subtitle != null ? event.subtitle : event.sub || ""
        );
        break;
      case "message_added":
        {
          const role = event.role || "assistant";
          const text = event.text || event.content || "";
          const streaming =
            role === "assistant" &&
            event.streaming !== false &&
            !text;
          addMessage(event.id, role, text, {
            streaming: streaming || (role === "assistant" && event.streaming === true),
          });
          if (role === "assistant" && !text) {
            const n = nodes.get(event.id);
            if (n) {
              n.bubble.classList.add("streaming");
              ensureStream(n);
            }
          }
        }
        break;
      case "message_delta":
        {
          const n = nodes.get(event.id);
          if (!n) {
            addMessage(event.id, "assistant", event.text || "", {
              streaming: true,
            });
            break;
          }
          const next = (n.raw || "") + (event.text || "");
          n.bubble.classList.add("streaming");
          streamUpdate(n, next);
          scrollIfPinned();
        }
        break;
      case "message_done":
        messageDone(
          event.id,
          event.text != null ? event.text : undefined
        );
        break;
      case "message_error":
        updateMessage(event.id, event.text || "Error", {
          streaming: false,
          finalize: true,
          error: true,
        });
        setActionsVisible(event.id, true);
        break;
      case "message_reset":
        messageReset(event.id, {
          streaming: event.streaming !== false,
          text: event.text || event.content || "",
        });
        break;
      case "message_removed":
        messageRemoved(event.id);
        break;
      case "theme_changed":
        {
          const light = event.theme === "light";
          document.body.classList.toggle("theme-light", light);
          document.body.classList.toggle("theme-dark", !light);
          setHljsTheme(light);
          syncEmptyBrandIcon();
        }
        break;
      default:
        break;
    }
  };

  window.chickenbuttApplyJson = function (jsonStr) {
    try {
      window.chickenbuttApply(JSON.parse(jsonStr));
    } catch (e) {
      console.error("chickenbuttApplyJson", e);
    }
  };

  configureMarked();
  setHljsTheme(false);
  syncEmptyBrandIcon();
  showEmpty();
  postIntent({ type: "ready" });
})();
