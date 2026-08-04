"""Assistant streaming send/start/stop/invalidate (group M)."""

from __future__ import annotations

import threading
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GLib, Gtk

from conversation_lifecycle import ConversationLifecycleController
from conversation_store import ConversationStore
from message_actions import MessageActionController
from model_profile import RequestParams
from ollama_client import OllamaClient, OllamaError
from ollama_health import HealthState, classify_error
from transcript_adapter import TranscriptAdapter


def join_continue(seed: str, piece: str) -> str:
    """Append continuation with a single blank-line Markdown boundary.

    Avoids fused text like ``🌐Here's`` and does not stack extra blank lines
    when the seed already ends with newlines.
    """
    seed = (seed or "").rstrip("\r\n")
    piece = (piece or "").lstrip("\r\n")
    if not seed:
        return piece
    if not piece:
        return seed
    return seed + "\n\n" + piece


def continue_seed_for_stream(seed: str) -> str:
    """Seed text for the transcript when starting a continue stream."""
    seed = (seed or "").rstrip("\r\n")
    if not seed:
        return ""
    return seed + "\n\n"


class StreamingEngineController:
    """Own streaming state and send/start/stop/invalidate/commit helpers."""

    def __init__(
        self,
        *,
        client: OllamaClient,
        get_store: Callable[[], ConversationStore],
        conversation: ConversationLifecycleController,
        message_actions: MessageActionController,
        transcript: TranscriptAdapter,
        get_current_model: Callable[[], str | None],
        is_loading_model: Callable[[], bool],
        get_health: Callable[[], HealthState | None],
        refresh_models: Callable[[], bool],
        apply_health: Callable[[HealthState], None],
        set_status: Callable[[str], None],
        sync_composer_hint: Callable[[], None],
        is_cli_busy: Callable[[], bool],
        try_command: Callable[[str], bool],
        input_widget: Gtk.TextView | None,
        send_control: Gtk.Button | None,
        stop_control: Gtk.Button | None,
        get_request_params: Callable[[str], RequestParams] | None = None,
        on_generation_done: Callable[[str, dict], None] | None = None,
    ) -> None:
        self.client = client
        self._get_store = get_store
        self._conversation = conversation
        self._message_actions = message_actions
        self._transcript = transcript
        self._get_current_model = get_current_model
        self._is_loading_model = is_loading_model
        self._get_health = get_health
        self._refresh_models = refresh_models
        self._apply_health = apply_health
        self._set_status = set_status
        self._sync_composer_hint = sync_composer_hint
        self._is_cli_busy = is_cli_busy
        self._try_command = try_command
        self.input = input_widget
        self.send_btn = send_control
        self.stop_btn = stop_control
        self._get_request_params = get_request_params
        self._on_generation_done = on_generation_done

        self._streaming = False
        self._stream_generation = 0
        self._active_stream_cancel: threading.Event | None = None

    def is_streaming(self) -> bool:
        return self._streaming

    def request_stop(self) -> None:
        """Manual Stop: cancel the current stream, keep its partial output."""
        if self._active_stream_cancel is not None:
            self._active_stream_cancel.set()

    def invalidate_active_stream(self) -> None:
        """Cancel the in-flight generation and mark it stale.

        Used when the active conversation changes out from under a running
        stream (switch / new chat / delete). Unlike manual Stop, this bumps
        the stream generation so the worker's pending UI and persistence
        callbacks see themselves as superseded and discard their output,
        even if the worker hasn't noticed the cancellation yet.
        """
        if self._active_stream_cancel is not None:
            self._active_stream_cancel.set()
        self._stream_generation += 1
        if self._streaming:
            try:
                self.stream_finished()
            except Exception:  # noqa: BLE001
                pass

    def send(self) -> None:
        if self._streaming or self._is_loading_model():
            return
        if self._is_cli_busy():
            return
        if self.input is None:
            return
        buf = self.input.get_buffer()
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False).strip()
        if not text:
            return

        # Local ollama CLI commands (e.g. ollama pull llama3.2) — never chat to the model
        if self._try_command(text):
            buf.set_text("", -1)
            return

        health = self._get_health()
        if health is not None and not health.can_chat:
            # Re-probe — user may have fixed Ollama since the banner appeared
            self._refresh_models()
            return
        if not self._get_current_model():
            return
        buf.set_text("", -1)
        uid = self._conversation.next_msg_id("user")
        if self._transcript.is_webkit:
            self._transcript.post(
                {
                    "type": "message_added",
                    "id": uid,
                    "role": "user",
                    "text": text,
                    "streaming": False,
                }
            )
        else:
            self._transcript.append_native_row(
                "user", text, message_id=uid
            )
        self._conversation.append_local(
            {"id": uid, "role": "user", "content": text}
        )
        self._conversation.persist_message("user", text, message_id=uid)
        self._sync_composer_hint()
        self.start_assistant_stream(mode="new")

    def start_assistant_stream(
        self,
        *,
        mode: str = "new",
        assistant_id: str | None = None,
        seed_text: str = "",
        api_messages: list[dict[str, str]] | None = None,
    ) -> None:
        """mode: new | replace | continue."""
        if self._streaming:
            return
        self._stream_generation += 1
        my_generation = self._stream_generation
        cancel_event = threading.Event()
        self._active_stream_cancel = cancel_event
        origin_conversation_id = self._conversation.conversation_id
        origin_model = self._get_current_model() or ""
        self._streaming = True
        if self.send_btn is not None:
            self.send_btn.set_sensitive(False)
            self.send_btn.set_visible(False)
        if self.stop_btn is not None:
            self.stop_btn.set_visible(True)
            self.stop_btn.set_sensitive(True)
        self._set_status("Thinking…")

        if mode in ("replace", "continue") and assistant_id:
            aid = assistant_id
        else:
            aid = self._conversation.next_msg_id("asst")
        # Continue: transcript seed ends with a blank-line boundary so new tokens
        # never fuse to the previous last character (e.g. "🌐Here's").
        stream_seed = (
            continue_seed_for_stream(seed_text) if mode == "continue" else seed_text
        )
        handle = self._transcript.begin_stream(
            mode=mode,
            message_id=aid,
            stream_seed=stream_seed,
        )

        pending: list[str] = []
        collected: list[str] = []
        state = {
            "streaming": True,
            "error": None,
            "ui_done": False,
            "lock": threading.Lock(),
        }
        outbound = (
            api_messages
            if api_messages is not None
            else self._message_actions.api_messages()
        )

        def still_current() -> bool:
            if my_generation != self._stream_generation:
                return False
            return self._transcript.is_current_stream(handle)

        def finalize_ui() -> None:
            if state["ui_done"] or not still_current():
                return
            state["ui_done"] = True
            err = state["error"]
            piece = "".join(collected)
            if mode == "continue":
                final = join_continue(seed_text, piece)
            else:
                final = piece

            if err is not None:
                # Keep partial transcript; surface plain-language recovery
                self._apply_health(
                    classify_error(
                        err,
                        context="stream",
                        model=origin_model,
                    )
                )
                self._transcript.stream_error(
                    handle, error=str(err), final=final
                )
            else:
                self._transcript.finalize_stream(handle, final=final)

            self.commit_assistant_result(
                aid,
                final,
                mode=mode,
                origin_conversation_id=origin_conversation_id or "",
                allow_empty=bool(err),
            )
            # Refresh native action bar with final text (no-op on WebKit / empty)
            self._transcript.replace_final_row(handle, final)
            if not self._transcript.is_webkit:
                self._transcript.scroll_to_end()
            self.stream_finished()

        def flush_stream() -> bool:
            """~30 fps paced append — single renderer only (native XOR webkit)."""
            if not still_current():
                return False
            with state["lock"]:
                chunk = "".join(pending) if pending else ""
                pending.clear()
                still_streaming = state["streaming"]

            if chunk:
                self._transcript.stream_delta(handle, chunk)

            if still_streaming:
                return True

            with state["lock"]:
                leftover = "".join(pending) if pending else ""
                pending.clear()
            if leftover and still_current():
                self._transcript.stream_delta(handle, leftover)
            finalize_ui()
            return False

        GLib.timeout_add(33, flush_stream)

        def work():
            try:
                params = RequestParams()
                if self._get_request_params is not None and origin_model:
                    try:
                        params = self._get_request_params(origin_model)
                    except Exception:  # noqa: BLE001
                        params = RequestParams()

                def _on_done(chunk: dict) -> None:
                    if self._on_generation_done is None or not origin_model:
                        return
                    try:
                        self._on_generation_done(origin_model, chunk)
                    except Exception:  # noqa: BLE001
                        pass

                for piece in self.client.chat_stream(
                    origin_model,
                    list(outbound),
                    cancel_event=cancel_event,
                    options=params.options,
                    keep_alive=params.keep_alive,
                    think=params.think,
                    on_done=_on_done if self._on_generation_done is not None else None,
                ):
                    collected.append(piece)
                    with state["lock"]:
                        pending.append(piece)
            except OllamaError as exc:
                with state["lock"]:
                    state["error"] = str(exc)
            finally:
                with state["lock"]:
                    state["streaming"] = False

        threading.Thread(target=work, daemon=True).start()

    def commit_assistant_result(
        self,
        assistant_id: str,
        final: str,
        *,
        mode: str,
        origin_conversation_id: str,
        allow_empty: bool = False,
    ) -> None:
        if not final and not allow_empty:
            return
        text = final or "(no response)"
        idx = self._message_actions.find_message_index(assistant_id)
        messages = self._conversation.messages
        if mode == "continue" and idx >= 0:
            messages[idx]["content"] = text
            try:
                self._get_store().update_message(assistant_id, text)
            except Exception as exc:  # noqa: BLE001
                print(f"continue persist: {exc}", flush=True)
            return
        if mode == "replace":
            if idx >= 0:
                messages[idx]["content"] = text
            else:
                self._conversation.append_local(
                    {"id": assistant_id, "role": "assistant", "content": text}
                )
            try:
                # Row was deleted before stream; re-insert into the
                # conversation the stream actually belongs to.
                self._get_store().append_message(
                    origin_conversation_id,
                    role="assistant",
                    content=text,
                    message_id=assistant_id,
                )
            except Exception as exc:  # noqa: BLE001
                # Might already exist if delete failed — try update
                try:
                    self._get_store().update_message(assistant_id, text)
                except Exception as exc2:  # noqa: BLE001
                    print(f"replace persist: {exc} / {exc2}", flush=True)
            return
        # new
        self._conversation.append_local(
            {"id": assistant_id, "role": "assistant", "content": text}
        )
        try:
            self._get_store().append_message(
                origin_conversation_id,
                role="assistant",
                content=text,
                message_id=assistant_id,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"persist message failed: {exc}", flush=True)

    def stream_finished(self) -> bool:
        self._streaming = False
        self._active_stream_cancel = None
        model = self._get_current_model()
        if self.send_btn is not None:
            self.send_btn.set_sensitive(bool(model))
            self.send_btn.set_visible(True)
        if self.stop_btn is not None:
            self.stop_btn.set_visible(False)
            self.stop_btn.set_sensitive(False)
        if model:
            self._set_status(model)
        else:
            self._set_status("Ready")
        return False
