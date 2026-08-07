"""Message-action helpers and intent dispatch (group L)."""

from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gdk", "4.0")

from gi.repository import Gdk

from conversation_lifecycle import ConversationLifecycleController
from conversation_store import ConversationStore


class MessageActionController:
    """Own find/api/clipboard/delete/drop/regenerate/edit/continue business logic."""

    def __init__(
        self,
        *,
        get_store: Callable[[], ConversationStore],
        conversation: ConversationLifecycleController,
        is_streaming: Callable[[], bool],
        is_loading_model: Callable[[], bool],
        get_current_model: Callable[[], str | None],
        is_webkit: Callable[[], bool],
        post_transcript: Callable[[dict], None],
        reset_empty_transcript: Callable[[], None],
        remove_native_message: Callable[[str], None],
        append_native_message: Callable[..., object],
        start_assistant_stream: Callable[..., None],
    ) -> None:
        self._get_store = get_store
        self._conversation = conversation
        self._is_streaming = is_streaming
        self._is_loading_model = is_loading_model
        self._get_current_model = get_current_model
        self._is_webkit = is_webkit
        self._post_transcript = post_transcript
        self._reset_empty_transcript = reset_empty_transcript
        self._remove_native_message = remove_native_message
        self._append_native_message = append_native_message
        self._start_assistant_stream = start_assistant_stream

    def rebind_is_streaming(self, is_streaming: Callable[[], bool]) -> None:
        """Rebind streaming query when Phase 26 owns stream state."""
        self._is_streaming = is_streaming

    def rebind_start_assistant_stream(
        self, start_assistant_stream: Callable[..., None]
    ) -> None:
        """Rebind stream start when Phase 26 owns the streaming engine."""
        self._start_assistant_stream = start_assistant_stream

    def find_message_index(self, message_id: str) -> int:
        for i, m in enumerate(self._conversation.messages):
            if m.get("id") == message_id:
                return i
        return -1

    def api_messages(
        self, messages: list[dict] | None = None
    ) -> list[dict]:
        """Build Ollama chat history. Include non-empty thinking on assistants."""
        src = messages if messages is not None else self._conversation.messages
        out: list[dict] = []
        for m in src:
            if m.get("role") not in ("user", "assistant"):
                continue
            if m.get("content") is None and not (m.get("thinking") or ""):
                continue
            row: dict = {
                "role": m["role"],
                "content": m.get("content") if m.get("content") is not None else "",
            }
            thinking = (m.get("thinking") or "").strip()
            if m.get("role") == "assistant" and thinking:
                row["thinking"] = m.get("thinking") or ""
            out.append(row)
        return out

    def clipboard_set(self, text: str) -> None:
        display = Gdk.Display.get_default()
        if display is not None and text is not None:
            display.get_clipboard().set(text)

    def delete_message(self, message_id: str) -> None:
        if not message_id or self._is_streaming() or self._is_loading_model():
            return
        idx = self.find_message_index(message_id)
        if idx < 0:
            return
        # Drop this message and everything after (keeps transcript coherent)
        dropped = self._conversation.truncate_from(idx)
        for m in dropped:
            mid = m.get("id")
            if not mid:
                continue
            try:
                self._get_store().delete_message(
                    mid, conversation_id=self._conversation.conversation_id
                )
            except Exception as exc:  # noqa: BLE001
                print(f"delete persist: {exc}", flush=True)
            if self._is_webkit():
                self._post_transcript({"type": "message_removed", "id": mid})
            else:
                self._remove_native_message(mid)
        if self._conversation.messages_empty():
            self._reset_empty_transcript()

    def drop_messages_from(self, idx: int, *, keep_ui_id: str | None = None) -> None:
        """Remove messages[idx:] from memory, DB, and transcript UI."""
        if idx < 0 or idx >= len(self._conversation.messages):
            return
        dropped = self._conversation.truncate_from(idx)
        for m in dropped:
            mid = m.get("id")
            if not mid:
                continue
            try:
                self._get_store().delete_message(
                    mid, conversation_id=self._conversation.conversation_id
                )
            except Exception as exc:  # noqa: BLE001
                print(f"drop persist: {exc}", flush=True)
            if keep_ui_id and mid == keep_ui_id:
                continue
            if self._is_webkit():
                self._post_transcript({"type": "message_removed", "id": mid})
            else:
                self._remove_native_message(mid)

    def regenerate_message(self, message_id: str) -> None:
        if (
            not message_id
            or self._is_streaming()
            or self._is_loading_model()
            or not self._get_current_model()
        ):
            return
        idx = self.find_message_index(message_id)
        if idx < 0:
            return
        role = self._conversation.messages[idx].get("role")
        if role == "user":
            # Re-run from this user turn: drop following replies, stream new assistant
            self.drop_messages_from(idx + 1)
            prefix = list(self._conversation.messages)
            self._start_assistant_stream(
                mode="new",
                api_messages=self.api_messages(prefix),
            )
            return
        if role != "assistant":
            return
        # Replace this assistant reply; drop any later turns
        dropped_tail = list(self._conversation.messages[idx + 1 :])
        for m in dropped_tail:
            mid = m.get("id")
            if not mid:
                continue
            try:
                self._get_store().delete_message(
                    mid, conversation_id=self._conversation.conversation_id
                )
            except Exception as exc:  # noqa: BLE001
                print(f"regen tail delete: {exc}", flush=True)
            if self._is_webkit():
                self._post_transcript({"type": "message_removed", "id": mid})
            else:
                self._remove_native_message(mid)
        self._conversation.truncate_from(idx)
        try:
            self._get_store().delete_message(
                message_id, conversation_id=self._conversation.conversation_id
            )
        except Exception as exc:  # noqa: BLE001
            print(f"regen delete: {exc}", flush=True)
        prefix = list(self._conversation.messages)
        self._start_assistant_stream(
            mode="replace",
            assistant_id=message_id,
            api_messages=self.api_messages(prefix),
        )

    def edit_resend_message(self, message_id: str, text: str) -> None:
        """Edit a user prompt, drop later turns, resubmit to the model."""
        text = (text or "").strip()
        if (
            not message_id
            or not text
            or self._is_streaming()
            or self._is_loading_model()
            or not self._get_current_model()
        ):
            return
        idx = self.find_message_index(message_id)
        if idx < 0 or self._conversation.messages[idx].get("role") != "user":
            return
        self._conversation.messages[idx]["content"] = text
        try:
            self._get_store().update_message(message_id, text)
        except Exception as exc:  # noqa: BLE001
            print(f"edit_resend persist: {exc}", flush=True)
        # Drop everything after this user message
        self.drop_messages_from(idx + 1)
        # Sync bubble text (WebKit edit UI already set it; still push for consistency)
        if self._is_webkit():
            self._post_transcript(
                {
                    "type": "message_added",
                    "id": message_id,
                    "role": "user",
                    "text": text,
                    "streaming": False,
                }
            )
        else:
            self._remove_native_message(message_id)
            self._append_native_message("user", text, message_id=message_id)
        prefix = list(self._conversation.messages)
        self._start_assistant_stream(
            mode="new",
            api_messages=self.api_messages(prefix),
        )

    def continue_message(self, message_id: str) -> None:
        if (
            not message_id
            or self._is_streaming()
            or self._is_loading_model()
            or not self._get_current_model()
        ):
            return
        idx = self.find_message_index(message_id)
        if idx < 0 or self._conversation.messages[idx].get("role") != "assistant":
            return
        # Only allow continue on the last assistant message (stable ordering)
        if idx != len(self._conversation.messages) - 1:
            print("continue: only the latest assistant message", flush=True)
            return
        seed = self._conversation.messages[idx].get("content") or ""
        api = self.api_messages(self._conversation.messages[: idx + 1])
        api.append(
            {
                "role": "user",
                "content": (
                    "Continue your previous response without repeating "
                    "what you already wrote."
                ),
            }
        )
        self._start_assistant_stream(
            mode="continue",
            assistant_id=message_id,
            seed_text=seed,
            api_messages=api,
        )

    def handle_intent(self, payload: dict) -> bool:
        """Handle intents from WebKit and native transcript action surfaces."""
        typ = payload.get("type")
        if typ == "copy_text":
            text = payload.get("text") or ""
            if text:
                self.clipboard_set(text)
        elif typ == "ready":
            pass
        elif typ == "regenerate":
            self.regenerate_message(str(payload.get("id") or ""))
        elif typ == "continue":
            self.continue_message(str(payload.get("id") or ""))
        elif typ == "delete_message":
            self.delete_message(str(payload.get("id") or ""))
        elif typ == "edit_resend":
            self.edit_resend_message(
                str(payload.get("id") or ""),
                str(payload.get("text") or ""),
            )
        return False
