"""Active-conversation projection and lifecycle ownership (group F)."""

from __future__ import annotations

import uuid
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk

from conversation_store import ConversationStore


class ConversationLifecycleController:
    """Own the in-memory active conversation ID + messages projection."""

    def __init__(
        self,
        *,
        store: ConversationStore,
        transient_parent: Gtk.Window,
        get_current_model: Callable[[], str | None],
        is_loading_model: Callable[[], bool],
        is_load_failed: Callable[[], bool],
        is_streaming: Callable[[], bool],
        reset_greetings: Callable[[], None],
        clear_native_rows: Callable[[], None],
        render_empty_transcript: Callable[[], None],
        apply_restored_transcript: Callable[[list[dict[str, str]]], None],
        mark_history_dirty: Callable[[], None],
        rebuild_history_list: Callable[[], bool],
        refresh_chat_title: Callable[[], bool],
        set_status: Callable[[str], None],
        show_ephemeral_greeting: Callable[[], None],
        sync_composer_hint: Callable[[], None],
        select_model_name: Callable[..., None],
        save_last_model: Callable[[str], None],
        is_ephemeral_greeting: Callable[[str, str], bool],
        request_stop: Callable[[], None],
        invalidate_active_stream: Callable[[], None],
        grab_input_focus: Callable[[], None],
    ) -> None:
        self._store = store
        self._transient_parent = transient_parent
        self._get_current_model = get_current_model
        self._is_loading_model = is_loading_model
        self._is_load_failed = is_load_failed
        self._is_streaming = is_streaming
        self._reset_greetings = reset_greetings
        self._clear_native_rows = clear_native_rows
        self._render_empty_transcript = render_empty_transcript
        self._apply_restored_transcript = apply_restored_transcript
        self._mark_history_dirty = mark_history_dirty
        self._rebuild_history_list = rebuild_history_list
        self._refresh_chat_title = refresh_chat_title
        self._set_status = set_status
        self._show_ephemeral_greeting = show_ephemeral_greeting
        self._sync_composer_hint = sync_composer_hint
        self._select_model_name = select_model_name
        self._save_last_model = save_last_model
        self._is_ephemeral_greeting = is_ephemeral_greeting
        self._request_stop = request_stop
        self._invalidate_active_stream = invalidate_active_stream
        self._grab_input_focus = grab_input_focus

        self._conversation_id: str | None = None
        self._messages: list[dict[str, str]] = []
        self._msg_counter = 0
        self._history_restored = False

    def rebind_request_stop(self, request_stop: Callable[[], None]) -> None:
        """Rebind stop when Phase 26 owns the streaming engine."""
        self._request_stop = request_stop

    def rebind_invalidate_active_stream(
        self, invalidate_active_stream: Callable[[], None]
    ) -> None:
        """Rebind invalidate when Phase 26 owns the streaming engine."""
        self._invalidate_active_stream = invalidate_active_stream

    @property
    def conversation_id(self) -> str | None:
        return self._conversation_id

    @conversation_id.setter
    def conversation_id(self, value: str | None) -> None:
        self._conversation_id = value

    @property
    def messages(self) -> list[dict[str, str]]:
        return self._messages

    @messages.setter
    def messages(self, value: list[dict[str, str]]) -> None:
        self._messages = value

    @property
    def history_restored(self) -> bool:
        return self._history_restored

    @history_restored.setter
    def history_restored(self, value: bool) -> None:
        self._history_restored = bool(value)

    @property
    def msg_counter(self) -> int:
        return self._msg_counter

    @msg_counter.setter
    def msg_counter(self, value: int) -> None:
        self._msg_counter = int(value)

    def messages_empty(self) -> bool:
        return not self._messages

    def replace_messages(self, messages: list[dict[str, str]]) -> None:
        """Narrow mutation API for later Phase 24/26 consumers."""
        self._messages = list(messages)

    def append_local(self, message: dict[str, str]) -> None:
        """Narrow mutation API for later Phase 24/26 consumers."""
        self._messages.append(message)

    def truncate_from(self, index: int) -> list[dict[str, str]]:
        """Narrow mutation API: drop from index onward and return dropped rows."""
        dropped = self._messages[index:]
        self._messages = self._messages[:index]
        return dropped

    def message_content(self, message_id: str, fallback: str = "") -> str:
        """Look up in-memory content by id for transcript current-text providers."""
        for message in self._messages:
            if message.get("id") == message_id:
                return message.get("content") or fallback
        return fallback

    def active_conversation_model(self) -> str | None:
        """Provide the active conversation's stored model preference."""
        if not self._conversation_id:
            return None
        conv = self._store.get_conversation(self._conversation_id)
        return conv.model if conv is not None else None

    def next_msg_id(self, prefix: str) -> str:
        self._msg_counter += 1
        return f"{prefix}-{self._msg_counter}-{uuid.uuid4().hex[:6]}"

    def ensure_conversation(self) -> str:
        if self._conversation_id:
            return self._conversation_id
        conv = self._store.ensure_active(model=self._get_current_model())
        self._conversation_id = conv.id
        return conv.id

    def persist_message(
        self, role: str, content: str, message_id: str | None = None
    ) -> None:
        try:
            cid = self.ensure_conversation()
            self._store.append_message(
                cid,
                role=role,
                content=content,
                message_id=message_id,
            )
            # First user message sets title — sidebar + header need refresh
            if role == "user":
                self._mark_history_dirty()
                GLib.idle_add(self._refresh_chat_title)
                GLib.idle_add(self._rebuild_history_list)
        except Exception as exc:  # noqa: BLE001
            print(f"persist message failed: {exc}", flush=True)

    def conversation_display_title(self, conversation_id: str) -> str:
        """Best human title for dialogs / export names."""
        try:
            conv = self._store.get_conversation(conversation_id)
            if conv and (conv.title or "").strip():
                return conv.title.strip()
            for m in self._store.list_messages(conversation_id):
                if m.role == "user" and (m.content or "").strip():
                    return m.content.strip().splitlines()[0][:80]
        except Exception:  # noqa: BLE001
            pass
        if conversation_id == self._conversation_id:
            for m in self._messages:
                if m.get("role") == "user" and (m.get("content") or "").strip():
                    return str(m["content"]).strip().splitlines()[0][:80]
        return "this chat"

    def clear_chat(self) -> None:
        if self._is_streaming():
            self._request_stop()
        self._messages.clear()
        self._reset_greetings()
        self._clear_native_rows()
        # Keep one active row; wipe messages so restart is empty
        try:
            if self._conversation_id:
                self._store.clear_messages(self._conversation_id)
            else:
                conv = self._store.create_conversation(model=self._get_current_model())
                self._conversation_id = conv.id
        except Exception as exc:  # noqa: BLE001
            print(f"clear_chat persist: {exc}", flush=True)
        # Empty chats are hidden from Recent
        self._mark_history_dirty()
        self._rebuild_history_list()
        self._render_empty_transcript()
        self._set_status(self._get_current_model() or "Ready")
        # Re-show ephemeral greeting if a model is already warm
        if (
            self._get_current_model()
            and not self._is_loading_model()
            and not self._is_load_failed()
        ):
            self._show_ephemeral_greeting()
        self._refresh_chat_title()
        self._sync_composer_hint()

    def active_chat_is_empty(self) -> bool:
        """True when there is nothing meaningful to abandon (no saved messages)."""
        if self._messages:
            return False
        if not self._conversation_id:
            return True
        try:
            return self._store.is_empty(self._conversation_id)
        except Exception:  # noqa: BLE001
            return not self._messages

    def new_chat(self) -> None:
        """Create and activate a new empty conversation (multi-chat).

        If the active chat is already empty, do not create another DB row —
        just focus the composer.
        """
        if self._is_streaming():
            self._invalidate_active_stream()
        if self._is_loading_model():
            return

        # Already on a blank slate — avoid empty-chat proliferation
        if self.active_chat_is_empty():
            if (
                self._get_current_model()
                and not self._is_load_failed()
                and not self._messages
            ):
                self._show_ephemeral_greeting()
            self._grab_input_focus()
            return

        # Drop other abandoned empty rows before creating a new one
        try:
            self._store.prune_empty_conversations(keep_id=None)
        except Exception as exc:  # noqa: BLE001
            print(f"prune_empty: {exc}", flush=True)

        try:
            conv = self._store.create_conversation(model=self._get_current_model())
            self._conversation_id = conv.id
        except Exception as exc:  # noqa: BLE001
            print(f"new_chat: {exc}", flush=True)
            return
        self._messages.clear()
        self._reset_greetings()
        self._clear_native_rows()
        self._history_restored = False
        self._render_empty_transcript()
        self._set_status(self._get_current_model() or "Ready")
        if self._get_current_model() and not self._is_load_failed():
            self._show_ephemeral_greeting()
        self._mark_history_dirty()
        self._rebuild_history_list()
        self._refresh_chat_title()
        self._sync_composer_hint()
        self._grab_input_focus()
        print(f"New chat {conv.id[:12]}…", flush=True)

    def confirm_delete_conversation(self, conversation_id: str) -> None:
        title = self.conversation_display_title(conversation_id)
        if len(title) > 60:
            title = title[:57] + "…"
        dialog = Adw.MessageDialog(
            transient_for=self._transient_parent,
            heading="Delete chat?",
            body=f'"{title}" will be permanently removed from this device.',
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")

        def on_response(_d, response: str) -> None:
            if response == "delete":
                self.delete_conversation(conversation_id)

        dialog.connect("response", on_response)
        dialog.present()

    def delete_conversation(self, conversation_id: str) -> None:
        """Delete a chat from SQLite and UI; switch away if it was active."""
        if not conversation_id:
            return
        if self._is_streaming() and conversation_id == self._conversation_id:
            self._invalidate_active_stream()
        was_active = conversation_id == self._conversation_id
        try:
            self._store.delete_conversation(conversation_id)
        except Exception as exc:  # noqa: BLE001
            print(f"delete_conversation: {exc}", flush=True)
            return
        self._mark_history_dirty()
        if was_active:
            # Switch to next remaining chat, or create empty
            nxt = self._store.get_active_conversation()
            if nxt is not None:
                # Force reload even if id was reassigned in meta
                self._conversation_id = None
                self.switch_conversation(nxt.id)
            else:
                self.new_chat()
        else:
            self._rebuild_history_list()
        print(f"Deleted chat {conversation_id[:12]}…", flush=True)

    def switch_conversation(self, conversation_id: str) -> None:
        """Activate another conversation and replay its transcript."""
        if not conversation_id or conversation_id == self._conversation_id:
            return
        if self._is_streaming():
            self._invalidate_active_stream()
        if self._is_loading_model():
            return
        # Leaving an empty draft — drop it so Recent stays clean
        prev = self._conversation_id
        if prev and prev != conversation_id:
            try:
                if self._store.is_empty(prev):
                    self._store.delete_conversation(prev)
                    self._mark_history_dirty()
            except Exception as exc:  # noqa: BLE001
                print(f"prune empty on switch: {exc}", flush=True)
        conv = self._store.get_conversation(conversation_id)
        if conv is None:
            print(f"switch_conversation: missing {conversation_id}", flush=True)
            return
        try:
            self._store.set_active(conversation_id)
        except Exception as exc:  # noqa: BLE001
            print(f"set_active: {exc}", flush=True)
        self._conversation_id = conversation_id
        self._reset_greetings()
        self._clear_native_rows()
        # Load messages (filter legacy greeting)
        try:
            stored = self._store.list_messages(conversation_id)
        except Exception as exc:  # noqa: BLE001
            print(f"switch load messages: {exc}", flush=True)
            stored = []
        real = [
            m
            for m in stored
            if not self._is_ephemeral_greeting(m.role, m.content)
        ]
        self._messages = [
            {"id": m.id, "role": m.role, "content": m.content} for m in real
        ]
        self._history_restored = bool(real)
        payload = [
            {"id": m.id, "role": m.role, "content": m.content} for m in real
        ]
        if real:
            self._apply_restored_transcript(payload)
        else:
            self._render_empty_transcript()
            if self._get_current_model() and not self._is_load_failed():
                self._show_ephemeral_greeting()
        self._sync_composer_hint()
        # Restore per-conversation model when available
        if conv.model:
            self._save_last_model(conv.model)
            self._select_model_name(conv.model, warm=True, greet=not real)
        else:
            self._set_status(self._get_current_model() or "Ready")
        self._mark_history_dirty()
        self._rebuild_history_list()
        self._refresh_chat_title()
        print(
            f"Switched to {conversation_id[:12]}… "
            f"({len(real)} messages)",
            flush=True,
        )

    def restore_history(self) -> None:
        """Load most recent / active conversation into memory + transcript."""
        try:
            conv = self._store.get_active_conversation()
            if conv is None:
                conv = self._store.create_conversation(model=self._get_current_model())
            self._conversation_id = conv.id
            # Drop abandoned empty chats (keep the active row even if empty)
            try:
                n = self._store.prune_empty_conversations(keep_id=conv.id)
                if n:
                    print(f"Pruned {n} empty chat(s)", flush=True)
                    self._mark_history_dirty()
            except Exception as exc:  # noqa: BLE001
                print(f"prune on restore: {exc}", flush=True)
            stored = self._store.list_messages(conv.id)
            # Drop legacy greeting rows (never model context, never chat bubbles)
            real = [
                m
                for m in stored
                if not self._is_ephemeral_greeting(m.role, m.content)
            ]
            legacy = [
                m for m in stored if self._is_ephemeral_greeting(m.role, m.content)
            ]
            for m in legacy:
                try:
                    self._store.delete_message(m.id)
                except Exception:  # noqa: BLE001
                    pass
            if legacy:
                try:
                    self._store.touch(conv.id)
                except Exception:  # noqa: BLE001
                    pass
            if not real:
                self._history_restored = False
                self._messages = []
                return
            payload = [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                }
                for m in real
            ]
            self._messages = [
                {"id": m.id, "role": m.role, "content": m.content} for m in real
            ]
            self._history_restored = True
            if conv.model:
                self._save_last_model(conv.model)
            self._apply_restored_transcript(payload)
            self._sync_composer_hint()
            print(
                f"Restored conversation {conv.id[:12]}… "
                f"({len(real)} messages)",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"restore history failed: {exc}", flush=True)
            self._history_restored = False
