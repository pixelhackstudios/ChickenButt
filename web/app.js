/**
 * ChickenButt transcript page — presentation only.
 *
 * Streaming (assistant): open a real code card as soon as ``` arrives, then
 * fill it token-by-token (Grok-style). Live prose is healed (remend-style
 * unterminated markers) and rendered through marked+DOMPurify per block.
 * Completed blocks stay in the tree; message_done does not replace the bubble.
 * Incoming deltas are paced with an rAF display buffer so Ollama bursts do
 * not splat; the host finishing still drains the remainder quickly.
 * New prose and fenced-code tails fade in.
 */
(function () {
  "use strict";

  const messagesEl = document.getElementById("messages");
  const emptyEl = document.getElementById("empty");
  const nodes = new Map();

  let stickToBottom = true;

  // Display buffer: network/host chunks vs what streamUpdate paints.
  // ~70 cps so the 240ms tail fade is actually visible. Backlog still
  // raises the rate so a fast local model never sits minutes behind.
  // After message_done, drain in FINISH_MS.
  const SMOOTH_CHAR_MS = 14;
  const SMOOTH_BACKLOG_GAIN = 64;
  const SMOOTH_FINISH_MS = 200;
  const STREAM_FADE_MS = 240;

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

  function highlightCodeEl(codeEl, lang, plainSrc) {
    if (!codeEl || typeof hljs === "undefined") return;
    const plain =
      plainSrc != null ? String(plainSrc) : codeEl.textContent || "";
    if (
      codeEl.dataset.hljs === "1" &&
      codeEl.dataset.hljsPlain === String(plain.length)
    ) {
      return;
    }
    try {
      codeEl.textContent = plain;
      codeEl.classList.add("language-" + (lang || "code"));
      if (lang && hljs.getLanguage(lang)) {
        const result = hljs.highlight(plain, { language: lang, ignoreIllegals: true });
        codeEl.innerHTML = result.value;
        codeEl.classList.add("hljs");
      } else {
        hljs.highlightElement(codeEl);
      }
      codeEl.dataset.hljs = "1";
      codeEl.dataset.hljsPlain = String(plain.length);
    } catch (_) {
      try {
        hljs.highlightElement(codeEl);
        codeEl.dataset.hljs = "1";
        codeEl.dataset.hljsPlain = String(plain.length);
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
    nodes.forEach((n) => cancelSmooth(n));
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

  /* ---------- incomplete Markdown (remend-style, prose segments only) ---------- */

  /**
   * Close unterminated inline markers so marked can render a live prose
   * segment. Fenced code is owned by the code-shell path and is not closed
   * here. Incomplete links/images are reduced to visible text rather than a
   * dummy href.
   */
  function healIncompleteMarkdown(text) {
    if (!text) return text;
    let s = String(text);

    s = s.replace(/!\[[^\]]*\]\([^)\n]*$/, "");
    s = s.replace(/!\[[^\]]*$/, "");
    s = s.replace(/\[([^\]]+)\]\([^)\n]*$/, "$1");
    s = s.replace(/\[([^\]]+)$/, "$1");

    if (unbalancedBackticks(s)) s += "`";
    if (countDelim(s, "~~") % 2 === 1) s += "~~";
    if (countDelim(s, "**") % 2 === 1) s += "**";
    if (countDelim(s, "__") % 2 === 1) s += "__";
    if (
      countSingleMarker(s, "*") % 2 === 1 &&
      !singleMarkerIsListBullet(s, "*")
    ) {
      s += "*";
    }
    if (countSingleMarker(s, "_") % 2 === 1 && lastUnderscoreIsEmphasis(s)) {
      s += "_";
    }
    return s;
  }

  function scanNonCode(s, onChar) {
    let i = 0;
    let inInline = false;
    while (i < s.length) {
      if (s[i] === "\\" && i + 1 < s.length) {
        i += 2;
        continue;
      }
      if (s.startsWith("```", i)) {
        const end = s.indexOf("```", i + 3);
        if (end === -1) break;
        i = end + 3;
        continue;
      }
      if (s[i] === "`") {
        inInline = !inInline;
        i += 1;
        continue;
      }
      if (!inInline) {
        const step = onChar(i);
        i += step != null && step > 0 ? step : 1;
      } else {
        i += 1;
      }
    }
  }

  function unbalancedBackticks(s) {
    let n = 0;
    let i = 0;
    while (i < s.length) {
      if (s[i] === "\\" && i + 1 < s.length) {
        i += 2;
        continue;
      }
      if (s.startsWith("```", i)) {
        i += 3;
        continue;
      }
      if (s[i] === "`") n += 1;
      i += 1;
    }
    return n % 2 === 1;
  }

  function countDelim(s, delim) {
    let n = 0;
    const dlen = delim.length;
    scanNonCode(s, (i) => {
      if (s.startsWith(delim, i)) {
        n += 1;
        return dlen;
      }
      return 1;
    });
    return n;
  }

  function countSingleMarker(s, ch) {
    let n = 0;
    const dbl = ch + ch;
    scanNonCode(s, (i) => {
      if (s.startsWith(dbl, i)) return 2;
      if (s[i] === ch) n += 1;
      return 1;
    });
    return n;
  }

  function lastSingleMarkerIndex(s, ch) {
    let last = -1;
    const dbl = ch + ch;
    scanNonCode(s, (i) => {
      if (s.startsWith(dbl, i)) return 2;
      if (s[i] === ch) last = i;
      return 1;
    });
    return last;
  }

  function singleMarkerIsListBullet(s, ch) {
    const idx = lastSingleMarkerIndex(s, ch);
    if (idx < 0) return false;
    const lineStart = s.lastIndexOf("\n", idx - 1) + 1;
    const prefix = s.slice(lineStart, idx);
    if (/[^ \t]/.test(prefix)) return false;
    const after = idx + 1 < s.length ? s[idx + 1] : "";
    return after === "" || after === " " || after === "\t";
  }

  function lastUnderscoreIsEmphasis(s) {
    const idx = lastSingleMarkerIndex(s, "_");
    if (idx < 0) return false;
    const before = idx > 0 ? s[idx - 1] : "\n";
    // snake_case / identifiers: marked does not treat these as italic.
    if (/[A-Za-z0-9_]/.test(before)) return false;
    const after = s.slice(idx + 1);
    return after.search(/\S/) !== -1;
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
    return {
      pre,
      code,
      langSpan,
      plain: "",
      committedLen: 0,
      fades: [],
      prefix: null,
    };
  }

  function ensureStream(n) {
    if (n.stream) return n.stream;
    n.body.innerHTML = "";
    n.stream = {
      mode: "prose", // prose | code
      carry: "",
      proseEl: null,
      proseRaw: "",
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
    s.proseRaw = "";
    s.proseVisibleLen = 0;
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
    if (s.hlRaf) {
      cancelAnimationFrame(s.hlRaf);
      s.hlRaf = 0;
    }
    if (s.code && s.code.pre) {
      s.code.pre.classList.remove("streaming-code");
      paintLiveCode(s, true);
    }
    s.code = null;
    s.mode = "prose";
    n.bubble.classList.remove("in-code");
  }

  function collectProseTextNodes(root, out) {
    const kids = root.childNodes;
    const skipWs =
      root.classList && root.classList.contains("stream-prose");
    for (let i = 0; i < kids.length; i += 1) {
      const node = kids[i];
      if (node.nodeType === 3) {
        if (skipWs && !String(node.nodeValue || "").trim()) continue;
        if (node.nodeValue) out.push(node);
      } else if (node.nodeType === 1 && node.tagName !== "PRE") {
        collectProseTextNodes(node, out);
      }
    }
  }

  function proseVisibleLength(el) {
    const nodes = [];
    collectProseTextNodes(el, nodes);
    let n = 0;
    for (let i = 0; i < nodes.length; i += 1) {
      n += (nodes[i].nodeValue || "").length;
    }
    return n;
  }

  function appendFadeChunk(parent, extra) {
    const parts = String(extra).split(/(\s+)/);
    for (let i = 0; i < parts.length; i += 1) {
      const part = parts[i];
      if (!part) continue;
      if (/^\s+$/.test(part)) {
        parent.appendChild(document.createTextNode(part));
        continue;
      }
      const span = document.createElement("span");
      span.className = "stream-fade";
      span.textContent = part;
      parent.appendChild(span);
    }
  }

  function tryPatchProseTail(el, html) {
    if (!el || !el.lastElementChild) return false;
    const tmp = document.createElement("div");
    tmp.innerHTML = html;
    if (tmp.childElementCount !== el.childElementCount) return false;
    const oldLast = el.lastElementChild;
    const newLast = tmp.lastElementChild;
    if (!oldLast || !newLast) return false;
    if (oldLast.tagName !== newLast.tagName) return false;
    if (oldLast.tagName === "PRE") return false;
    const oldText = oldLast.textContent || "";
    const newText = newLast.textContent || "";
    if (newText === oldText) return true;
    if (!newText.startsWith(oldText)) return false;
    const extra = newText.slice(oldText.length);
    if (extra) appendFadeChunk(oldLast, extra);
    return true;
  }

  function wrapNewProseTail(el, skipChars) {
    if (!el || skipChars < 0) return;
    const nodes = [];
    collectProseTextNodes(el, nodes);
    let seen = 0;
    for (let i = 0; i < nodes.length; i += 1) {
      const node = nodes[i];
      const t = node.nodeValue || "";
      const nextSeen = seen + t.length;
      if (nextSeen <= skipChars) {
        seen = nextSeen;
        continue;
      }
      const cut = Math.max(0, skipChars - seen);
      const fresh = t.slice(cut);
      seen = nextSeen;
      if (!fresh || !/\S/.test(fresh)) continue;
      const parent = node.parentNode;
      if (!parent) continue;
      const span = document.createElement("span");
      span.className = "stream-fade";
      span.textContent = fresh;
      if (cut > 0) {
        node.nodeValue = t.slice(0, cut);
        parent.insertBefore(span, node.nextSibling);
      } else {
        parent.replaceChild(span, node);
      }
    }
  }

  function appendProseText(n, text) {
    if (!text) return;
    const s = ensureStream(n);
    const el = ensureProseEl(n);
    s.proseRaw = (s.proseRaw || "") + text;
    const html = renderMarkdown(healIncompleteMarkdown(s.proseRaw));
    const skip = s.proseVisibleLen || 0;
    let patched = false;
    try {
      patched = tryPatchProseTail(el, html);
    } catch (_) {
      patched = false;
    }
    if (!patched) {
      el.innerHTML = html;
      try {
        const vis = proseVisibleLength(el);
        if (vis > skip) wrapNewProseTail(el, skip);
        else if (vis < skip) wrapNewProseTail(el, 0);
      } catch (_) { /* fade is cosmetic */ }
    }
    s.proseVisibleLen = proseVisibleLength(el);
  }

  function flushCarryFinished(n) {
    const s = n.stream;
    if (!s) return;
    if (s.carry) {
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
    } else if (s.mode === "code") {
      closeCode(n);
    }
  }

  function appendCodeText(n, text) {
    if (!text) return;
    const s = ensureStream(n);
    if (!s.code) openCode(n, "code");
    s.code.plain = (s.code.plain || "") + text;
    const span = document.createElement("span");
    span.className = "stream-fade";
    span.textContent = text;
    s.code.code.appendChild(span);
    if (!s.code.fades) s.code.fades = [];
    s.code.fades.push({
      el: span,
      at: performance.now ? performance.now() : Date.now(),
      len: text.length,
    });
    s.code.pre.scrollTop = s.code.pre.scrollHeight;
    scheduleLiveHighlight(n);
  }

  function ensureCodePrefix(shell) {
    if (shell.prefix && shell.prefix.isConnected) return shell.prefix;
    const prefix = document.createElement("span");
    prefix.className = "cb-code-prefix";
    shell.code.insertBefore(prefix, shell.code.firstChild);
    shell.prefix = prefix;
    return prefix;
  }

  function paintLiveCode(s, flatten) {
    if (!s || !s.code || !s.code.code) return;
    const shell = s.code;
    const lang = shell.pre.dataset.lang || "";
    const plain = shell.plain || "";
    if (flatten) {
      shell.fades = [];
      shell.committedLen = plain.length;
      shell.prefix = null;
      highlightCodeEl(shell.code, lang, plain);
      return;
    }
    const now = performance.now ? performance.now() : Date.now();
    const fades = shell.fades || [];
    while (fades.length && now - fades[0].at >= STREAM_FADE_MS) {
      const done = fades.shift();
      shell.committedLen = (shell.committedLen || 0) + done.len;
      if (done.el && done.el.parentNode) done.el.parentNode.removeChild(done.el);
    }
    const committed = Math.min(shell.committedLen || 0, plain.length);
    shell.committedLen = committed;
    if (committed > 0) {
      const prefix = ensureCodePrefix(shell);
      highlightCodeEl(prefix, lang, plain.slice(0, committed));
      shell.code.classList.add("hljs");
      shell.code.dataset.hljs = "1";
    }
  }

  function scheduleLiveHighlight(n) {
    const s = n.stream;
    if (!s || !s.code) return;
    if (s.hlRaf) return;
    s.hlRaf = requestAnimationFrame(() => {
      s.hlRaf = 0;
      paintLiveCode(s);
    });
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

  function utf16Take(s, charCount) {
    let i = 0;
    let n = 0;
    while (i < s.length && n < charCount) {
      const c = s.charCodeAt(i);
      i += c >= 0xd800 && c <= 0xdbff && i + 1 < s.length ? 2 : 1;
      n += 1;
    }
    return i;
  }

  function ensureSmooth(n) {
    if (n.smooth) return n.smooth;
    n.smooth = {
      pending: "",
      displayed: n.raw || "",
      raf: 0,
      lastTs: 0,
      finishing: false,
      finishText: null,
      finishThinking: undefined,
    };
    return n.smooth;
  }

  function cancelSmooth(n) {
    if (!n || !n.smooth) return;
    if (n.smooth.raf) {
      cancelAnimationFrame(n.smooth.raf);
      n.smooth.raf = 0;
    }
    n.smooth = null;
  }

  function kickSmooth(n) {
    const s = n.smooth;
    if (!s || s.raf) return;
    const tick = (ts) => {
      if (!n.smooth) return;
      n.smooth.raf = 0;
      pumpSmooth(n, ts);
      if (n.smooth && (n.smooth.pending || n.smooth.finishing)) {
        n.smooth.raf = requestAnimationFrame(tick);
      }
    };
    s.raf = requestAnimationFrame(tick);
  }

  function pumpSmooth(n, ts) {
    const s = n.smooth;
    if (!s) return;
    if (!s.pending) {
      if (s.finishing) completeSmooth(n);
      return;
    }
    let dt;
    if (!s.lastTs) {
      // First tick: pretend one frame so we do not stall at 1 code unit.
      dt = 16;
      s.lastTs = ts;
    } else {
      dt = Math.min(50, Math.max(0, ts - s.lastTs));
      s.lastTs = ts;
    }
    let takeChars = Math.max(
      1,
      Math.round((dt / SMOOTH_CHAR_MS) * (1 + s.pending.length / SMOOTH_BACKLOG_GAIN))
    );
    if (s.finishing) {
      takeChars = Math.max(
        takeChars,
        Math.ceil((s.pending.length * dt) / SMOOTH_FINISH_MS)
      );
    }
    const take = utf16Take(s.pending, takeChars);
    if (take <= 0) return;
    s.displayed += s.pending.slice(0, take);
    s.pending = s.pending.slice(take);
    streamUpdate(n, s.displayed);
    scrollIfPinned();
    if (s.finishing && !s.pending) completeSmooth(n);
  }

  function enqueueSmoothDelta(n, chunk) {
    if (!n || !chunk) return;
    const s = ensureSmooth(n);
    s.pending += chunk;
    if (!s.displayed) {
      pumpSmooth(n, performance.now ? performance.now() : 0);
    }
    kickSmooth(n);
  }

  function beginSmoothFinish(n, text, thinking) {
    if (!n) return;
    const s = ensureSmooth(n);
    const have = s.displayed + s.pending;
    const next = text != null ? text : have;
    if (next !== have) {
      if (s.displayed && next.startsWith(s.displayed)) {
        s.pending = next.slice(s.displayed.length);
      } else {
        cancelSmooth(n);
        finalizeStream(n, next, thinking);
        scrollIfPinned();
        return;
      }
    }
    s.finishing = true;
    s.finishText = next;
    s.finishThinking = thinking;
    if (!s.pending) {
      completeSmooth(n);
      return;
    }
    s.lastTs = 0;
    kickSmooth(n);
  }

  function completeSmooth(n) {
    const s = n.smooth;
    if (!s) {
      return;
    }
    const text = s.finishText != null ? s.finishText : s.displayed + s.pending;
    const thinking = s.finishThinking;
    if (s.pending) {
      s.displayed += s.pending;
      s.pending = "";
      streamUpdate(n, s.displayed);
    }
    cancelSmooth(n);
    finalizeStream(n, text, thinking);
    scrollIfPinned();
  }

  function finalizeStream(n, fullText, thinkingText) {
    if (thinkingText != null) n.reasoning = thinkingText;
    const prev = n.raw || "";
    const next = fullText != null ? fullText : prev;

    // Keep the live block tree. Only rebuild when the host canonical text
    // is not an extension of what we already painted (empty → placeholder,
    // error rewrite). Replay still goes through the streaming painter so
    // we never snap from plain text to Markdown.
    if (next !== prev) {
      if (next.startsWith(prev)) {
        streamUpdate(n, next);
      } else {
        n.body.innerHTML = "";
        n.stream = null;
        n.raw = "";
        streamUpdate(n, next);
      }
    }
    n.raw = next;
    flushCarryFinished(n);

    n.stream = null;
    n.bubble.classList.remove("streaming");
    n.bubble.classList.remove("in-code");
    if (n.row) n.row.classList.remove("streaming-row");
    if (n.reasoning) setReasoning(n, n.reasoning, { streaming: false });
    else setReasoning(n, "");
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

  /* ---------- reasoning (sibling of answer content) ---------- */

  function ensureReasoningEl(n, streaming) {
    if (!n || n.role === "user") return null;
    if (n.reasoningDetails) {
      if (n.reasoningSummary) {
        n.reasoningSummary.textContent = streaming ? "Thinking…" : "Reasoning";
      }
      if (streaming) n.reasoningDetails.open = true;
      return n.reasoningDetails;
    }
    const details = document.createElement("details");
    details.className = "reasoning";
    if (streaming) details.open = true;
    const summary = document.createElement("summary");
    summary.className = "reasoning-summary";
    summary.textContent = streaming ? "Thinking…" : "Reasoning";
    const pre = document.createElement("pre");
    pre.className = "reasoning-body";
    details.appendChild(summary);
    details.appendChild(pre);
    // Above answer body inside the bubble
    n.bubble.insertBefore(details, n.body);
    n.reasoningDetails = details;
    n.reasoningSummary = summary;
    n.reasoningBody = pre;
    n.reasoning = n.reasoning || "";
    return details;
  }

  function setReasoning(n, text, opts) {
    opts = opts || {};
    if (!n || n.role === "user") return;
    const raw = text || "";
    n.reasoning = raw;
    if (!raw) {
      if (n.reasoningDetails && n.reasoningDetails.parentNode) {
        n.reasoningDetails.parentNode.removeChild(n.reasoningDetails);
      }
      n.reasoningDetails = null;
      n.reasoningSummary = null;
      n.reasoningBody = null;
      return;
    }
    ensureReasoningEl(n, !!opts.streaming);
    if (n.reasoningBody) n.reasoningBody.textContent = raw;
    if (n.reasoningSummary) {
      n.reasoningSummary.textContent = opts.streaming ? "Thinking…" : "Reasoning";
    }
    if (n.reasoningDetails) {
      if (opts.streaming) n.reasoningDetails.open = true;
      else if (opts.collapse !== false) n.reasoningDetails.open = false;
    }
  }

  function appendReasoning(n, chunk) {
    if (!n || !chunk) return;
    n.reasoning = (n.reasoning || "") + chunk;
    ensureReasoningEl(n, true);
    if (n.reasoningBody) n.reasoningBody.textContent = n.reasoning;
    if (n.reasoningSummary) n.reasoningSummary.textContent = "Thinking…";
    if (n.reasoningDetails) n.reasoningDetails.open = true;
  }

  function collapseReasoning(n) {
    if (!n || !n.reasoningDetails) return;
    if (n.reasoningSummary) n.reasoningSummary.textContent = "Reasoning";
    n.reasoningDetails.open = false;
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
      reasoning: opts.thinking || "",
      stream: null,
      actions,
      editing: false,
      reasoningDetails: null,
      reasoningSummary: null,
      reasoningBody: null,
    };
    nodes.set(id, n);

    if (role === "user") {
      body.textContent = text || "";
      setActionsVisible(id, true);
    } else if (opts.streaming || opts.streaming === undefined) {
      if (n.reasoning) setReasoning(n, n.reasoning, { streaming: true, collapse: false });
      if (text) streamUpdate(n, text);
      else ensureStream(n);
      bubble.classList.add("streaming");
      row.classList.add("streaming-row");
      setActionsVisible(id, false);
    } else {
      if (n.reasoning) setReasoning(n, n.reasoning, { streaming: false });
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
      cancelSmooth(n);
      n.bubble.classList.add("streaming");
      if (n.row) n.row.classList.add("streaming-row");
      setActionsVisible(id, false);
      streamUpdate(n, text || "");
      ensureSmooth(n).displayed = n.raw || "";
    } else {
      cancelSmooth(n);
      finalizeStream(n, text);
    }
    scrollIfPinned();
  }

  function messageDone(id, text, thinking) {
    const n = nodes.get(id);
    if (!n) return;
    beginSmoothFinish(
      n,
      text != null ? text : n.smooth ? n.smooth.displayed + n.smooth.pending : n.raw,
      thinking != null ? thinking : n.reasoning
    );
  }

  function messageReset(id, opts) {
    opts = opts || {};
    let n = nodes.get(id);
    if (!n) {
      addMessage(id, "assistant", "", { streaming: !!opts.streaming });
      n = nodes.get(id);
    }
    if (!n) return;
    cancelSmooth(n);
    n.raw = opts.text || "";
    n.stream = null;
    n.bubble.classList.remove("error");
    n.body.innerHTML = "";
    if (opts.clear_thinking) {
      setReasoning(n, "");
    } else if (opts.thinking != null) {
      setReasoning(n, opts.thinking || "", {
        streaming: !!opts.streaming && !(opts.text || ""),
        collapse: !opts.streaming,
      });
    }
    if (opts.streaming) {
      n.bubble.classList.add("streaming");
      if (n.row) n.row.classList.add("streaming-row");
      setActionsVisible(id, false);
      ensureStream(n);
      if (n.raw) {
        collapseReasoning(n);
        streamUpdate(n, n.raw);
      }
      ensureSmooth(n).displayed = n.raw || "";
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
    cancelSmooth(n);
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
              thinking: m.thinking || "",
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
          let n = nodes.get(event.id);
          if (!n) {
            addMessage(event.id, "assistant", "", { streaming: true });
            n = nodes.get(event.id);
          }
          if (!n) break;
          n.bubble.classList.add("streaming");
          if (n.reasoning) collapseReasoning(n);
          enqueueSmoothDelta(n, event.text || "");
        }
        break;
      case "reasoning_delta":
        {
          let n = nodes.get(event.id);
          if (!n) {
            addMessage(event.id, "assistant", "", { streaming: true });
            n = nodes.get(event.id);
          }
          if (!n) break;
          n.bubble.classList.add("streaming");
          if (n.row) n.row.classList.add("streaming-row");
          appendReasoning(n, event.text || "");
          scrollIfPinned();
        }
        break;
      case "message_done":
        messageDone(
          event.id,
          event.text != null ? event.text : undefined,
          event.thinking != null ? event.thinking : undefined
        );
        break;
      case "message_error":
        {
          const n = nodes.get(event.id);
          if (n && event.thinking != null) {
            setReasoning(n, event.thinking || "", { streaming: false });
          }
          updateMessage(event.id, event.text || "Error", {
            streaming: false,
            finalize: true,
            error: true,
          });
          setActionsVisible(event.id, true);
        }
        break;
      case "message_reset":
        messageReset(event.id, {
          streaming: event.streaming !== false,
          text: event.text || event.content || "",
          thinking: event.thinking,
          clear_thinking: !!event.clear_thinking,
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
