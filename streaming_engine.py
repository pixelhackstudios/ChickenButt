"""Assistant streaming send/start/stop/invalidate (group M)."""

from __future__ import annotations

import threading
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import GLib, Gtk

from context_compaction import (
    DEFAULT_WINDOW,
    StoredSummary,
    TokenCalibration,
    api_row,
    is_api_message,
    plan_outbound,
    rows_tokens,
    summary_chunks,
    summary_reply_tokens,
    summary_request,
    summary_row,
)
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


def _linked_cancel(
    parent: threading.Event,
) -> tuple[threading.Event, threading.Event]:
    """A fresh event set when *parent* is; set the second event to unlink."""
    child = threading.Event()
    unlink = threading.Event()

    def follow() -> None:
        while not unlink.is_set():
            if parent.wait(0.1):
                child.set()
                return

    threading.Thread(target=follow, daemon=True, name="cb-summary-cancel").start()
    return child, unlink


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

        # Context compaction: learned chars/token and last allocated window
        # per model (from /api/ps), both process-local.
        self._calibration = TokenCalibration()
        self._window_cache: dict[str, int] = {}

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
        api_messages: list[dict] | None = None,
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
        # Resolve display gate before begin_stream so Continue does not reseed
        # prior thinking into the UI when Show reasoning is off.
        params = RequestParams()
        if self._get_request_params is not None and origin_model:
            try:
                params = self._get_request_params(origin_model)
            except Exception:  # noqa: BLE001
                params = RequestParams()
        show_reasoning = params.think is True

        # Prior thinking for continue-append / persist; replace starts clean.
        seed_thinking = ""
        if mode == "continue" and assistant_id:
            seed_thinking = self._conversation.message_thinking(assistant_id) or ""
        # UI only: never paint stored reasoning when display is off.
        ui_seed_thinking = (
            seed_thinking if (mode == "continue" and show_reasoning) else ""
        )
        handle = self._transcript.begin_stream(
            mode=mode,
            message_id=aid,
            stream_seed=stream_seed,
            seed_thinking=ui_seed_thinking,
            clear_thinking=(mode in ("replace", "new")),
        )

        pending: list[str] = []
        collected: list[str] = []
        thinking_pending: list[str] = []
        thinking_collected: list[str] = []
        state = {
            "streaming": True,
            "error": None,
            "ui_done": False,
            "lock": threading.Lock(),
            "show_reasoning": show_reasoning,
        }
        outbound = (
            api_messages
            if api_messages is not None
            else self._message_actions.api_messages()
        )

        # Compaction works on the id-bearing history behind ``outbound``.
        # Every caller builds outbound from the current messages, plus an
        # optional tail (Continue's instruction row); if that ever stops
        # holding, outbound is sent untouched.
        history = list(self._conversation.messages)
        base_rows = [api_row(m) for m in history if is_api_message(m)]
        outbound_list = list(outbound)
        extra_tail: list[dict] | None = None
        if outbound_list[: len(base_rows)] == base_rows:
            extra_tail = outbound_list[len(base_rows) :]
        stored_summary: StoredSummary | None = None
        if extra_tail is not None and origin_conversation_id:
            try:
                rec = self._get_store().get_context_summary(origin_conversation_id)
            except Exception:  # noqa: BLE001
                rec = None
            if rec is not None:
                stored_summary = StoredSummary(
                    through_message_id=rec.through_message_id,
                    content=rec.content,
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
            thinking_piece = "".join(thinking_collected)
            if mode == "continue":
                final = join_continue(seed_text, piece)
                final_thinking = join_continue(seed_thinking, thinking_piece)
            else:
                final = piece
                final_thinking = thinking_piece

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
                    handle,
                    error=str(err),
                    final=final,
                    thinking=final_thinking if state["show_reasoning"] else "",
                )
            else:
                self._transcript.finalize_stream(
                    handle,
                    final=final,
                    thinking=final_thinking if state["show_reasoning"] else "",
                )

            self.commit_assistant_result(
                aid,
                final,
                mode=mode,
                origin_conversation_id=origin_conversation_id or "",
                allow_empty=bool(err) or bool(final_thinking),
                thinking=final_thinking,
            )
            # Refresh native action bar with final text (no-op on WebKit / empty)
            self._transcript.replace_final_row(
                handle,
                final,
                thinking=final_thinking if state["show_reasoning"] else "",
            )
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
                tchunk = "".join(thinking_pending) if thinking_pending else ""
                thinking_pending.clear()
                still_streaming = state["streaming"]
                show = state["show_reasoning"]

            if tchunk and show:
                self._transcript.stream_reasoning_delta(handle, tchunk)
            if chunk:
                self._transcript.stream_delta(handle, chunk)

            if still_streaming:
                return True

            with state["lock"]:
                leftover = "".join(pending) if pending else ""
                pending.clear()
                tleft = "".join(thinking_pending) if thinking_pending else ""
                thinking_pending.clear()
                show = state["show_reasoning"]
            if tleft and show and still_current():
                self._transcript.stream_reasoning_delta(handle, tleft)
            if leftover and still_current():
                self._transcript.stream_delta(handle, leftover)
            finalize_ui()
            return False

        GLib.timeout_add(33, flush_stream)

        def work():
            try:
                # params / show_reasoning resolved on the UI thread before
                # begin_stream so Continue seed painting stays gated.
                send_rows = outbound_list
                window = DEFAULT_WINDOW
                if extra_tail is not None and origin_model:
                    window = self._context_window(origin_model, params)
                    try:
                        send_rows = self._compact_outbound(
                            model=origin_model,
                            history=history,
                            extra_tail=extra_tail,
                            summary=stored_summary,
                            window=window,
                            params=params,
                            cancel_event=cancel_event,
                            conversation_id=origin_conversation_id or "",
                        )
                    except Exception as exc:  # noqa: BLE001
                        # Compaction must never cost the user their reply.
                        print(f"context compaction skipped: {exc}", flush=True)
                        send_rows = outbound_list

                def _on_done(chunk: dict) -> None:
                    if origin_model and isinstance(chunk, dict):
                        try:
                            self._calibration.observe(
                                origin_model,
                                rows=send_rows,
                                prompt_eval_count=chunk.get("prompt_eval_count"),
                                window=window,
                            )
                        except Exception:  # noqa: BLE001
                            pass
                    if self._on_generation_done is None or not origin_model:
                        return
                    try:
                        self._on_generation_done(origin_model, chunk)
                    except Exception:  # noqa: BLE001
                        pass

                def _on_thinking(piece: str) -> None:
                    if not piece:
                        return
                    thinking_collected.append(piece)
                    with state["lock"]:
                        thinking_pending.append(piece)

                for piece in self.client.chat_stream(
                    origin_model,
                    list(send_rows),
                    cancel_event=cancel_event,
                    options=params.options,
                    keep_alive=params.keep_alive,
                    think=params.think,
                    on_done=_on_done,
                    on_thinking=_on_thinking,
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

    def _context_window(self, model: str, params: RequestParams) -> int:
        """Window the request will run in (worker thread).

        An explicit num_ctx wins; Auto uses what Ollama allocated for the
        loaded model (/api/ps), then the last value seen, then 4096.
        """
        opts = params.options or {}
        n = opts.get("num_ctx")
        if isinstance(n, int) and not isinstance(n, bool) and n > 0:
            return n
        try:
            for row in self.client.list_running_models_detail():
                if row.name == model or row.model == model:
                    ctx = row.context_length
                    if isinstance(ctx, int) and ctx > 0:
                        self._window_cache[model] = ctx
                        return ctx
        except Exception:  # noqa: BLE001
            pass
        return self._window_cache.get(model, DEFAULT_WINDOW)

    def _compact_outbound(
        self,
        *,
        model: str,
        history: list[dict],
        extra_tail: list[dict],
        summary: StoredSummary | None,
        window: int,
        params: RequestParams,
        cancel_event: threading.Event,
        conversation_id: str,
    ) -> list[dict]:
        """Fit history into *window*; may summarize (worker thread)."""
        cpt = self._calibration.chars_per_token(model)
        npred = (params.options or {}).get("num_predict")
        plan = plan_outbound(
            history,
            window=window,
            summary=summary,
            num_predict=npred if isinstance(npred, int) else None,
            chars_per_token=cpt,
            extra_tail_tokens=rows_tokens(extra_tail, cpt),
        )
        rows = list(plan.rows)
        marker: str | None = (
            plan.used_summary.through_message_id if plan.used_summary else None
        )
        if plan.oversize:
            print(
                "context: latest message alone exceeds the context window",
                flush=True,
            )
        if plan.needs_summary and plan.summary_through_id:
            GLib.idle_add(self._set_status, "Summarizing earlier messages…")
            new = self._summarize(
                model,
                prior=plan.prior_summary,
                messages=list(plan.to_summarize),
                window=window,
                cpt=cpt,
                params=params,
                cancel_event=cancel_event,
            )
            if new:
                rows = [summary_row(new)] + list(plan.kept_rows)
                marker = plan.summary_through_id
                GLib.idle_add(
                    self._persist_summary,
                    conversation_id,
                    plan.summary_through_id,
                    new,
                    model,
                )
            if not cancel_event.is_set():
                GLib.idle_add(self._set_status, "Thinking…")
        if summary is not None or marker is not None:
            GLib.idle_add(self._show_context_marker, conversation_id, marker)
        return rows + list(extra_tail)

    def _summarize(
        self,
        model: str,
        *,
        prior: str,
        messages: list[dict],
        window: int,
        cpt: float,
        params: RequestParams,
        cancel_event: threading.Event,
    ) -> str | None:
        """Rolling summary of *messages* on top of *prior*; None on failure."""
        options = dict(params.options or {})
        options.pop("num_predict", None)
        # A reply cap would starve a thinking model of visible output.
        if params.think is False:
            options["num_predict"] = summary_reply_tokens(window)
        current = prior
        try:
            for lines in summary_chunks(messages, window=window, chars_per_token=cpt):
                if cancel_event.is_set():
                    return None
                pieces: list[str] = []
                # chat_stream sets the event it is given when it finishes
                # (to release its socket watcher), so each call gets its own
                # event that follows the reply's Stop.
                call_cancel, unlink = _linked_cancel(cancel_event)
                try:
                    for piece in self.client.chat_stream(
                        model,
                        summary_request(current, lines),
                        cancel_event=call_cancel,
                        options=options or None,
                        keep_alive=params.keep_alive,
                        think=params.think,
                    ):
                        pieces.append(piece)
                finally:
                    unlink.set()
                if cancel_event.is_set():
                    return None
                text = "".join(pieces).strip()
                if not text:
                    return None
                current = text
        except OllamaError as exc:
            print(f"context summary failed: {exc}", flush=True)
            return None
        except Exception as exc:  # noqa: BLE001
            print(f"context summary failed: {exc}", flush=True)
            return None
        return current if current.strip() else None

    def _persist_summary(
        self, conversation_id: str, through_id: str, content: str, model: str
    ) -> bool:
        """Store a new summary (main thread). Anchor must still exist."""
        if not conversation_id or not through_id:
            return False
        try:
            self._get_store().set_context_summary(
                conversation_id,
                through_message_id=through_id,
                content=content,
                model=model,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"context summary persist: {exc}", flush=True)
        return False

    def _show_context_marker(self, conversation_id: str, after_id: str | None) -> bool:
        """Divider where the model's memory starts (main thread)."""
        if conversation_id != self._conversation.conversation_id:
            return False
        try:
            self._transcript.set_context_marker(after_id)
        except Exception as exc:  # noqa: BLE001
            print(f"context marker: {exc}", flush=True)
        return False

    def commit_assistant_result(
        self,
        assistant_id: str,
        final: str,
        *,
        mode: str,
        origin_conversation_id: str,
        allow_empty: bool = False,
        thinking: str = "",
    ) -> None:
        thinking = thinking or ""
        if not final and not thinking and not allow_empty:
            return
        # Thinking-only partial (Stop mid-reasoning) keeps empty content, not
        # the placeholder — content and thinking stay siblings.
        if final:
            text = final
        elif thinking:
            text = ""
        else:
            text = "(no response)"
        idx = self._message_actions.find_message_index(assistant_id)
        messages = self._conversation.messages
        if mode == "continue" and idx >= 0:
            messages[idx]["content"] = text
            messages[idx]["thinking"] = thinking
            try:
                self._get_store().update_message(
                    assistant_id, text, thinking=thinking
                )
            except Exception as exc:  # noqa: BLE001
                print(f"continue persist: {exc}", flush=True)
            return
        if mode == "replace":
            if idx >= 0:
                messages[idx]["content"] = text
                messages[idx]["thinking"] = thinking
            else:
                self._conversation.append_local(
                    {
                        "id": assistant_id,
                        "role": "assistant",
                        "content": text,
                        "thinking": thinking,
                    }
                )
            try:
                # Row was deleted before stream; re-insert into the
                # conversation the stream actually belongs to.
                self._get_store().append_message(
                    origin_conversation_id,
                    role="assistant",
                    content=text,
                    message_id=assistant_id,
                    thinking=thinking,
                )
            except Exception as exc:  # noqa: BLE001
                # Might already exist if delete failed — try update
                try:
                    self._get_store().update_message(
                        assistant_id, text, thinking=thinking
                    )
                except Exception as exc2:  # noqa: BLE001
                    print(f"replace persist: {exc} / {exc2}", flush=True)
            return
        # new
        self._conversation.append_local(
            {
                "id": assistant_id,
                "role": "assistant",
                "content": text,
                "thinking": thinking,
            }
        )
        try:
            self._get_store().append_message(
                origin_conversation_id,
                role="assistant",
                content=text,
                message_id=assistant_id,
                thinking=thinking,
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
