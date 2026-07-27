"""Conversation export through the GTK file-dialog lifecycle."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk

from conversation_store import ConversationStore


class ConversationExporter:
    """Export stored conversations without owning conversation title policy."""

    def __init__(
        self,
        *,
        store: ConversationStore,
        transient_parent: Gtk.Window,
        title_provider: Callable[[str], str],
    ) -> None:
        self._store = store
        self._transient_parent = transient_parent
        self._title_provider = title_provider

    def set_title_provider(self, title_provider: Callable[[str], str]) -> None:
        """Rebind title projection when conversation ownership moves."""
        self._title_provider = title_provider

    def _safe_export_basename(self, conversation_id: str) -> str:
        title = self._title_provider(conversation_id)
        if title == "this chat":
            title = "chat"
        safe = "".join(c if c.isalnum() or c in " -_" else "-" for c in title)
        safe = "-".join(safe.split())[:48].strip("-") or "chat"
        return f"chickenbutt-{safe}"

    def export_conversation(self, conversation_id: str, fmt: str = "md") -> None:
        """Save conversation as Markdown or JSON via file dialog."""
        fmt = (fmt or "md").lower().strip(".")
        if fmt not in ("md", "markdown", "json"):
            fmt = "md"
        if fmt == "markdown":
            fmt = "md"

        if fmt == "json":
            payload = self._store.export_dict(conversation_id)
            if payload is None:
                print("export: conversation not found", flush=True)
                return
            body = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
            ext = "json"
            mime = "application/json"
        else:
            body = self._store.export_markdown(conversation_id)
            if body is None:
                print("export: conversation not found", flush=True)
                return
            ext = "md"
            mime = "text/markdown"

        basename = f"{self._safe_export_basename(conversation_id)}.{ext}"
        dialog = Gtk.FileDialog()
        dialog.set_title("Export chat")
        dialog.set_initial_name(basename)
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filt = Gtk.FileFilter()
        if ext == "json":
            filt.set_name("JSON")
            filt.add_pattern("*.json")
            filt.add_mime_type(mime)
        else:
            filt.set_name("Markdown")
            filt.add_pattern("*.md")
            filt.add_mime_type(mime)
        filters.append(filt)
        dialog.set_filters(filters)
        dialog.set_default_filter(filt)

        def on_save(_dlg, result) -> None:
            try:
                file = dialog.save_finish(result)
            except GLib.Error as exc:
                if exc.matches(Gio.io_error_quark(), Gio.IOErrorEnum.CANCELLED):
                    return
                print(f"export dialog: {exc}", flush=True)
                return
            if file is None:
                return
            path = file.get_path()
            if not path:
                print("export: no path", flush=True)
                return
            try:
                Path(path).write_text(body, encoding="utf-8")
                print(f"Exported {fmt} → {path}", flush=True)
            except OSError as exc:
                print(f"export write failed: {exc}", flush=True)
                err = Adw.MessageDialog(
                    transient_for=self._transient_parent,
                    heading="Export failed",
                    body=str(exc),
                )
                err.add_response("ok", "OK")
                err.present()

        dialog.save(self._transient_parent, None, on_save)
