"""Composer-local Ollama CLI commands (pull/list/ps) — never sent to the LLM."""

from __future__ import annotations

import re
import threading
from collections.abc import Callable

import gi

gi.require_version("GLib", "2.0")

from gi.repository import GLib

from ollama_client import OllamaClient, OllamaError

_RE_OLLAMA_PULL = re.compile(
    r"^ollama\s+pull\s+([A-Za-z0-9][A-Za-z0-9._:/-]*)\s*$",
    re.IGNORECASE,
)
_RE_OLLAMA_LIST = re.compile(r"^ollama\s+list\s*$", re.IGNORECASE)
_RE_OLLAMA_PS = re.compile(r"^ollama\s+ps\s*$", re.IGNORECASE)


class ComposerCliController:
    """Own `_ollama_cli_busy` and composer command execution."""

    def __init__(
        self,
        *,
        client: OllamaClient,
        post_status: Callable[..., None],
        update_status: Callable[..., None],
        next_msg_id: Callable[[str], str],
        get_current_model: Callable[[], str | None],
        set_status: Callable[[str], None],
        on_cli_busy_changed: Callable[[bool], None],
        on_pull_succeeded: Callable[[], None],
        format_bytes: Callable[[float | int], str],
    ) -> None:
        self.client = client
        self._post_status = post_status
        self._update_status = update_status
        self._next_msg_id = next_msg_id
        self._get_current_model = get_current_model
        self._set_status = set_status
        self._on_cli_busy_changed = on_cli_busy_changed
        self._on_pull_succeeded = on_pull_succeeded
        self._format_bytes = format_bytes
        self._ollama_cli_busy = False

    def rebind_next_msg_id(self, provider: Callable[[str], str]) -> None:
        """Rebind message-ID allocation when Phase 22 owns the projection."""
        self._next_msg_id = provider

    def is_busy(self) -> bool:
        return bool(self._ollama_cli_busy)

    def set_busy(self, busy: bool) -> None:
        """Own the busy flag and report send-button-only sensitivity via callback."""
        self._ollama_cli_busy = busy
        self._on_cli_busy_changed(busy)

    def post_status_message(self, text: str, *, streaming: bool = False) -> str:
        """Show a non-persisted assistant-style note in the transcript."""
        mid = self._next_msg_id("asst")
        self._post_status(mid, text, streaming=streaming)
        return mid

    def update_status_message(
        self, mid: str, text: str, *, done: bool = False
    ) -> None:
        """Push progressive status text into a non-chat transcript bubble."""
        self._update_status(mid, text, done=done)

    def format_pull_progress(self, chunk: dict) -> str:
        """Human line from a /api/pull NDJSON object (no ANSI)."""
        status = chunk.get("status")
        status_s = str(status).replace("_", " ") if status else "Working"
        completed = chunk.get("completed")
        total = chunk.get("total")
        digest = chunk.get("digest") or chunk.get("layer")
        parts = [status_s]
        if (
            isinstance(completed, (int, float))
            and isinstance(total, (int, float))
            and total > 0
        ):
            pct = 100.0 * float(completed) / float(total)
            parts.append(
                f"{self._format_bytes(completed)} / {self._format_bytes(total)} "
                f"({pct:.0f}%)"
            )
        elif isinstance(digest, str) and digest:
            short = digest if len(digest) <= 20 else digest[:12] + "…"
            parts.append(short)
        return " · ".join(parts)

    def try_command(self, text: str) -> bool:
        """Handle ollama commands typed in the composer (HTTP API — not LLM)."""
        raw = (text or "").strip()
        if not raw.lower().startswith("ollama"):
            return False

        pull = _RE_OLLAMA_PULL.match(raw)
        if pull:
            self.run_pull(pull.group(1))
            return True
        if _RE_OLLAMA_LIST.match(raw):
            self.run_info("list")
            return True
        if _RE_OLLAMA_PS.match(raw):
            self.run_info("ps")
            return True

        self.post_status_message(
            "Composer command not recognized.\n\n"
            "Supported:\n"
            "- `ollama pull <model-name>`\n"
            "- `ollama list`\n"
            "- `ollama ps`\n\n"
            "Example: `ollama pull llama3.2`"
        )
        return True

    def run_pull(self, model: str) -> None:
        """Pull via POST /api/pull stream — clean JSON progress, no CLI ANSI."""
        if self.is_busy():
            self.post_status_message(
                "An Ollama command is already running. Wait for it to finish."
            )
            return
        self.set_busy(True)
        mid = self.post_status_message(
            f"**Pulling** `{model}`…\n\n_starting_", streaming=True
        )
        self._set_status(f"Pulling {model}…")

        def work() -> None:
            lines: list[str] = []
            last_ui = ""
            ok = False
            err_msg: str | None = None
            try:
                for chunk in self.client.pull_model(model):
                    line = self.format_pull_progress(chunk)
                    status = (chunk.get("status") or "").lower()
                    # Keep a short rolling log of distinct status lines
                    if line and (not lines or lines[-1] != line):
                        # Replace last download line when only % changes on same phase
                        if (
                            lines
                            and " / " in lines[-1]
                            and " / " in line
                            and lines[-1].split(" · ")[0] == line.split(" · ")[0]
                        ):
                            lines[-1] = line
                        else:
                            lines.append(line)
                            # Cap history so the bubble stays readable
                            if len(lines) > 12:
                                lines = lines[-12:]
                    body = (
                        f"**Pulling** `{model}`…\n\n"
                        + "\n".join(f"- {x}" for x in lines)
                    )
                    if body != last_ui:
                        last_ui = body
                        GLib.idle_add(
                            lambda b=body: (
                                self.update_status_message(mid, b, done=False)
                                or False
                            )
                        )
                    if status == "success":
                        ok = True
                if not ok and not err_msg:
                    # Stream ended without explicit success — treat as ok if no error raised
                    ok = True
            except OllamaError as exc:
                err_msg = str(exc)
                ok = False
            except Exception as exc:  # noqa: BLE001
                err_msg = str(exc)
                ok = False

            if ok:
                final = (
                    f"**Pull complete:** `{model}`\n\n"
                    + ("\n".join(f"- {x}" for x in lines) if lines else "_Done._")
                    + "\n\n_Refreshing model list…_"
                )
            else:
                final = (
                    f"**Pull failed:** `{model}`\n\n"
                    + (f"{err_msg}\n\n" if err_msg else "")
                    + ("\n".join(f"- {x}" for x in lines) if lines else "")
                )

            def done() -> bool:
                self.update_status_message(mid, final, done=True)
                self.set_busy(False)
                if ok:
                    self._on_pull_succeeded()
                else:
                    self._set_status(self._get_current_model() or "Ready")
                return False

            GLib.idle_add(done)

        threading.Thread(target=work, daemon=True).start()

    def run_info(self, kind: str) -> None:
        """ollama list / ps via HTTP (/api/tags, /api/ps) — structured text."""
        if self.is_busy():
            self.post_status_message(
                "An Ollama command is already running. Wait for it to finish."
            )
            return
        label = f"ollama {kind}"
        self.set_busy(True)
        mid = self.post_status_message(f"Running `{label}`…", streaming=True)
        self._set_status(f"Running {label}…")

        def work() -> None:
            try:
                if kind == "list":
                    body = (
                        f"**Installed models** (`ollama list`)\n\n"
                        f"{self.client.format_list_models()}"
                    )
                else:
                    body = (
                        f"**Loaded models** (`ollama ps`)\n\n"
                        f"{self.client.format_ps_models()}"
                    )
                ok = True
            except OllamaError as exc:
                body = f"**`{label}` failed:** {exc}"
                ok = False
            except Exception as exc:  # noqa: BLE001
                body = f"**`{label}` failed:** {exc}"
                ok = False

            def done() -> bool:
                self.update_status_message(mid, body, done=True)
                self.set_busy(False)
                self._set_status(self._get_current_model() or "Ready")
                return False

            GLib.idle_add(done)

        threading.Thread(target=work, daemon=True).start()
