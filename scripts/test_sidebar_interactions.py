#!/usr/bin/env python3
"""Regression: settings, composer, export, health, model-load, and sidebar behavior.

Covers the Phase-1 settings seam, the complete Phase-3 composer
characterization surface, the Phase-5 export seam, every Phase-7 health/probe
branch, the Phase-9 model-load lifecycle, Phase-19 composer CLI commands
(including `_send`'s busy guard and command dispatch), Phase-21 conversation
lifecycle helpers and persistence-failure asymmetry, Phase-23 message-action
helpers/guards/routing and completed replace/continue commits, Phase-25
direct `_send` guards/success ordering and mid-stream non-cancellation error
health reclassification, UI-construction post-build contracts (widget attrs,
Gio actions/accels, header chrome, load-overlay tree, transcript mode timing,
controller ownership/ordering), pointer cursors on clickable controls, the
model selector living in the sidebar (not under the header), and the sidebar
always starting closed regardless of a stale settings file.

Real ChatSidebar + real WebKit view + real GLib loop, same pattern as the
other scripts/test_*.py files. Model refresh/load network calls are
monkeypatched on the real OllamaClient instance (fake models, instant
"already loaded") so the real production _refresh_models -> _on_model_selected
-> _begin_model_load -> _save_last_model chain runs end-to-end without
needing a real Ollama server.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, GObject, Gtk  # noqa: E402

import conversation_export as export_module  # noqa: E402
import health_probe as health_probe_module  # noqa: E402
import model_session as model_session_module  # noqa: E402
from composer_geometry import ComposerGeometry  # noqa: E402
from conversation_export import ConversationExporter  # noqa: E402
import conversation_lifecycle as conversation_lifecycle_module  # noqa: E402
from conversation_lifecycle import ConversationLifecycleController  # noqa: E402
from health_probe import HealthProbeController  # noqa: E402
import message_actions as message_actions_module  # noqa: E402
from message_actions import MessageActionController  # noqa: E402
from model_session import ModelLoadController  # noqa: E402
from message_widgets import MessageBody  # noqa: E402
from ollama_client import OllamaClient, OllamaError  # noqa: E402
from ollama_health import HealthKind, HealthState, ProbeResult  # noqa: E402
import composer_cli as composer_cli_module  # noqa: E402
from composer_cli import ComposerCliController  # noqa: E402
from sidebar_history import SidebarHistoryController  # noqa: E402
import streaming_engine as streaming_engine_module  # noqa: E402
from streaming_engine import StreamingEngineController  # noqa: E402
import transcript_adapter as transcript_adapter_module  # noqa: E402
from transcript_adapter import TranscriptAdapter  # noqa: E402
import window as window_module  # noqa: E402
from window import ChatSidebar  # noqa: E402


class Results:
    def __init__(self) -> None:
        self.ok: list[str] = []
        self.fail: list[str] = []

    def check(self, name: str, cond: bool, detail: str = "") -> None:
        if cond:
            self.ok.append(name)
            print(f"  PASS  {name}" + (f" — {detail}" if detail else ""), flush=True)
        else:
            self.fail.append(name)
            print(f"  FAIL  {name}" + (f" — {detail}" if detail else ""), flush=True)


def pump(seconds: float = 0.0) -> None:
    ctx = GLib.main_context_default()
    deadline = time.time() + seconds
    while True:
        while ctx.pending():
            ctx.iteration(False)
        if time.time() >= deadline:
            break
        time.sleep(0.01)


def wait_until(cond, timeout: float = 20.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        pump(0.02)
        if cond():
            return True
    return False


def cursor_name(widget) -> str | None:
    cur = widget.get_cursor()
    return cur.get_name() if cur is not None else None


def is_descendant(widget, ancestor) -> bool:
    p = widget.get_parent()
    while p is not None:
        if p is ancestor:
            return True
        p = p.get_parent()
    return False


def child_index(container, target) -> int:
    """Index of target among container's direct children, or -1."""
    i = 0
    child = container.get_first_child()
    while child is not None:
        if child is target:
            return i
        child = child.get_next_sibling()
        i += 1
    return -1


def direct_child_ancestor(widget, container):
    """Walk up from widget to find the ancestor that is a direct child of
    container — skips GTK-internal wrappers like the Gtk.Viewport a
    ScrolledWindow inserts around a non-Gtk.Scrollable child."""
    w = widget
    while w is not None:
        parent = w.get_parent()
        if parent is container:
            return w
        w = parent
    return None


def direct_children(container) -> list[Gtk.Widget]:
    children: list[Gtk.Widget] = []
    child = container.get_first_child()
    while child is not None:
        children.append(child)
        child = child.get_next_sibling()
    return children


def eval_js(web, js: str) -> None:
    web._view.evaluate_javascript(js, -1, None, None, None, None, None)


def eval_js_value(web, js: str, captured: dict, timeout: float = 10.0):
    def cb(_gobj, res, *_a):
        try:
            val = web._view.evaluate_javascript_finish(res)
            captured["json"] = val.to_json(0) if val is not None else None
        except Exception as exc:  # noqa: BLE001
            captured["error"] = repr(exc)

    captured.pop("json", None)
    captured.pop("error", None)
    web._view.evaluate_javascript(js, -1, None, None, None, cb, None)
    wait_until(lambda: "json" in captured or "error" in captured, timeout=timeout)
    if "json" in captured:
        raw = captured["json"]
        # evaluate_javascript_finish's to_json double-encodes string results.
        try:
            return json.loads(json.loads(raw))
        except (TypeError, json.JSONDecodeError):
            return json.loads(raw) if raw is not None else None
    return None


def characterize_settings(
    results: Results,
    settings_dir: Path,
    settings_path: Path,
) -> None:
    """Lock down the settings helpers before their Phase-2 extraction."""
    print("\n[0] Settings helper characterization", flush=True)

    window_module._SETTINGS_DIR = settings_dir
    window_module._SETTINGS_PATH = settings_path

    results.check(
        "missing settings file reads as an empty mapping",
        window_module._read_settings() == {},
    )

    settings_dir.mkdir(parents=True, exist_ok=True)
    settings_path.write_text('["not", "a", "mapping"]', encoding="utf-8")
    results.check(
        "valid non-object JSON is ignored",
        window_module._read_settings() == {},
    )
    settings_path.write_text("{broken", encoding="utf-8")
    results.check(
        "malformed JSON is ignored",
        window_module._read_settings() == {},
    )
    settings_path.write_text(
        json.dumps({"last_model": "model-a", "keep": "value"}),
        encoding="utf-8",
    )
    results.check(
        "valid settings objects are returned intact",
        window_module._read_settings()
        == {"last_model": "model-a", "keep": "value"},
    )

    class ReadFailurePath:
        def is_file(self) -> bool:
            return True

        def read_text(self, *, encoding: str) -> str:
            raise OSError("forced read failure")

    window_module._SETTINGS_PATH = ReadFailurePath()
    results.check(
        "settings read failures are ignored",
        window_module._read_settings() == {},
    )

    class TypeFailurePath:
        def is_file(self) -> bool:
            return True

        def read_text(self, *, encoding: str):
            return object()

    window_module._SETTINGS_PATH = TypeFailurePath()
    results.check(
        "settings read type failures are ignored",
        window_module._read_settings() == {},
    )

    window_module._SETTINGS_PATH = settings_path
    window_module._write_settings({"unicode": "✓", "nested": {"value": 1}})
    written = settings_path.read_text(encoding="utf-8")
    results.check(
        "settings writes are UTF-8 JSON objects with a trailing newline",
        written.endswith("\n")
        and json.loads(written) == {"unicode": "✓", "nested": {"value": 1}},
    )

    class WriteFailurePath:
        def write_text(self, *_args, **_kwargs) -> None:
            raise OSError("forced write failure")

    window_module._SETTINGS_PATH = WriteFailurePath()
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        window_module._write_settings({"last_model": "model-a"})
    results.check(
        "settings write failures are reported and suppressed",
        "settings save failed: forced write failure" in captured.getvalue(),
        captured.getvalue().strip(),
    )

    window_module._SETTINGS_PATH = settings_path
    for value, expected, label in (
        (None, None, "missing last_model returns None"),
        (7, None, "non-string last_model returns None"),
        ("", None, "empty last_model returns None"),
        ("   ", None, "whitespace-only last_model returns None"),
        ("  model-b  ", "  model-b  ", "nonblank last_model is returned untrimmed"),
    ):
        settings_path.write_text(
            json.dumps({"last_model": value}),
            encoding="utf-8",
        )
        actual = window_module._load_last_model()
        results.check(label, actual == expected, repr(actual))

    settings_path.write_text(
        json.dumps({"last_model": "same", "keep": "value"}),
        encoding="utf-8",
    )
    before = settings_path.read_text(encoding="utf-8")
    window_module._save_last_model("")
    window_module._save_last_model("   ")
    results.check(
        "empty and whitespace-only saves are no-ops",
        settings_path.read_text(encoding="utf-8") == before,
    )
    window_module._save_last_model("same")
    results.check(
        "saving the exact existing model is a no-op",
        settings_path.read_text(encoding="utf-8") == before,
    )
    window_module._save_last_model("  changed:model  ")
    saved = json.loads(settings_path.read_text(encoding="utf-8"))
    results.check(
        "saving a changed model preserves other keys and does not trim",
        saved == {"last_model": "  changed:model  ", "keep": "value"},
        repr(saved),
    )

    startup_cases = (
        ([], "model-a", 0, "empty model list selects index zero"),
        (["model-a", "model-b"], None, 0, "missing preference selects index zero"),
        (["model-a", "model-b"], "model-b", 1, "exact preference wins"),
        (
            ["model-a:8b", "model-a:latest"],
            "model-a:latest",
            1,
            "exact tagged preference wins over an earlier soft match",
        ),
        (
            ["other:latest", "model-a:8b", "model-a:latest"],
            "model-a:q4",
            1,
            "tag drift soft-matches the first installed base name",
        ),
        (
            ["model-a", "model-b"],
            "missing",
            0,
            "uninstalled preference falls back to index zero",
        ),
    )
    for models, preferred, expected, label in startup_cases:
        actual = window_module._pick_startup_model(models, preferred)
        results.check(label, actual == expected, str(actual))

    # Leave the production globals pointed at this test's isolated files for
    # the real ChatSidebar model-load/persistence checks below.
    window_module._SETTINGS_DIR = settings_dir
    window_module._SETTINGS_PATH = settings_path


def characterize_composer_geometry(results: Results, win: ChatSidebar) -> None:
    """Lock down the complete Phase-4 composer-geometry extraction surface."""
    print("\n[0b] Composer geometry characterization", flush=True)

    class FakeSurface:
        def __init__(self) -> None:
            self.connections: list[tuple[str, object]] = []

        def connect(self, signal: str, callback) -> int:
            self.connections.append((signal, callback))
            return len(self.connections)

    class HookOwner:
        def __init__(self) -> None:
            self.surface = None
            self.apply_calls = 0
            self._composer_layout_hooked = False
            self._surface_provider = lambda: self.surface

        def _apply_composer_height(self) -> None:
            self.apply_calls += 1

    hook_owner = HookOwner()
    ComposerGeometry._hook_composer_surface_layout(hook_owner)
    results.check(
        "surface hook retries when no surface is available",
        hook_owner._composer_layout_hooked is False and hook_owner.apply_calls == 0,
    )
    surface = FakeSurface()
    hook_owner.surface = surface
    ComposerGeometry._hook_composer_surface_layout(hook_owner)
    results.check(
        "surface hook connects one layout callback and marks itself hooked",
        hook_owner._composer_layout_hooked
        and [signal for signal, _callback in surface.connections] == ["layout"],
    )
    results.check(
        "surface hook immediately reapplies composer height",
        hook_owner.apply_calls == 1,
        str(hook_owner.apply_calls),
    )
    ComposerGeometry._hook_composer_surface_layout(hook_owner)
    results.check(
        "surface hook is idempotent after connection",
        len(surface.connections) == 1 and hook_owner.apply_calls == 1,
    )
    surface.connections[0][1](surface)
    results.check(
        "surface layout events reapply composer height",
        hook_owner.apply_calls == 2,
        str(hook_owner.apply_calls),
    )

    class LineLayout:
        def __init__(self, height: int) -> None:
            self.height = height

        def get_pixel_size(self) -> tuple[int, int]:
            return 10, self.height

    class LineInput:
        def __init__(self, *, height: int = 25, fail: bool = False) -> None:
            self.height = height
            self.fail = fail

        def create_pango_layout(self, _text: str) -> LineLayout:
            if self.fail:
                raise RuntimeError("forced layout failure")
            return LineLayout(self.height)

        def get_pixels_above_lines(self) -> int:
            return 1

        def get_pixels_below_lines(self) -> int:
            return 2

    no_line_input = type("NoLineInput", (), {"input": None})()
    results.check(
        "line height falls back to 22px without an input widget",
        ComposerGeometry._composer_line_height_px(no_line_input) == 22,
    )
    measured_line = type("MeasuredLine", (), {"input": LineInput()})()
    results.check(
        "line height includes Pango height and line spacing",
        ComposerGeometry._composer_line_height_px(measured_line) == 28,
    )
    minimum_line = type(
        "MinimumLine",
        (),
        {"input": LineInput(height=10)},
    )()
    results.check(
        "line height is clamped to an 18px minimum",
        ComposerGeometry._composer_line_height_px(minimum_line) == 18,
    )
    failed_line = type("FailedLine", (), {"input": LineInput(fail=True)})()
    results.check(
        "line height falls back to 22px when measurement fails",
        ComposerGeometry._composer_line_height_px(failed_line) == 22,
    )

    class WindowGeometry:
        def __init__(
            self,
            height: int,
            default_height: int = window_module.DEFAULT_HEIGHT,
            *,
            height_fails: bool = False,
            default_fails: bool = False,
        ) -> None:
            self.height = height
            self.default_height = default_height
            self.height_fails = height_fails
            self.default_fails = default_fails
            self._height_provider = self.get_height
            self._default_size_provider = self.get_default_size
            self._fallback_window_height = window_module.DEFAULT_HEIGHT

        def get_height(self) -> int:
            if self.height_fails:
                raise RuntimeError("forced height failure")
            return self.height

        def get_default_size(self) -> tuple[int, int]:
            if self.default_fails:
                raise RuntimeError("forced default-size failure")
            return 780, self.default_height

    results.check(
        "short current windows use the compact six-line cap",
        ComposerGeometry._composer_max_visible_lines(WindowGeometry(500))
        == window_module.COMPOSER_COMPACT_MAX_LINES,
    )
    results.check(
        "tall current windows use the normal eight-line cap",
        ComposerGeometry._composer_max_visible_lines(WindowGeometry(700))
        == window_module.COMPOSER_MAX_LINES,
    )
    results.check(
        "unallocated windows fall back to their short default height",
        ComposerGeometry._composer_max_visible_lines(WindowGeometry(0, 500))
        == window_module.COMPOSER_COMPACT_MAX_LINES,
    )
    results.check(
        "zero default-window height falls back to DEFAULT_HEIGHT",
        ComposerGeometry._composer_max_visible_lines(WindowGeometry(0, 0))
        == window_module.COMPOSER_MAX_LINES,
    )
    results.check(
        "window-height provider failures fall back to DEFAULT_HEIGHT",
        ComposerGeometry._composer_max_visible_lines(
            WindowGeometry(0, height_fails=True, default_fails=True)
        )
        == window_module.COMPOSER_MAX_LINES,
    )

    class WidthProvider:
        def __init__(self, width: int) -> None:
            self.width = width

        def get_width(self) -> int:
            return self.width

    class MeasureInput:
        def __init__(
            self,
            width: int,
            natural_height: int,
            *,
            fail: bool = False,
        ) -> None:
            self.width = width
            self.natural_height = natural_height
            self.fail = fail
            self.measured_widths: list[int] = []

        def get_width(self) -> int:
            return self.width

        def measure(self, orientation, width: int) -> tuple[int, int, int, int]:
            if self.fail:
                raise RuntimeError("forced content measurement failure")
            self.measured_widths.append(width)
            assert orientation == Gtk.Orientation.VERTICAL
            return 1, self.natural_height, -1, -1

    no_content_input = type(
        "NoContentInput",
        (),
        {"input": None, "_input_scroll": None},
    )()
    results.check(
        "content height falls back to 36px without an input widget",
        ComposerGeometry._composer_content_height_px(no_content_input) == 36,
    )
    own_width_input = MeasureInput(250, 80)
    own_width_owner = type(
        "OwnWidthOwner",
        (),
        {"input": own_width_input, "_input_scroll": WidthProvider(320)},
    )()
    results.check(
        "content measurement uses the allocated input width",
        ComposerGeometry._composer_content_height_px(own_width_owner) == 80
        and own_width_input.measured_widths == [250],
    )
    scroll_width_input = MeasureInput(0, 70)
    scroll_width_owner = type(
        "ScrollWidthOwner",
        (),
        {"input": scroll_width_input, "_input_scroll": WidthProvider(320)},
    )()
    results.check(
        "content measurement falls back to the scroller width",
        ComposerGeometry._composer_content_height_px(scroll_width_owner) == 70
        and scroll_width_input.measured_widths == [320],
    )
    default_width_input = MeasureInput(0, 0)
    default_width_owner = type(
        "DefaultWidthOwner",
        (),
        {"input": default_width_input, "_input_scroll": WidthProvider(0)},
    )()
    results.check(
        "content measurement falls back to 400px and floors natural height at one",
        ComposerGeometry._composer_content_height_px(default_width_owner) == 1
        and default_width_input.measured_widths == [400],
    )
    failed_content_owner = type(
        "FailedContentOwner",
        (),
        {
            "input": MeasureInput(250, 80, fail=True),
            "_input_scroll": WidthProvider(320),
        },
    )()
    results.check(
        "content height falls back to 36px when measurement fails",
        ComposerGeometry._composer_content_height_px(failed_content_owner) == 36,
    )

    class MarginInput:
        def get_top_margin(self) -> int:
            return 8

        def get_bottom_margin(self) -> int:
            return 8

    class SizeTarget:
        def __init__(self) -> None:
            self.requests: list[tuple[int, int]] = []

        def set_size_request(self, width: int, height: int) -> None:
            self.requests.append((width, height))

    class GeometryScroll(SizeTarget):
        def __init__(self) -> None:
            super().__init__()
            self.policies: list[tuple[Gtk.PolicyType, Gtk.PolicyType]] = []
            self.min_heights: list[int] = []
            self.max_heights: list[int] = []
            self.parent = SizeTarget()

        def set_policy(self, horizontal, vertical) -> None:
            self.policies.append((horizontal, vertical))

        def set_min_content_height(self, height: int) -> None:
            self.min_heights.append(height)

        def set_max_content_height(self, height: int) -> None:
            self.max_heights.append(height)

        def get_parent(self) -> SizeTarget:
            return self.parent

    class ApplyOwner:
        def __init__(self, content_height: int) -> None:
            self.input = MarginInput()
            self._input_scroll = GeometryScroll()
            self.content_height = content_height
            self.sync_calls: list[tuple[int, int]] = []

        def _composer_line_height_px(self) -> int:
            return 20

        def _composer_max_visible_lines(self) -> int:
            return 6

        def _composer_content_height_px(self) -> int:
            return self.content_height

        def _align_callback(
            self,
            *,
            content_h: int,
            min_h: int,
        ) -> None:
            self.sync_calls.append((content_h, min_h))

    missing_geometry = type(
        "MissingGeometry",
        (),
        {"input": None, "_input_scroll": None},
    )()
    ComposerGeometry._apply_composer_height(missing_geometry)
    results.check(
        "height application is a no-op until both widgets exist",
        missing_geometry.input is None and missing_geometry._input_scroll is None,
    )

    short_owner = ApplyOwner(20)
    ComposerGeometry._apply_composer_height(short_owner)
    short_scroll = short_owner._input_scroll
    results.check(
        "short content uses the 36px minimum without a scrollbar",
        short_scroll.policies
        == [(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)]
        and short_scroll.min_heights == [36]
        and short_scroll.max_heights == [136]
        and short_scroll.requests == [(-1, 36)]
        and short_scroll.parent.requests == [(-1, 36)]
        and short_owner.sync_calls == [(20, 36)],
    )

    medium_owner = ApplyOwner(80)
    ComposerGeometry._apply_composer_height(medium_owner)
    results.check(
        "medium content uses its natural height without a scrollbar",
        medium_owner._input_scroll.min_heights == [80]
        and medium_owner._input_scroll.policies
        == [(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)],
    )

    tall_owner = ApplyOwner(200)
    ComposerGeometry._apply_composer_height(tall_owner)
    results.check(
        "over-cap content is clamped and enables automatic vertical scrolling",
        tall_owner._input_scroll.min_heights == [136]
        and tall_owner._input_scroll.max_heights == [136]
        and tall_owner._input_scroll.policies
        == [(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)]
        and tall_owner.sync_calls == [(200, 36)],
    )

    class FakeLabel:
        def __init__(self) -> None:
            self.visible = False
            self.text = ""
            self.classes: set[str] = set()
            self.tooltip = ""

        def set_visible(self, visible: bool) -> None:
            self.visible = visible

        def set_text(self, text: str) -> None:
            self.text = text

        def add_css_class(self, name: str) -> None:
            self.classes.add(name)

        def remove_css_class(self, name: str) -> None:
            self.classes.discard(name)

        def set_tooltip_text(self, text: str) -> None:
            self.tooltip = text

    label = FakeLabel()
    counter_owner = type(
        "CounterOwner",
        (),
        {"_composer_char_label": label},
    )()
    threshold = int(
        window_module.COMPOSER_CHAR_LIMIT
        * window_module.COMPOSER_COUNTER_SHOW_RATIO
    )
    ComposerGeometry._update_composer_char_counter(counter_owner, threshold - 1)
    results.check(
        "character counter stays hidden below the warning threshold",
        label.visible is False,
    )
    ComposerGeometry._update_composer_char_counter(counter_owner, threshold)
    results.check(
        "character counter appears at the threshold with normal styling",
        label.visible
        and label.text
        == f"{threshold:,} / {window_module.COMPOSER_CHAR_LIMIT:,}"
        and "warning" not in label.classes
        and label.tooltip
        == (
            "Hard safety limit is "
            f"{window_module.COMPOSER_CHAR_LIMIT:,} characters"
        ),
    )
    ComposerGeometry._update_composer_char_counter(
        counter_owner,
        window_module.COMPOSER_CHAR_LIMIT,
    )
    results.check(
        "character counter warns at the hard cap",
        label.text
        == (
            f"{window_module.COMPOSER_CHAR_LIMIT:,} / "
            f"{window_module.COMPOSER_CHAR_LIMIT:,}"
        )
        and "warning" in label.classes
        and label.tooltip == "Character safety limit reached",
    )

    class InsertBuffer:
        def __init__(self, count: int) -> None:
            self.count = count
            self.stopped: list[str] = []
            self.inserted: list[tuple[object, str]] = []

        def get_char_count(self) -> int:
            return self.count

        def stop_emission_by_name(self, name: str) -> None:
            self.stopped.append(name)

        def insert(self, location, text: str) -> None:
            self.inserted.append((location, text))
            self.count += len(text)

    class InsertOwner:
        def __init__(self, truncating: bool = False) -> None:
            self._composer_truncating = truncating
            self.counter_updates: list[int] = []

        def _update_composer_char_counter(self, count: int) -> None:
            self.counter_updates.append(count)

    guarded_owner = InsertOwner(truncating=True)
    guarded_buffer = InsertBuffer(10)
    ComposerGeometry._on_composer_insert_text(
        guarded_owner,
        guarded_buffer,
        "loc",
        "ignored",
        7,
    )
    ComposerGeometry._on_composer_insert_text(
        InsertOwner(),
        guarded_buffer,
        "loc",
        "",
        0,
    )
    results.check(
        "insert handler ignores reentrant and empty insertions",
        guarded_buffer.stopped == [] and guarded_buffer.inserted == [],
    )

    full_owner = InsertOwner()
    full_buffer = InsertBuffer(window_module.COMPOSER_CHAR_LIMIT)
    ComposerGeometry._on_composer_insert_text(
        full_owner,
        full_buffer,
        "loc",
        "x",
        1,
    )
    results.check(
        "insertions at the hard cap are stopped and refresh the counter",
        full_buffer.stopped == ["insert-text"]
        and full_buffer.inserted == []
        and full_owner.counter_updates
        == [window_module.COMPOSER_CHAR_LIMIT],
    )

    paste_owner = InsertOwner()
    paste_buffer = InsertBuffer(window_module.COMPOSER_CHAR_LIMIT - 3)
    ComposerGeometry._on_composer_insert_text(
        paste_owner,
        paste_buffer,
        "loc",
        "abcdef",
        6,
    )
    results.check(
        "oversized pastes are clamped and the reentrancy guard is restored",
        paste_buffer.stopped == ["insert-text"]
        and paste_buffer.inserted == [("loc", "abc")]
        and paste_owner._composer_truncating is False,
    )

    fitting_owner = InsertOwner()
    fitting_buffer = InsertBuffer(10)
    ComposerGeometry._on_composer_insert_text(
        fitting_owner,
        fitting_buffer,
        "loc",
        "fits",
        4,
    )
    results.check(
        "in-range insertions are left to the default buffer handler",
        fitting_buffer.stopped == [] and fitting_buffer.inserted == [],
    )

    class ChangedBuffer:
        def __init__(self, text: str) -> None:
            self.text = text
            self.deletions: list[tuple[int, int]] = []

        def get_char_count(self) -> int:
            return len(self.text)

        def get_iter_at_offset(self, offset: int) -> int:
            return offset

        def get_end_iter(self) -> int:
            return len(self.text)

        def delete(self, start: int, end: int) -> None:
            self.deletions.append((start, end))
            self.text = self.text[:start] + self.text[end:]

        def get_start_iter(self) -> int:
            return 0

        def get_text(self, start: int, end: int, _include_hidden: bool) -> str:
            return self.text[start:end]

    class VisibilityTarget:
        def __init__(self) -> None:
            self.visible = None

        def set_visible(self, visible: bool) -> None:
            self.visible = visible

    class ChangedOwner:
        def __init__(self, truncating: bool = False) -> None:
            self._composer_truncating = truncating
            self._placeholder = VisibilityTarget()
            self.counter_updates: list[int] = []
            self.apply_calls = 0
            self.idle_align_calls = 0

        def _update_composer_char_counter(self, count: int) -> None:
            self.counter_updates.append(count)

        def _apply_composer_height(self) -> None:
            self.apply_calls += 1

        def _align_callback(self) -> bool:
            self.idle_align_calls += 1
            return False

    guarded_changed_owner = ChangedOwner(truncating=True)
    guarded_changed_buffer = ChangedBuffer("ignored")
    ComposerGeometry._on_buffer_changed(
        guarded_changed_owner,
        guarded_changed_buffer,
    )
    results.check(
        "changed handler ignores reentrant buffer mutations",
        guarded_changed_owner.counter_updates == []
        and guarded_changed_owner.apply_calls == 0,
    )

    over_limit_owner = ChangedOwner()
    over_limit_buffer = ChangedBuffer(
        "x" * (window_module.COMPOSER_CHAR_LIMIT + 5)
    )
    ComposerGeometry._on_buffer_changed(over_limit_owner, over_limit_buffer)
    pump(0.05)
    results.check(
        "changed handler deletes text beyond the hard cap and restores its guard",
        len(over_limit_buffer.text) == window_module.COMPOSER_CHAR_LIMIT
        and over_limit_buffer.deletions
        == [
            (
                window_module.COMPOSER_CHAR_LIMIT,
                window_module.COMPOSER_CHAR_LIMIT + 5,
            )
        ]
        and over_limit_owner._composer_truncating is False,
    )
    results.check(
        "changed handler updates placeholder, counter, height, and idle alignment",
        over_limit_owner._placeholder.visible is False
        and over_limit_owner.counter_updates
        == [window_module.COMPOSER_CHAR_LIMIT]
        and over_limit_owner.apply_calls == 1
        and over_limit_owner.idle_align_calls == 1,
    )

    empty_owner = ChangedOwner()
    ComposerGeometry._on_buffer_changed(empty_owner, ChangedBuffer(""))
    pump(0.05)
    results.check(
        "empty changed buffers show the placeholder and report zero characters",
        empty_owner._placeholder.visible is True
        and empty_owner.counter_updates == [0]
        and empty_owner.apply_calls == 1
        and empty_owner.idle_align_calls == 1,
    )

    results.check(
        "composer controller owns its private flags instead of the window",
        win._composer_geometry is not None
        and win._composer_geometry._composer_truncating is False
        and win._composer_geometry._composer_layout_hooked is True
        and not hasattr(win, "_composer_truncating")
        and not hasattr(win, "_composer_layout_hooked"),
    )
    results.check(
        "realized composer connects its surface-layout hook",
        win._composer_geometry is not None
        and win._composer_geometry._composer_layout_hooked is True,
    )
    initial_request = win._input_scroll.get_size_request()
    results.check(
        "construction applies an initial composer height",
        win._input_scroll.get_min_content_height() >= 36
        and win._input_scroll.get_max_content_height()
        >= win._input_scroll.get_min_content_height()
        and initial_request[1] >= 36,
        str(initial_request),
    )

    map_calls: list[str] = []
    original_apply_height = win._composer_geometry._apply_composer_height
    win._composer_geometry._apply_composer_height = (
        lambda *_args: map_calls.append("map")
    )
    map_error = ""
    try:
        win.emit("map")
    except Exception as exc:  # noqa: BLE001
        map_error = repr(exc)
    finally:
        win._composer_geometry._apply_composer_height = original_apply_height
    results.check(
        "window map signal is wired to composer-height reapplication",
        map_calls == ["map"] and not map_error,
        map_error or repr(map_calls),
    )

    real_buffer = win.input.get_buffer()
    real_buffer.set_text("")
    pump(0.05)
    results.check(
        "real changed signal shows the placeholder for an empty buffer",
        win._placeholder.get_visible() is True,
    )
    real_buffer.set_text("hello")
    pump(0.05)
    results.check(
        "real changed signal hides the placeholder for nonempty text",
        win._placeholder.get_visible() is False,
    )

    real_buffer.set_text("x" * window_module.COMPOSER_CHAR_LIMIT)
    pump(0.05)
    results.check(
        "real changed signal presents the hard-cap counter warning",
        real_buffer.get_char_count() == window_module.COMPOSER_CHAR_LIMIT
        and win._composer_char_label.get_visible()
        and win._composer_char_label.has_css_class("warning"),
    )

    real_buffer.set_text("x" * (window_module.COMPOSER_CHAR_LIMIT - 2))
    end = real_buffer.get_end_iter()
    real_buffer.insert(end, "wxyz")
    pump(0.05)
    real_text = real_buffer.get_text(
        real_buffer.get_start_iter(),
        real_buffer.get_end_iter(),
        False,
    )
    results.check(
        "real insert-text signal clamps an oversized paste at the hard cap",
        real_buffer.get_char_count() == window_module.COMPOSER_CHAR_LIMIT
        and real_text.endswith("wx"),
    )

    real_buffer.set_text("")
    pump(0.05)
    results.check(
        "composer test restores the real buffer to its empty startup state",
        real_buffer.get_char_count() == 0
        and win._placeholder.get_visible() is True
        and win._composer_char_label.get_visible() is False,
    )


def characterize_export(results: Results, win: ChatSidebar, tmp: Path) -> None:
    """Lock down the complete Phase-6 export extraction surface."""
    print("\n[0c] Export characterization", flush=True)

    class Conversation:
        def __init__(self, title: str) -> None:
            self.title = title

    class Message:
        def __init__(self, role: str, content: str) -> None:
            self.role = role
            self.content = content

    class TitleStore:
        def __init__(
            self,
            *,
            title: str = "",
            messages: list[Message] | None = None,
            fail: bool = False,
        ) -> None:
            self.title = title
            self.messages = messages or []
            self.fail = fail

        def get_conversation(self, _conversation_id: str):
            if self.fail:
                raise RuntimeError("forced title-store failure")
            return Conversation(self.title)

        def list_messages(self, _conversation_id: str) -> list[Message]:
            return self.messages

    stored_title_owner = type(
        "StoredTitleOwner",
        (),
        {
            "_store": TitleStore(title="  Stored title  "),
            "_conversation_id": "other",
            "_messages": [],
        },
    )()
    results.check(
        "display title prefers and trims the stored conversation title",
        ConversationLifecycleController.conversation_display_title(
            stored_title_owner, "conv"
        )
        == "Stored title",
    )

    excerpt = "x" * 90 + "\nignored second line"
    stored_excerpt_owner = type(
        "StoredExcerptOwner",
        (),
        {
            "_store": TitleStore(
                messages=[
                    Message("assistant", "ignored"),
                    Message("user", "   "),
                    Message("user", f"  {excerpt}  "),
                ]
            ),
            "_conversation_id": "other",
            "_messages": [],
        },
    )()
    results.check(
        "display title falls back to the first stored user-message line at 80 chars",
        ConversationLifecycleController.conversation_display_title(
            stored_excerpt_owner, "conv"
        )
        == "x" * 80,
    )

    active_fallback_owner = type(
        "ActiveFallbackOwner",
        (),
        {
            "_store": TitleStore(fail=True),
            "_conversation_id": "active",
            "_messages": [
                {"role": "assistant", "content": "ignored"},
                {"role": "user", "content": "  Active fallback\nsecond line  "},
            ],
        },
    )()
    results.check(
        "display title falls back to the active in-memory user message",
        ConversationLifecycleController.conversation_display_title(
            active_fallback_owner, "active"
        )
        == "Active fallback",
    )
    results.check(
        "display title uses the generic fallback for missing inactive conversations",
        ConversationLifecycleController.conversation_display_title(
            active_fallback_owner, "missing"
        )
        == "this chat",
    )

    class BasenameOwner:
        def __init__(self, title: str) -> None:
            self._title_provider = lambda _conversation_id: title

    results.check(
        "export basename replaces punctuation and collapses whitespace",
        ConversationExporter._safe_export_basename(
            BasenameOwner("  Alpha/Beta: test?  "),
            "conv",
        )
        == "chickenbutt-Alpha-Beta--test",
    )
    results.check(
        "export basename maps generic and punctuation-only titles to chat",
        ConversationExporter._safe_export_basename(
            BasenameOwner("this chat"),
            "conv",
        )
        == "chickenbutt-chat"
        and ConversationExporter._safe_export_basename(
            BasenameOwner("///"),
            "conv",
        )
        == "chickenbutt-chat",
    )
    long_basename = ConversationExporter._safe_export_basename(
        BasenameOwner("a" * 60),
        "conv",
    )
    results.check(
        "export basename truncates the sanitized title to 48 characters",
        long_basename == f"chickenbutt-{'a' * 48}",
    )

    class FakeStore:
        def __init__(
            self,
            *,
            json_payload: dict | None = None,
            markdown_body: str | None = None,
        ) -> None:
            self.json_payload = json_payload
            self.markdown_body = markdown_body
            self.calls: list[tuple[str, str]] = []

        def export_dict(self, conversation_id: str) -> dict | None:
            self.calls.append(("json", conversation_id))
            return self.json_payload

        def export_markdown(self, conversation_id: str) -> str | None:
            self.calls.append(("md", conversation_id))
            return self.markdown_body

    class FakeFile:
        def __init__(self, path: str | None) -> None:
            self.path = path

        def get_path(self) -> str | None:
            return self.path

    class FakeSaveResult:
        def __init__(
            self,
            *,
            file: FakeFile | None = None,
            error: GLib.Error | None = None,
        ) -> None:
            self.file = file
            self.error = error

    class FakeFileFilter:
        def __init__(self) -> None:
            self.name = ""
            self.patterns: list[str] = []
            self.mime_types: list[str] = []

        def set_name(self, name: str) -> None:
            self.name = name

        def add_pattern(self, pattern: str) -> None:
            self.patterns.append(pattern)

        def add_mime_type(self, mime_type: str) -> None:
            self.mime_types.append(mime_type)

    class FakeListStore(list):
        @classmethod
        def new(cls, _item_type):
            return cls()

        def append(self, item) -> None:
            super().append(item)

    class FakeFileDialog:
        instances: list["FakeFileDialog"] = []

        def __init__(self) -> None:
            self.title = ""
            self.initial_name = ""
            self.filters = None
            self.default_filter = None
            self.parent = None
            self.cancellable = "unset"
            self.callback = None
            self.__class__.instances.append(self)

        def set_title(self, title: str) -> None:
            self.title = title

        def set_initial_name(self, name: str) -> None:
            self.initial_name = name

        def set_filters(self, filters) -> None:
            self.filters = filters

        def set_default_filter(self, filt) -> None:
            self.default_filter = filt

        def save(self, parent, cancellable, callback) -> None:
            self.parent = parent
            self.cancellable = cancellable
            self.callback = callback

        def save_finish(self, result: FakeSaveResult) -> FakeFile | None:
            if result.error is not None:
                raise result.error
            return result.file

    class FakeMessageDialog:
        instances: list["FakeMessageDialog"] = []

        def __init__(self, *, transient_for, heading: str, body: str) -> None:
            self.transient_for = transient_for
            self.heading = heading
            self.body = body
            self.responses: list[tuple[str, str]] = []
            self.presented = False
            self.__class__.instances.append(self)

        def add_response(self, response_id: str, label: str) -> None:
            self.responses.append((response_id, label))

        def present(self) -> None:
            self.presented = True

    class FakeGtk:
        FileDialog = FakeFileDialog
        FileFilter = FakeFileFilter

    class FakeGio:
        ListStore = FakeListStore
        IOErrorEnum = Gio.IOErrorEnum
        io_error_quark = staticmethod(Gio.io_error_quark)

    class FakeAdw:
        MessageDialog = FakeMessageDialog

    class ExportOwner:
        def __init__(self, store: FakeStore) -> None:
            self._store = store
            self._transient_parent = self

        def _safe_export_basename(self, _conversation_id: str) -> str:
            return "chickenbutt-fixture"

    def start_export(fmt, store: FakeStore):
        owner = ExportOwner(store)
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            ConversationExporter.export_conversation(owner, "conv-id", fmt)
        dialog = (
            FakeFileDialog.instances[-1]
            if FakeFileDialog.instances
            and FakeFileDialog.instances[-1].parent is owner
            else None
        )
        return owner, dialog, stdout.getvalue()

    original_gtk = export_module.Gtk
    original_gio = export_module.Gio
    original_adw = export_module.Adw
    export_module.Gtk = FakeGtk
    export_module.Gio = FakeGio
    export_module.Adw = FakeAdw
    try:
        json_store = FakeStore(json_payload={"title": "café", "mark": "✓"})
        json_owner, json_dialog, json_output = start_export(".JSON", json_store)
        json_filter = json_dialog.default_filter
        results.check(
            "JSON format normalization configures its filename, filter, and dialog",
            json_store.calls == [("json", "conv-id")]
            and json_dialog.title == "Export chat"
            and json_dialog.initial_name == "chickenbutt-fixture.json"
            and json_filter.name == "JSON"
            and json_filter.patterns == ["*.json"]
            and json_filter.mime_types == ["application/json"]
            and json_dialog.filters == [json_filter]
            and json_dialog.parent is json_owner
            and json_dialog.cancellable is None
            and callable(json_dialog.callback)
            and json_output == "",
        )

        markdown_store = FakeStore(markdown_body="# Héllo ✓\n")
        markdown_owner, markdown_dialog, _ = start_export(
            "markdown",
            markdown_store,
        )
        markdown_filter = markdown_dialog.default_filter
        results.check(
            "Markdown alias configures its filename, filter, and dialog",
            markdown_store.calls == [("md", "conv-id")]
            and markdown_dialog.initial_name == "chickenbutt-fixture.md"
            and markdown_filter.name == "Markdown"
            and markdown_filter.patterns == ["*.md"]
            and markdown_filter.mime_types == ["text/markdown"],
        )

        unsupported_store = FakeStore(markdown_body="fallback\n")
        _, unsupported_dialog, _ = start_export("pdf", unsupported_store)
        none_store = FakeStore(markdown_body="default\n")
        _, none_dialog, _ = start_export(None, none_store)
        whitespace_store = FakeStore(markdown_body="whitespace fallback\n")
        _, whitespace_dialog, _ = start_export(" JSON ", whitespace_store)
        results.check(
            "unsupported, empty, and whitespace-padded formats fall back to Markdown",
            unsupported_store.calls == [("md", "conv-id")]
            and unsupported_dialog.initial_name.endswith(".md")
            and none_store.calls == [("md", "conv-id")]
            and none_dialog.initial_name.endswith(".md")
            and whitespace_store.calls == [("md", "conv-id")]
            and whitespace_dialog.initial_name.endswith(".md"),
        )

        dialog_count = len(FakeFileDialog.instances)
        missing_json = FakeStore(json_payload=None)
        missing_md = FakeStore(markdown_body=None)
        missing_output = io.StringIO()
        with contextlib.redirect_stdout(missing_output):
            ConversationExporter.export_conversation(
                ExportOwner(missing_json),
                "missing-json",
                "json",
            )
            ConversationExporter.export_conversation(
                ExportOwner(missing_md),
                "missing-md",
                "md",
            )
        results.check(
            "missing conversations log and return before opening a dialog",
            missing_json.calls == [("json", "missing-json")]
            and missing_md.calls == [("md", "missing-md")]
            and len(FakeFileDialog.instances) == dialog_count
            and missing_output.getvalue().count(
                "export: conversation not found\n"
            )
            == 2,
        )

        cancelled = GLib.Error.new_literal(
            Gio.io_error_quark(),
            "cancelled",
            Gio.IOErrorEnum.CANCELLED,
        )
        callback_output = io.StringIO()
        with contextlib.redirect_stdout(callback_output):
            markdown_dialog.callback(
                markdown_dialog,
                FakeSaveResult(error=cancelled),
            )
        results.check(
            "dialog cancellation is a silent no-op",
            callback_output.getvalue() == ""
            and FakeMessageDialog.instances == [],
        )

        dialog_error = GLib.Error.new_literal(
            Gio.io_error_quark(),
            "forced dialog failure",
            Gio.IOErrorEnum.FAILED,
        )
        callback_output = io.StringIO()
        with contextlib.redirect_stdout(callback_output):
            markdown_dialog.callback(
                markdown_dialog,
                FakeSaveResult(error=dialog_error),
            )
        results.check(
            "non-cancellation dialog errors are logged without a write attempt",
            callback_output.getvalue().startswith("export dialog:")
            and "forced dialog failure" in callback_output.getvalue()
            and FakeMessageDialog.instances == [],
        )

        callback_output = io.StringIO()
        with contextlib.redirect_stdout(callback_output):
            markdown_dialog.callback(
                markdown_dialog,
                FakeSaveResult(file=None),
            )
        results.check(
            "a None file result is a silent no-op",
            callback_output.getvalue() == "",
        )

        callback_output = io.StringIO()
        with contextlib.redirect_stdout(callback_output):
            markdown_dialog.callback(
                markdown_dialog,
                FakeSaveResult(file=FakeFile(None)),
            )
        results.check(
            "a file without a local path logs and returns",
            callback_output.getvalue() == "export: no path\n",
        )

        json_path = tmp / "phase5-export.json"
        callback_output = io.StringIO()
        with contextlib.redirect_stdout(callback_output):
            json_dialog.callback(
                json_dialog,
                FakeSaveResult(file=FakeFile(str(json_path))),
            )
        results.check(
            "successful JSON export writes indented UTF-8 with a trailing newline",
            json_path.read_text(encoding="utf-8")
            == '{\n  "title": "café",\n  "mark": "✓"\n}\n'
            and callback_output.getvalue()
            == f"Exported json → {json_path}\n",
        )

        markdown_path = tmp / "phase5-export.md"
        callback_output = io.StringIO()
        with contextlib.redirect_stdout(callback_output):
            markdown_dialog.callback(
                markdown_dialog,
                FakeSaveResult(file=FakeFile(str(markdown_path))),
            )
        results.check(
            "successful Markdown export writes its UTF-8 body unchanged",
            markdown_path.read_text(encoding="utf-8") == "# Héllo ✓\n"
            and callback_output.getvalue()
            == f"Exported md → {markdown_path}\n",
        )

        callback_output = io.StringIO()
        with contextlib.redirect_stdout(callback_output):
            markdown_dialog.callback(
                markdown_dialog,
                FakeSaveResult(file=FakeFile(str(tmp))),
            )
        error_dialog = FakeMessageDialog.instances[-1]
        results.check(
            "write failures are logged and shown in a user-visible error dialog",
            "export write failed:" in callback_output.getvalue()
            and error_dialog.transient_for is markdown_owner
            and error_dialog.heading == "Export failed"
            and error_dialog.body
            and error_dialog.responses == [("ok", "OK")]
            and error_dialog.presented is True,
        )
    finally:
        export_module.Gtk = original_gtk
        export_module.Gio = original_gio
        export_module.Adw = original_adw

    delegated: list[tuple[str, str]] = []
    original_export = win._conversation_exporter.export_conversation
    win._conversation_exporter.export_conversation = (
        lambda conversation_id, fmt: delegated.append((conversation_id, fmt))
    )
    try:
        win.export_conversation("delegated-conversation", "json")
    finally:
        win._conversation_exporter.export_conversation = original_export
    results.check(
        "window export entrypoint remains a thin stable delegator",
        delegated == [("delegated-conversation", "json")],
    )
    results.check(
        "window exporter receives its store, transient parent, and title provider",
        win._conversation_exporter._store is win._store
        and win._conversation_exporter._transient_parent is win
        and getattr(win._conversation_exporter._title_provider, "__self__", None)
        is win._conversation,
    )
    rebound = ConversationExporter(
        store=win._store,
        transient_parent=win,
        title_provider=lambda _conversation_id: "before",
    )
    rebound.set_title_provider(lambda _conversation_id: "after")
    results.check(
        "title provider can be rebound for the Phase 22 ownership migration",
        rebound._safe_export_basename("conv") == "chickenbutt-after",
    )
    projection_title = ConversationExporter(
        store=win._store,
        transient_parent=win,
        title_provider=lambda _conversation_id: "before",
    )
    projection_title.set_title_provider(win._conversation.conversation_display_title)
    previous_id = win._conversation.conversation_id
    previous_messages = list(win._conversation.messages)
    win._conversation.conversation_id = "export-active"
    win._conversation.messages = [
        {"role": "user", "content": "  Projection fallback title\nignored  "}
    ]
    results.check(
        "rebound export title provider reads the migrated conversation projection",
        projection_title._safe_export_basename("export-active")
        == "chickenbutt-Projection-fallback-title",
    )
    win._conversation.conversation_id = previous_id
    win._conversation.messages = previous_messages


class _HealthWidget:
    def __init__(self, *, child=None) -> None:
        self.visible: bool | None = None
        self.sensitive: bool | None = None
        self.text: str | None = None
        self.label: str | None = None
        self.child = child
        self.css_classes: set[str] = set()

    def set_visible(self, visible: bool) -> None:
        self.visible = visible

    def set_sensitive(self, sensitive: bool) -> None:
        self.sensitive = sensitive

    def set_text(self, text: str) -> None:
        self.text = text

    def set_label(self, label: str) -> None:
        self.label = label

    def get_child(self):
        return self.child

    def add_css_class(self, css_class: str) -> None:
        self.css_classes.add(css_class)

    def remove_css_class(self, css_class: str) -> None:
        self.css_classes.discard(css_class)


class _HealthItem:
    def __init__(self, value: str) -> None:
        self.value = value

    def get_string(self) -> str:
        return self.value


class _HealthModel:
    def __init__(self, items) -> None:
        self.items = [
            None if item is None else _HealthItem(item)
            for item in items
        ]

    def get_n_items(self) -> int:
        return len(self.items)

    def get_item(self, index: int):
        return self.items[index]


class _HealthCombo(_HealthWidget):
    def __init__(self, items=()) -> None:
        super().__init__()
        self.model = _HealthModel(items)
        self.selected = 0
        self.selection_history: list[int] = []

    def get_model(self):
        return self.model

    def set_model(self, model) -> None:
        self.model = model
        self.selected = 0

    def set_selected(self, index: int) -> None:
        self.selected = index
        self.selection_history.append(index)

    def get_selected_item(self):
        if self.model is None:
            return None
        if self.selected < 0 or self.selected >= self.model.get_n_items():
            return None
        return self.model.get_item(self.selected)


class _HealthStore:
    def __init__(self, conversation=None, *, error: Exception | None = None) -> None:
        self.conversation = conversation
        self.error = error
        self.calls: list[str] = []

    def get_conversation(self, conversation_id: str):
        self.calls.append(conversation_id)
        if self.error is not None:
            raise self.error
        return self.conversation


class _HealthHarness(HealthProbeController):
    def __init__(self, model_items=()) -> None:
        self.client = object()
        self._current_model: str | None = None
        self._loading = False
        self._failed = False
        self._message_list: list[dict] = []
        self._active_conversation_id: str | None = None
        self._conversation_store = _HealthStore()

        health_child = _HealthWidget()
        health_banner: _HealthWidget | None = _HealthWidget(
            child=health_child
        )
        health_title: _HealthWidget | None = _HealthWidget()
        health_detail: _HealthWidget | None = _HealthWidget()
        health_action: _HealthWidget | None = _HealthWidget()
        refresh_control: _HealthWidget | None = _HealthWidget()
        model_selector: _HealthCombo | None = _HealthCombo(model_items)
        self.send_btn: _HealthWidget | None = _HealthWidget()
        self.input: _HealthWidget | None = _HealthWidget()

        self.statuses: list[str] = []
        self.control_sensitivity: list[bool] = []
        self.load_requests: list[tuple[str, bool]] = []
        self.overlay_hides = 0

        super().__init__(
            client=self.client,
            model_selector=model_selector,
            refresh_control=refresh_control,
            health_banner=health_banner,
            health_title=health_title,
            health_detail=health_detail,
            health_action=health_action,
            get_current_model=lambda: self._model,
            set_current_model=lambda model: setattr(self, "_model", model),
            is_loading=lambda: self._loading_model,
            is_load_failed=lambda: self._load_failed,
            set_load_failed=lambda failed: setattr(self, "_load_failed", failed),
            begin_load=lambda model, greet: self._begin_model_load(
                model, greet=greet
            ),
            messages_empty=lambda: not self._messages,
            active_conversation_model=self._active_conversation_model,
            settings_fallback=lambda: window_module._load_last_model(),
            set_status=lambda text: self._set_status(text),
            hide_load_overlay=lambda: self._hide_load_overlay(),
            set_shared_sensitivity=lambda enabled: (
                self._set_load_controls_sensitive(enabled)
            ),
            set_send_sensitivity=lambda enabled: (
                self.send_btn.set_sensitive(enabled)
                if self.send_btn is not None
                else None
            ),
            set_input_sensitivity=lambda enabled: (
                self.input.set_sensitive(enabled) if self.input is not None else None
            ),
        )
        # Characterization cases distinguish a strict refresh no-op from
        # publishing the controller's normal initial checking state.
        self._health = None

    @property
    def _model(self) -> str | None:
        return self._current_model

    @_model.setter
    def _model(self, model: str | None) -> None:
        self._current_model = model

    @property
    def _loading_model(self) -> bool:
        return self._loading

    @_loading_model.setter
    def _loading_model(self, loading: bool) -> None:
        self._loading = loading

    @property
    def _load_failed(self) -> bool:
        return self._failed

    @_load_failed.setter
    def _load_failed(self, failed: bool) -> None:
        self._failed = failed

    @property
    def _messages(self) -> list[dict]:
        return self._message_list

    @_messages.setter
    def _messages(self, messages: list[dict]) -> None:
        self._message_list = messages

    @property
    def _conversation_id(self) -> str | None:
        return self._active_conversation_id

    @_conversation_id.setter
    def _conversation_id(self, conversation_id: str | None) -> None:
        self._active_conversation_id = conversation_id

    @property
    def _store(self) -> _HealthStore:
        return self._conversation_store

    @_store.setter
    def _store(self, store: _HealthStore) -> None:
        self._conversation_store = store

    def _active_conversation_model(self) -> str | None:
        if not self._conversation_id:
            return None
        conversation = self._store.get_conversation(self._conversation_id)
        return conversation.model if conversation is not None else None

    def _set_status(self, text: str) -> None:
        self.statuses.append(text)

    def _set_load_controls_sensitive(self, enabled: bool) -> None:
        self.control_sensitivity.append(enabled)

    def _begin_model_load(self, model: str, *, greet: bool = False) -> None:
        self.load_requests.append((model, greet))

    def _hide_load_overlay(self) -> None:
        self.overlay_hides += 1


def _string_list_values(model) -> list[str]:
    return [
        model.get_item(index).get_string()
        for index in range(model.get_n_items())
    ]


def characterize_health_probe(results: Results) -> None:
    """Lock down all Phase-7 health/probe branches before extraction."""
    print("\n[0c] Health/probe characterization", flush=True)

    # _apply_health: state ownership, visibility, content, style, and action.
    state = HealthState(
        kind=HealthKind.API_ERROR,
        title="API title",
        detail="API detail",
        action_label="Retry",
        action="refresh",
        model="model-a",
    )
    no_banner = _HealthHarness()
    no_banner._health_banner = None
    no_banner._apply_health(state)
    results.check(
        "health state is stored even when no banner exists",
        no_banner._health is state,
    )

    healthy = _HealthHarness()
    healthy._health_title.text = "unchanged"
    healthy._health_action_id = "unchanged-action"
    healthy._health_banner.child.css_classes.add("warn")
    healthy._apply_health(
        HealthState(HealthKind.OK, "Ollama is ready", "Connected")
    )
    results.check(
        "OK health hides the banner and returns before rewriting hidden state",
        healthy._health_banner.visible is False
        and healthy._health_title.text == "unchanged"
        and healthy._health_action_id == "unchanged-action"
        and healthy._health_banner.child.css_classes == {"warn"},
    )

    checking = _HealthHarness()
    checking._health_action_id = "stale"
    checking._health_action_model = "stale-model"
    checking._health_banner.child.css_classes.update(("error", "warn"))
    checking._apply_health(
        HealthState(HealthKind.CHECKING, "Checking", "Please wait")
    )
    results.check(
        "checking health remains visible and clears stale style/action state",
        checking._health_banner.visible is True
        and checking._health_title.text == "Checking"
        and checking._health_detail.text == "Please wait"
        and checking._health_banner.child.css_classes == set()
        and checking._health_action_btn.visible is False
        and checking._health_action_id is None
        and checking._health_action_model is None,
    )

    for kind in (
        HealthKind.OOM,
        HealthKind.STREAM_LOST,
        HealthKind.API_ERROR,
        HealthKind.MODEL_LOAD_FAILED,
    ):
        owner = _HealthHarness()
        owner._health_banner.child.css_classes.add("warn")
        owner._apply_health(
            HealthState(
                kind,
                f"{kind.value} title",
                "detail",
                action_label="Retry",
                action="retry_load",
                model="model-b",
            )
        )
        results.check(
            f"{kind.value} health uses error styling and exposes its action",
            owner._health_banner.child.css_classes == {"error"}
            and owner._health_action_btn.visible is True
            and owner._health_action_btn.label == "Retry"
            and owner._health_action_id == "retry_load"
            and owner._health_action_model == "model-b",
        )

    for kind in (
        HealthKind.NOT_RUNNING,
        HealthKind.NOT_INSTALLED,
        HealthKind.NO_MODELS,
    ):
        owner = _HealthHarness()
        owner._health_banner.child.css_classes.add("error")
        owner._apply_health(HealthState(kind, kind.value, "detail"))
        results.check(
            f"{kind.value} health uses warning styling",
            owner._health_banner.child.css_classes == {"warn"},
        )

    class RemoveFailureWidget(_HealthWidget):
        def remove_css_class(self, css_class: str) -> None:
            raise RuntimeError(f"cannot remove {css_class}")

    style_failure = _HealthHarness()
    style_failure._health_banner.child = RemoveFailureWidget()
    style_failure._apply_health(
        HealthState(HealthKind.API_ERROR, "Error", "detail")
    )
    results.check(
        "health style-removal failures are swallowed before new style applies",
        style_failure._health_banner.child.css_classes == {"error"},
    )

    no_child = _HealthHarness()
    no_child._health_banner.child = None
    no_child._apply_health(
        HealthState(HealthKind.NO_MODELS, "No models", "detail")
    )
    results.check(
        "health banners without an inner child still update safely",
        no_child._health_banner.visible is True
        and no_child._health_title.text == "No models",
    )
    missing_optional_health_widgets = _HealthHarness()
    missing_optional_health_widgets._health_title = None
    missing_optional_health_widgets._health_detail = None
    missing_optional_health_widgets._health_action_btn = None
    missing_optional_health_widgets._apply_health(
        HealthState(HealthKind.CHECKING, "Checking", "detail")
    )
    results.check(
        "missing optional health labels and action button are tolerated",
        missing_optional_health_widgets._health.kind == HealthKind.CHECKING
        and missing_optional_health_widgets._health_banner.visible is True,
    )

    # _refresh_models: loading no-op and current asynchronous ordering.
    blocked_refresh = _HealthHarness()
    blocked_refresh._loading_model = True
    results.check(
        "model refresh is a strict no-op while a model load is active",
        blocked_refresh._refresh_models() is False
        and blocked_refresh._health is None
        and blocked_refresh.statuses == []
        and blocked_refresh.control_sensitivity == [],
    )

    refresh = _HealthHarness()
    trace: list[object] = []
    probe_result = ProbeResult(
        HealthState(HealthKind.NO_MODELS, "No models", "none"),
        [],
    )
    refresh._apply_health = lambda health: trace.append(
        ("health", health.kind)
    )
    refresh._set_status = lambda status: trace.append(("status", status))
    refresh._set_load_controls_sensitive = lambda enabled: trace.append(
        ("controls", enabled)
    )
    refresh._refresh_btn = SimpleNamespace(
        set_sensitive=lambda enabled: trace.append(("refresh", enabled))
    )

    class ImmediateThread:
        def __init__(self, *, target, daemon: bool) -> None:
            trace.append(("thread", daemon))
            self.target = target

        def start(self) -> None:
            trace.append("start")
            self.target()

    def fake_probe(client):
        trace.append(("probe", client))
        return probe_result

    def fake_idle_add(callback, result):
        trace.append(("idle", callback.__name__, result))
        return 1

    with (
        patch.object(health_probe_module.threading, "Thread", ImmediateThread),
        patch.object(health_probe_module, "probe_ollama", fake_probe),
        patch.object(health_probe_module.GLib, "idle_add", fake_idle_add),
    ):
        refresh_result = refresh._refresh_models()
    results.check(
        "refresh publishes checking UI before starting its background probe",
        refresh_result is False
        and trace[:4]
        == [
            ("health", HealthKind.CHECKING),
            ("status", "Checking Ollama…"),
            ("controls", False),
            ("refresh", False),
        ]
        and trace[4:7]
        == [
            ("thread", True),
            "start",
            ("probe", refresh.client),
        ]
        and trace[7][0:2] == ("idle", "_on_ollama_probe")
        and trace[7][2] is probe_result,
    )
    no_refresh_button = _HealthHarness()
    no_refresh_button._refresh_btn = None
    with (
        patch.object(health_probe_module.threading, "Thread", ImmediateThread),
        patch.object(health_probe_module, "probe_ollama", fake_probe),
        patch.object(health_probe_module.GLib, "idle_add", fake_idle_add),
    ):
        no_refresh_button_result = no_refresh_button._refresh_models()
    results.check(
        "refresh tolerates a missing refresh button",
        no_refresh_button_result is False
        and no_refresh_button._health.kind == HealthKind.CHECKING,
    )

    # _on_ollama_probe: successful load and every recovery placeholder.
    ok_owner = _HealthHarness()
    ok_owner._preferred_model = lambda: "beta:latest"
    ok_result = ProbeResult(
        HealthState(HealthKind.OK, "Ready", "connected"),
        ["alpha:latest", "beta:latest"],
    )
    ok_return = ok_owner._on_ollama_probe(ok_result)
    results.check(
        "healthy probe installs models, selects the preference, and begins warm-up",
        ok_return is False
        and ok_owner._health is ok_result.state
        and ok_owner._load_failed is False
        and _string_list_values(ok_owner.model_combo.model)
        == ["alpha:latest", "beta:latest"]
        and ok_owner.model_combo.selected == 1
        and ok_owner._model == "beta:latest"
        and ok_owner.send_btn.sensitive is False
        and ok_owner.statuses == ["Loading beta:latest…"]
        and ok_owner._suppress_model_select is False
        and ok_owner.load_requests == [("beta:latest", True)],
    )

    ok_with_messages = _HealthHarness()
    ok_with_messages._messages = [{"role": "user", "content": "hello"}]
    ok_with_messages._preferred_model = lambda: None
    ok_with_messages._on_ollama_probe(ok_result)
    results.check(
        "healthy probe suppresses greeting when messages already exist",
        ok_with_messages.load_requests == [("alpha:latest", False)],
    )

    recovery_cases = (
        (
            HealthKind.NO_MODELS,
            "No models installed",
            "No models installed",
        ),
        (
            HealthKind.NOT_RUNNING,
            "Ollama stopped",
            "Ollama unavailable",
        ),
        (
            HealthKind.NOT_INSTALLED,
            "Ollama absent",
            "Ollama unavailable",
        ),
        (
            HealthKind.API_ERROR,
            "E" * 100,
            "E" * 80,
        ),
        (
            HealthKind.OK,
            "",
            "Ollama error",
        ),
    )
    for kind, title, placeholder in recovery_cases:
        owner = _HealthHarness()
        owner._model = "stale-model"
        owner.send_btn.sensitive = True
        owner.input.sensitive = False
        probe = ProbeResult(HealthState(kind, title, "detail"), [])
        probe_return = owner._on_ollama_probe(probe)
        results.check(
            f"{kind.value} probe without models enters the documented recovery state",
            probe_return is False
            and owner._health is probe.state
            and owner.overlay_hides == 1
            and owner._load_failed is True
            and owner._model is None
            and _string_list_values(owner.model_combo.model) == [placeholder]
            and owner._suppress_model_select is False
            and owner.send_btn.sensitive is False
            and owner.statuses == [title]
            and owner.control_sensitivity == [True]
            and owner.input.sensitive is True,
        )
    no_input = _HealthHarness()
    no_input.input = None
    no_input._on_ollama_probe(
        ProbeResult(
            HealthState(HealthKind.NOT_RUNNING, "Unavailable", "detail"),
            [],
        )
    )
    results.check(
        "unhealthy probe tolerates a missing input widget",
        no_input._load_failed is True and no_input._model is None,
    )
    unhealthy_with_models = _HealthHarness()
    unhealthy_with_models._on_ollama_probe(
        ProbeResult(
            HealthState(HealthKind.API_ERROR, "Probe error", "detail"),
            ["ignored-model"],
        )
    )
    results.check(
        "an unhealthy state stays on recovery even if its result carries models",
        unhealthy_with_models._load_failed is True
        and unhealthy_with_models._model is None
        and _string_list_values(unhealthy_with_models.model_combo.model)
        == ["Probe error"]
        and unhealthy_with_models.load_requests == [],
    )

    delivered = _HealthHarness()
    delivered._preferred_model = lambda: None
    newer = ProbeResult(
        HealthState(HealthKind.OK, "newer", "detail"),
        ["newer-model"],
    )
    older = ProbeResult(
        HealthState(HealthKind.API_ERROR, "older error", "detail"),
        [],
    )
    delivered._on_ollama_probe(newer)
    delivered._on_ollama_probe(older)
    results.check(
        "probe callbacks have no generation guard and apply in delivery order",
        delivered._health is older.state
        and delivered._model is None
        and _string_list_values(delivered.model_combo.model)
        == ["older error"],
    )

    # _on_health_action: refresh, retry-load fallbacks, and dismiss.
    action_owner = _HealthHarness()
    action_trace: list[object] = []
    action_owner._refresh_models = lambda: action_trace.append("refresh")
    action_owner._begin_model_load = (
        lambda model, *, greet=False: action_trace.append(
            ("load", model, greet)
        )
    )
    action_owner._health_action_id = "refresh"
    action_owner._on_health_action()
    action_owner._health_action_id = "retry_load"
    action_owner._health_action_model = "action-model"
    action_owner._messages = []
    action_owner._on_health_action()
    action_owner._health_action_model = None
    action_owner._model = "current-model"
    action_owner._messages = [{"role": "user"}]
    action_owner._on_health_action()
    action_owner._model = None
    action_owner._on_health_action()
    results.check(
        "health refresh and retry actions preserve model and greeting fallbacks",
        action_trace
        == [
            "refresh",
            ("load", "action-model", True),
            ("load", "current-model", False),
            "refresh",
        ],
    )

    dismiss = _HealthHarness()
    dismiss._health_action_id = "dismiss"
    dismiss._health_banner.visible = True
    dismiss._on_health_action()
    results.check(
        "dismiss applies healthy state and explicitly hides the banner",
        dismiss._health.kind == HealthKind.OK
        and dismiss._health.title == "Ollama is ready"
        and dismiss._health_banner.visible is False,
    )
    dismiss_without_banner = _HealthHarness()
    dismiss_without_banner._health_action_id = "dismiss"
    dismiss_without_banner._health_banner = None
    dismiss_without_banner._on_health_action()
    results.check(
        "dismiss tolerates a missing health banner",
        dismiss_without_banner._health.kind == HealthKind.OK,
    )
    unknown_action = _HealthHarness()
    unknown_action._health_action_id = "unknown"
    unknown_action._on_health_action()
    results.check(
        "unknown or missing health actions are no-ops",
        unknown_action._health is None
        and unknown_action.load_requests == []
        and unknown_action.statuses == [],
    )

    # _preferred_model: active-conversation priority and all fallbacks.
    preferred = _HealthHarness()
    preferred._conversation_id = "conversation-a"
    preferred._store = _HealthStore(
        SimpleNamespace(model="conversation-model")
    )
    with patch.object(
        window_module,
        "_load_last_model",
        return_value="last-model",
    ) as load_last:
        selected_preference = preferred._preferred_model()
    results.check(
        "active conversation model outranks the global last model",
        selected_preference == "conversation-model"
        and preferred._store.calls == ["conversation-a"]
        and load_last.call_count == 0,
    )

    for label, conversation_id, store in (
        ("missing active id", None, _HealthStore()),
        (
            "conversation without model",
            "conversation-b",
            _HealthStore(SimpleNamespace(model=None)),
        ),
        ("missing conversation", "conversation-c", _HealthStore(None)),
        (
            "store failure",
            "conversation-d",
            _HealthStore(error=RuntimeError("forced store failure")),
        ),
    ):
        owner = _HealthHarness()
        owner._conversation_id = conversation_id
        owner._store = store
        with patch.object(
            window_module,
            "_load_last_model",
            return_value="last-model",
        ):
            value = owner._preferred_model()
        results.check(
            f"{label} falls back to the global last model",
            value == "last-model",
        )

    # _select_model_name: empty/model-less, exact/soft/no-match, and warm-up.
    no_name = _HealthHarness(("alpha",))
    no_name._model = "unchanged"
    no_name._select_model_name("", warm=True, greet=True)
    no_combo = _HealthHarness(("alpha",))
    no_combo.model_combo = None
    no_combo._select_model_name("alpha", warm=True, greet=True)
    results.check(
        "programmatic selection ignores empty names and missing dropdowns",
        no_name._model == "unchanged"
        and no_name.load_requests == []
        and no_combo._model is None
        and no_combo.load_requests == [],
    )

    no_model = _HealthHarness()
    no_model.model_combo.model = None
    no_model._select_model_name("raw-name")
    warm_no_model = _HealthHarness()
    warm_no_model.model_combo.model = None
    warm_no_model._select_model_name("warm-name", warm=True, greet=True)
    results.check(
        "missing dropdown model preserves raw name and optional warm-up",
        no_model._model == "raw-name"
        and no_model.load_requests == []
        and warm_no_model._model == "warm-name"
        and warm_no_model.load_requests == [("warm-name", True)],
    )

    exact = _HealthHarness(
        (None, "family:latest", "family:exact", "other:latest")
    )
    exact._select_model_name("family:exact")
    soft = _HealthHarness(("family:latest", "other:latest"))
    soft._select_model_name("family:new")
    missing = _HealthHarness(("alpha:latest", "beta:latest"))
    missing._select_model_name("gamma:latest")
    results.check(
        "programmatic selection prefers exact, then soft-family, then raw name",
        exact.model_combo.selected == 2
        and exact._model == "family:exact"
        and soft.model_combo.selected == 0
        and soft._model == "family:latest"
        and missing.model_combo.selection_history == []
        and missing._model == "gamma:latest"
        and not exact._suppress_model_select
        and not soft._suppress_model_select
        and not missing._suppress_model_select,
    )

    warm_empty = _HealthHarness(("alpha",))
    warm_empty._select_model_name("alpha", warm=True, greet=True)
    warm_messages = _HealthHarness(("alpha",))
    warm_messages._messages = [{"role": "user"}]
    warm_messages._select_model_name("alpha", warm=True, greet=True)
    warming = _HealthHarness(("alpha",))
    warming._loading_model = True
    warming._select_model_name("alpha", warm=True, greet=True)
    cold = _HealthHarness(("alpha",))
    cold._select_model_name("alpha", warm=False, greet=True)
    results.check(
        "programmatic warm-up honors greet, messages, warm, and load-in-progress",
        warm_empty.load_requests == [("alpha", True)]
        and warm_messages.load_requests == [("alpha", False)]
        and warming.load_requests == []
        and cold.load_requests == [],
    )

    # _on_model_selected: suppression/placeholders, same-model, retry, load.
    suppressed = _HealthHarness(("alpha",))
    suppressed._suppress_model_select = True
    suppressed._on_model_selected()
    no_item = _HealthHarness(("alpha",))
    no_item.model_combo.selected = -1
    no_item._on_model_selected()
    results.check(
        "dropdown selection ignores suppression and missing selected items",
        suppressed.load_requests == []
        and suppressed._model is None
        and no_item.load_requests == []
        and no_item._model is None,
    )

    for invalid_name in (
        "",
        "Loading models…",
        "No models installed",
        "Cannot reach Ollama",
        "Error from Ollama",
    ):
        invalid = _HealthHarness((invalid_name,))
        invalid._on_model_selected()
        results.check(
            f"dropdown ignores non-model entry {invalid_name!r}",
            invalid._model is None
            and invalid.statuses == []
            and invalid.load_requests == [],
        )

    same = _HealthHarness(("alpha",))
    same._model = "alpha"
    same._on_model_selected()
    results.check(
        "same healthy loaded model selection is a no-op",
        same.statuses == [] and same.load_requests == [],
    )

    retry = _HealthHarness(("alpha",))
    retry._model = "alpha"
    retry._load_failed = True
    retry._on_model_selected()
    during_load = _HealthHarness(("alpha",))
    during_load._model = "alpha"
    during_load._loading_model = True
    during_load._on_model_selected()
    changed = _HealthHarness(("beta",))
    changed._model = "alpha"
    changed._messages = [{"role": "user"}]
    changed._on_model_selected()
    results.check(
        "dropdown retry/load-in-progress/different-model paths begin load exactly as today",
        retry.statuses == ["alpha"]
        and retry.load_requests == [("alpha", True)]
        and during_load.statuses == ["alpha"]
        and during_load.load_requests == [("alpha", True)]
        and changed._model == "beta"
        and changed.statuses == ["beta"]
        and changed.load_requests == [("beta", False)],
    )

    owner = _HealthHarness(("alpha",))
    results.check(
        "health controller owns all four Phase-8 private state fields",
        all(
            name in owner.__dict__
            for name in (
                "_health",
                "_suppress_model_select",
                "_health_action_id",
                "_health_action_model",
            )
        ),
    )

    rebound_model: dict[str, object] = {
        "current": None,
        "loading": False,
        "failed": True,
        "loads": [],
    }
    owner.set_model_session_callbacks(
        get_current_model=lambda: rebound_model["current"],
        set_current_model=lambda model: rebound_model.__setitem__(
            "current", model
        ),
        is_loading=lambda: bool(rebound_model["loading"]),
        is_load_failed=lambda: bool(rebound_model["failed"]),
        set_load_failed=lambda failed: rebound_model.__setitem__(
            "failed", failed
        ),
        begin_load=lambda model, greet: rebound_model["loads"].append(
            (model, greet)
        ),
    )
    owner.set_conversation_providers(
        messages_empty=lambda: False,
        active_conversation_model=lambda: "rebound-preference",
    )
    owner._select_model_name("alpha", warm=True, greet=True)
    results.check(
        "Phase 10 and Phase 22 callbacks can be rebound without copied state",
        rebound_model["current"] == "alpha"
        and rebound_model["loads"] == [("alpha", False)]
        and owner._preferred_model() == "rebound-preference",
    )


class _LoadWidget(_HealthWidget):
    def __init__(self, *, child=None) -> None:
        super().__init__(child=child)
        self.visible = False
        self.pulses = 0
        self.fractions: list[float] = []
        self.starts = 0
        self.stops = 0
        self.focuses = 0
        self.fail_start = False
        self.fail_stop = False
        self.fail_focus = False

    def get_visible(self) -> bool:
        return bool(self.visible)

    def pulse(self) -> None:
        self.pulses += 1

    def set_fraction(self, fraction: float) -> None:
        self.fractions.append(fraction)

    def start(self) -> None:
        if self.fail_start:
            raise RuntimeError("forced spinner start failure")
        self.starts += 1

    def stop(self) -> None:
        if self.fail_stop:
            raise RuntimeError("forced spinner stop failure")
        self.stops += 1

    def grab_focus(self) -> None:
        if self.fail_focus:
            raise RuntimeError("forced focus failure")
        self.focuses += 1


class _LoadStore:
    def __init__(self, trace: list[object]) -> None:
        self.trace = trace
        self.error: Exception | None = None

    def set_model(self, conversation_id: str, model: str) -> None:
        self.trace.append(("store_model", conversation_id, model))
        if self.error is not None:
            raise self.error


class _LoadClient:
    def __init__(self) -> None:
        self.loaded = False
        self.chunks: list[dict] = []
        self.error: Exception | None = None
        self.calls: list[object] = []
        self.stop_checks: list[object] = []

    def is_model_loaded(self, model: str) -> bool:
        self.calls.append(("loaded", model))
        if self.error is not None:
            raise self.error
        return self.loaded

    def load_model(self, model: str, *, should_stop):
        self.calls.append(("load", model))
        self.stop_checks.append(should_stop)
        if self.error is not None:
            raise self.error
        yield from self.chunks


class _LoadHarness(ModelLoadController):
    def __init__(self) -> None:
        self.client = _LoadClient()
        self._streaming = False
        self._messages: list[dict] = []
        self.trace: list[object] = []
        self._store = _LoadStore(self.trace)
        super().__init__(
            client=self.client,
            load_overlay=_LoadWidget(),
            load_title=_LoadWidget(),
            load_model_label=_LoadWidget(),
            load_status=_LoadWidget(),
            load_progress=_LoadWidget(),
            load_spinner=_LoadWidget(),
            health_banner=_LoadWidget(),
            model_selector=_LoadWidget(),
            refresh_control=_LoadWidget(),
            input_widget=_LoadWidget(),
            send_control=_LoadWidget(),
            clear_control=_LoadWidget(),
            new_chat_control=_LoadWidget(),
            sidebar_new_control=_LoadWidget(),
            sidebar_control=_LoadWidget(),
            history_list=_LoadWidget(),
            is_streaming=lambda: self._streaming,
            messages_empty=lambda: not self._messages,
            ensure_conversation=self._ensure_conversation,
            set_conversation_model=self._store.set_model,
            set_status=self._set_status,
            apply_health=self._apply_health,
            set_shared_sensitivity=self._set_load_controls_sensitive,
            save_last_model=lambda model: None,
            format_bytes=window_module._fmt_bytes,
            on_ready=lambda should_greet: (
                self._show_ephemeral_greeting() if should_greet else None
            ),
        )

    def _set_load_controls_sensitive(self, enabled: bool) -> None:
        self.trace.append(("controls", enabled))

    def _set_status(self, status: str) -> None:
        self.trace.append(("status", status))

    def _apply_health(self, health: HealthState) -> None:
        self.trace.append(("health", health))

    def _ensure_conversation(self) -> str:
        self.trace.append("ensure_conversation")
        return "conversation-a"

    def _show_ephemeral_greeting(self) -> None:
        self.trace.append("greeting")


def characterize_model_load(results: Results) -> None:
    """Lock down every Phase-9 model-load branch before extraction."""
    print("\n[0d] Model-load characterization", flush=True)

    no_overlay = _LoadHarness()
    no_overlay._load_overlay = None
    no_overlay._show_load_overlay(
        model="alpha", title="Loading", status="Starting"
    )
    results.check(
        "show-load is a strict no-op when the overlay is absent",
        no_overlay.trace == []
        and no_overlay._load_title.text is None
        and no_overlay._load_progress.pulses == 0,
    )

    timers: list[object] = []
    overlay = _LoadHarness()
    with patch.object(
        model_session_module.GLib,
        "timeout_add",
        side_effect=lambda interval, callback: (
            timers.append((interval, callback)) or 41
        ),
    ):
        overlay._show_load_overlay(
            model="alpha",
            title="Loading model",
            status="Starting",
            pulse=True,
        )
        overlay._start_load_pulse()
    results.check(
        "indeterminate overlay presentation starts exactly one pulse source",
        overlay._load_title.text == "Loading model"
        and overlay._load_model_label.text == "alpha"
        and overlay._load_model_label.visible is True
        and overlay._load_status.text == "Starting"
        and overlay._load_progress.pulses == 1
        and overlay._load_spinner.starts == 1
        and overlay._load_overlay.visible is True
        and overlay.trace == [("controls", False)]
        and len(timers) == 1
        and timers[0][0] == 100
        and overlay._load_pulse_id == 41,
    )
    tick = timers[0][1]
    before = overlay._load_progress.pulses
    visible_tick = tick()
    overlay._load_indeterminate = False
    determinate_tick = tick()
    overlay._load_overlay.visible = False
    hidden_tick = tick()
    results.check(
        "pulse ticks stop when hidden and pulse only while indeterminate",
        visible_tick is True
        and determinate_tick is True
        and hidden_tick is False
        and overlay._load_progress.pulses == before + 1
        and overlay._load_pulse_id == 0,
    )

    removed: list[int] = []
    overlay._load_overlay.visible = True
    overlay._load_pulse_id = 52
    with patch.object(
        model_session_module.GLib,
        "source_remove",
        side_effect=lambda source_id: removed.append(source_id),
    ):
        overlay._show_load_overlay(
            model=None,
            title="Ready",
            status="Done",
            pulse=False,
            fraction=1.5,
        )
    results.check(
        "determinate overlay clamps progress, hides empty model, and stops pulse",
        removed == [52]
        and overlay._load_pulse_id == 0
        and overlay._load_indeterminate is False
        and overlay._load_progress.fractions[-1] == 1.0
        and overlay._load_model_label.text == ""
        and overlay._load_model_label.visible is False,
    )

    overlay._load_pulse_id = 63
    overlay._load_spinner.fail_stop = True
    with patch.object(
        model_session_module.GLib,
        "source_remove",
        side_effect=RuntimeError("forced source failure"),
    ):
        overlay._hide_load_overlay()
    results.check(
        "hide-load swallows stop failures, hides overlay, and restores controls",
        overlay._load_pulse_id == 0
        and overlay._load_overlay.visible is False
        and overlay.trace[-1] == ("controls", True),
    )
    spinner_failure = _LoadHarness()
    spinner_failure._load_spinner.fail_start = True
    with patch.object(model_session_module.GLib, "timeout_add", return_value=64):
        spinner_failure._show_load_overlay(
            model="alpha", title="Loading", status="Starting"
        )
    results.check(
        "show-load swallows spinner start failures after presenting the overlay",
        spinner_failure._load_overlay.visible is True
        and spinner_failure.trace == [("controls", False)],
    )

    progress = _LoadHarness()
    progress._load_pulse_id = 70
    with patch.object(model_session_module.GLib, "source_remove"):
        progress._update_load_progress(
            {"status": "pulling_manifest", "completed": 1024, "total": 2048}
        )
        first_progress_text = progress._load_status.text
        progress._update_load_progress({"completed": 300, "total": 100})
    results.check(
        "NDJSON byte progress maps status, detail, fractions, and clamping",
        first_progress_text == "Pulling manifest · 1.0 KB / 2.0 KB"
        and progress._load_status.text == "300 B / 100 B"
        and progress._load_progress.fractions == [0.5, 1.0]
        and progress._load_indeterminate is False,
    )
    progress._load_pulse_id = 0
    timers.clear()
    with patch.object(
        model_session_module.GLib,
        "timeout_add",
        side_effect=lambda interval, callback: (
            timers.append((interval, callback)) or 71
        ),
    ):
        progress._update_load_progress({"status": "warming_weights"})
        previous_text = progress._load_status.text
        progress._update_load_progress({})
    results.check(
        "status-only and malformed chunks preserve text and use indeterminate pulse",
        previous_text == "Warming weights"
        and progress._load_status.text == previous_text
        and progress._load_indeterminate is True
        and progress._load_progress.pulses == 2
        and len(timers) == 1,
    )

    stale = _LoadHarness()
    stale._load_generation = 4
    stale._loading_model = True
    stale_status = stale._on_load_status(
        3, "old", "Old title", "Old status", 0.5
    )
    stale_chunk = stale._on_load_chunk(3, {"status": "old"})
    stale_finish = stale._on_model_load_finished(3, "old", None, True)
    results.check(
        "stale status, chunk, and finish callbacks are strict no-ops",
        stale_status is False
        and stale_chunk is False
        and stale_finish is False
        and stale._loading_model is True
        and stale.trace == []
        and stale._load_title.text is None,
    )

    current = _LoadHarness()
    current._load_generation = 5
    current._load_pulse_id = 72
    with patch.object(model_session_module.GLib, "source_remove"):
        current._on_load_status(
            5, "alpha", "Loaded", "Ready.", 0.75
        )
    timers.clear()
    current._load_pulse_id = 0
    with patch.object(
        model_session_module.GLib,
        "timeout_add",
        side_effect=lambda interval, callback: (
            timers.append((interval, callback)) or 73
        ),
    ):
        current._on_load_status(
            5, "alpha", "Loading", "Warming", None
        )
        current._on_load_chunk(5, {"status": "loading_weights"})
    results.check(
        "current status and chunk callbacks preserve determinate/indeterminate transitions",
        current._load_title.text == "Loading"
        and current._load_model_label.text == "alpha"
        and current._load_model_label.visible is True
        and current._load_status.text == "Loading weights"
        and current._load_progress.fractions == [0.75]
        and current._load_indeterminate is True
        and len(timers) == 1,
    )

    threads: list[object] = []

    class CapturingThread:
        def __init__(self, *, target, daemon: bool) -> None:
            self.target = target
            self.daemon = daemon

        def start(self) -> None:
            threads.append(self)

    no_start = _LoadHarness()
    with patch.object(model_session_module.threading, "Thread", CapturingThread):
        no_start._begin_model_load("", greet=True)
        no_start._streaming = True
        no_start._begin_model_load("alpha", greet=True)
    results.check(
        "empty-model and streaming begin-load paths are strict no-ops",
        no_start._load_generation == 0
        and no_start.trace == []
        and threads == [],
    )

    replacement = _LoadHarness()
    threads.clear()
    queued: list[tuple[str, tuple]] = []
    with (
        patch.object(model_session_module.threading, "Thread", CapturingThread),
        patch.object(
            model_session_module.GLib,
            "idle_add",
            side_effect=lambda callback, *args: (
                queued.append((callback.__name__, args)) or 1
            ),
        ),
    ):
        replacement._begin_model_load("older", greet=True)
        older_thread = threads[-1]
        replacement._begin_model_load("newer", greet=False)
        older_thread.target()
    results.check(
        "new loads replace prior generations and stale workers cannot enqueue UI",
        replacement._load_generation == 2
        and replacement._loading_model is True
        and replacement._stop_load is False
        and len(threads) == 2
        and replacement.client.calls == [("loaded", "older")]
        and queued == [],
    )

    def run_worker(owner: _LoadHarness) -> list[tuple[str, tuple]]:
        threads.clear()
        events: list[tuple[str, tuple]] = []
        with (
            patch.object(model_session_module.threading, "Thread", CapturingThread),
            patch.object(
                model_session_module.GLib,
                "idle_add",
                side_effect=lambda callback, *args: (
                    events.append((callback.__name__, args)) or 1
                ),
            ),
        ):
            owner._begin_model_load("alpha", greet=True)
            threads[-1].target()
        return events

    already = _LoadHarness()
    already.client.loaded = True
    already_events = run_worker(already)
    results.check(
        "already-loaded workers enqueue ready status before successful finish",
        [event[0] for event in already_events]
        == ["_on_load_status", "_on_model_load_finished"]
        and already_events[0][1][2:] == (
            "Model already loaded",
            "Ready.",
            1.0,
        )
        and already_events[1][1] == (1, "alpha", None, True),
    )

    cold = _LoadHarness()
    cold.client.chunks = [
        {"status": "pulling", "completed": 1, "total": 2},
        {"status": "loading"},
    ]
    cold_events = run_worker(cold)
    cold_stop = cold.client.stop_checks[0]
    cold_stop_initial = cold_stop()
    cold._stop_load = True
    cold_stop_requested = cold_stop()
    cold._stop_load = False
    cold._load_generation += 1
    cold_stop_stale = cold_stop()
    results.check(
        "cold workers enqueue warm status, every chunk, then finish in order",
        [event[0] for event in cold_events]
        == [
            "_on_load_status",
            "_on_load_chunk",
            "_on_load_chunk",
            "_on_model_load_finished",
        ]
        and cold.client.stop_checks
        and cold_stop_initial is False
        and cold_stop_requested is True
        and cold_stop_stale is True,
    )

    for label, error in (
        ("OllamaError", OllamaError("ollama failure")),
        ("generic exception", RuntimeError("generic failure")),
    ):
        failed_worker = _LoadHarness()
        failed_worker.client.error = error
        error_events = run_worker(failed_worker)
        results.check(
            f"{label} workers enqueue the exact error for completion",
            error_events == [
                (
                    "_on_model_load_finished",
                    (1, "alpha", str(error), True),
                )
            ],
        )

    failure = _LoadHarness()
    failure._load_generation = 8
    failure._loading_model = True
    failure._stop_load_pulse = lambda: failure.trace.append("stop_pulse")
    failure._hide_load_overlay = lambda: failure.trace.append("hide_overlay")
    failure_return = failure._on_model_load_finished(
        8, "broken-model", "model failed", True
    )
    failure_health = next(
        event[1] for event in failure.trace if isinstance(event, tuple) and event[0] == "health"
    )
    results.check(
        "failed completion preserves state, health, status, and recovery sensitivity ordering",
        failure_return is False
        and failure._loading_model is False
        and failure._load_failed is True
        and failure._model == "broken-model"
        and failure.trace[:4]
        == [
            "stop_pulse",
            "hide_overlay",
            ("health", failure_health),
            ("status", "Load failed"),
        ]
        and failure_health.kind == HealthKind.API_ERROR
        and failure.model_combo.sensitive is True
        and failure._refresh_btn.sensitive is True
        and failure.input.sensitive is True
        and failure.send_btn.sensitive is False
        and failure._clear_btn.sensitive is True
        and failure._new_chat_btn.sensitive is True
        and failure._sidebar_new_btn.sensitive is True
        and failure._sidebar_btn.sensitive is True
        and failure._history_list.sensitive is True,
    )

    success = _LoadHarness()
    success._load_generation = 9
    success._loading_model = True
    success._stop_load_pulse = lambda: success.trace.append("stop_pulse")
    success._hide_load_overlay = lambda: success.trace.append("hide_overlay")
    success._save_last_model = lambda model: success.trace.append(
        ("save_last", model)
    )
    success._on_model_load_finished(9, "alpha", None, True)
    success._load_generation = 10
    success._loading_model = True
    success._on_model_load_finished(10, "alpha", None, True)
    success_health = next(
        event[1]
        for event in success.trace
        if isinstance(event, tuple) and event[0] == "health"
    )
    results.check(
        "successful completion persists before one-time greeting and restores focus",
        success._loading_model is False
        and success._load_failed is False
        and success._load_progress.fractions == [1.0, 1.0]
        and success._load_status.text == "Ready"
        and success._health_banner.visible is False
        and success._greeted_models == {"alpha"}
        and success.trace.count("greeting") == 1
        and success.trace[:4]
        == [
            "stop_pulse",
            "hide_overlay",
            ("health", success_health),
            ("status", "alpha"),
        ]
        and success_health.kind == HealthKind.OK
        and success.trace.index(("save_last", "alpha"))
        < success.trace.index("ensure_conversation")
        < success.trace.index(("store_model", "conversation-a", "alpha"))
        < success.trace.index("greeting")
        and success.send_btn.sensitive is True
        and success.input.focuses == 2,
    )

    persistence_failure = _LoadHarness()
    persistence_failure._load_generation = 10
    persistence_failure._store.error = RuntimeError("forced persistence failure")
    persistence_failure._stop_load_pulse = lambda: None
    persistence_failure._hide_load_overlay = lambda: None
    with contextlib.redirect_stdout(io.StringIO()) as captured:
        persistence_failure._on_model_load_finished(
            10, "beta", None, True
        )
    results.check(
        "conversation-model persistence failure is logged but greeting and controls continue",
        "persist model failed: forced persistence failure" in captured.getvalue()
        and persistence_failure.trace[-1] == "greeting"
        and persistence_failure.send_btn.sensitive is True
        and persistence_failure.input.focuses == 1,
    )

    nonempty = _LoadHarness()
    nonempty._load_generation = 11
    nonempty._messages = [{"role": "user"}]
    nonempty._stop_load_pulse = lambda: None
    nonempty._hide_load_overlay = lambda: None
    nonempty._on_model_load_finished(11, "gamma", None, True)
    results.check(
        "successful load with existing messages does not consume greeting dedup",
        "greeting" not in nonempty.trace and nonempty._greeted_models == set(),
    )

    class RecordingSet(set):
        def __init__(self, trace: list[str], label: str, values=()) -> None:
            super().__init__(values)
            self.trace = trace
            self.label = label

        def clear(self) -> None:
            self.trace.append(self.label)
            super().clear()

    class RecordingList(list):
        def __init__(self, trace: list[str], label: str, values=()) -> None:
            super().__init__(values)
            self.trace = trace
            self.label = label

        def clear(self) -> None:
            self.trace.append(self.label)
            super().clear()

    class RecordingDict(dict):
        def __init__(self, trace: list[str], label: str) -> None:
            super().__init__({"row": object()})
            self.trace = trace
            self.label = label

        def clear(self) -> None:
            self.trace.append(self.label)
            super().clear()

    class LifecycleStore:
        def __init__(self, trace: list[str]) -> None:
            self.trace = trace
            self.empty = False
            self.conversation = SimpleNamespace(id="new-conversation", model=None)

        def clear_messages(self, _conversation_id: str) -> None:
            self.trace.append("clear_store")

        def create_conversation(self, *, model):
            self.trace.append("create")
            return self.conversation

        def prune_empty_conversations(self, *, keep_id) -> None:
            self.trace.append("prune")

        def is_empty(self, _conversation_id: str) -> bool:
            self.trace.append("is_empty")
            return self.empty

        def delete_conversation(self, _conversation_id: str) -> None:
            self.trace.append("delete")

        def get_conversation(self, _conversation_id: str):
            self.trace.append("get")
            return self.conversation

        def set_active(self, _conversation_id: str) -> None:
            self.trace.append("set_active")

        def list_messages(self, _conversation_id: str):
            self.trace.append("list_messages")
            return []

    class LifecycleHarness:
        def __init__(self) -> None:
            self.trace: list[str] = []
            self._streaming = False
            self._loading_model = False
            self._load_failed = False
            self._model = None
            self._greeted_models = RecordingSet(
                self.trace, "greetings_clear", {"alpha"}
            )
            self._store = LifecycleStore(self.trace)
            self.input = _LoadWidget()
            self._conversation = ConversationLifecycleController(
                store=self._store,
                transient_parent=SimpleNamespace(),
                get_current_model=lambda: self._model,
                is_loading_model=lambda: self._loading_model,
                is_load_failed=lambda: self._load_failed,
                is_streaming=lambda: self._streaming,
                reset_greetings=self._greeted_models.clear,
                clear_native_rows=RecordingDict(self.trace, "rows_clear").clear,
                render_empty_transcript=lambda: None,
                apply_restored_transcript=lambda _messages: None,
                mark_history_dirty=lambda: None,
                rebuild_history_list=lambda: False,
                refresh_chat_title=lambda: False,
                set_status=lambda _text: None,
                show_ephemeral_greeting=lambda: None,
                sync_composer_hint=lambda: None,
                select_model_name=lambda *_args, **_kwargs: None,
                save_last_model=lambda _model: None,
                is_ephemeral_greeting=window_module._is_ephemeral_greeting,
                request_stop=lambda: None,
                invalidate_active_stream=lambda: None,
                grab_input_focus=lambda: None,
            )
            self._conversation.conversation_id = "active"
            self._conversation.messages = RecordingList(
                self.trace, "messages_clear", [{"role": "user"}]
            )
            self._conversation.history_restored = True

        def clear_chat(self) -> None:
            self._conversation.clear_chat()

        def new_chat(self) -> None:
            self._conversation.new_chat()

        def switch_conversation(self, conversation_id: str) -> None:
            self._conversation.switch_conversation(conversation_id)

        @property
        def _messages(self):
            return self._conversation.messages

        @_messages.setter
        def _messages(self, value) -> None:
            self._conversation.messages = value

    clear_owner = LifecycleHarness()
    clear_owner.clear_chat()
    new_owner = LifecycleHarness()
    new_owner.new_chat()
    empty_owner = LifecycleHarness()
    empty_owner._messages.clear()
    empty_owner.trace.clear()
    empty_owner._store.empty = True
    empty_owner.new_chat()
    switch_owner = LifecycleHarness()
    switch_owner._store.empty = False
    switch_owner.switch_conversation("target")
    results.check(
        "greeting resets stay at clear, successful-new, and successful-switch positions",
        clear_owner.trace[:4]
        == ["messages_clear", "greetings_clear", "rows_clear", "clear_store"]
        and "greetings_clear" in new_owner.trace
        and new_owner.trace.index("greetings_clear")
        == new_owner.trace.index("messages_clear") + 1
        and new_owner.trace.index("rows_clear")
        == new_owner.trace.index("greetings_clear") + 1
        and switch_owner.trace.index("set_active")
        < switch_owner.trace.index("greetings_clear")
        < switch_owner.trace.index("rows_clear")
        < switch_owner.trace.index("list_messages"),
    )
    results.check(
        "already-empty new-chat returns without resetting greeting dedup",
        empty_owner._greeted_models == {"alpha"}
        and "greetings_clear" not in empty_owner.trace,
    )

    extracted_owner = _LoadHarness()
    results.check(
        "model controller owns all eight Phase-10 state fields",
        all(
            name in extracted_owner.__dict__
            for name in (
                "_model",
                "_loading_model",
                "_load_failed",
                "_load_generation",
                "_stop_load",
                "_load_pulse_id",
                "_load_indeterminate",
                "_greeted_models",
            )
        ),
    )
    rebound_conversation: list[object] = []
    extracted_owner.set_conversation_providers(
        messages_empty=lambda: True,
        ensure_conversation=lambda: (
            rebound_conversation.append("ensure") or "rebound-conversation"
        ),
    )
    extracted_owner._set_conversation_model = (
        lambda conversation_id, model: rebound_conversation.append(
            ("persist", conversation_id, model)
        )
    )
    extracted_owner._load_generation = 12
    extracted_owner._stop_load_pulse = lambda: None
    extracted_owner._hide_load_overlay = lambda: None
    extracted_owner._on_model_load_finished(12, "rebound-model", None, True)
    results.check(
        "Phase 22 conversation providers can be rebound without copied state",
        rebound_conversation
        == [
            "ensure",
            ("persist", "rebound-conversation", "rebound-model"),
        ]
        and extracted_owner._greeted_models == {"rebound-model"}
        and extracted_owner.trace[-1] == "greeting",
    )


def characterize_transcript_reset_replay_removal(
    results: Results,
    app: Adw.Application,
) -> None:
    """Lock Phase-11 backend selection plus reset/replay/removal behavior."""
    print("\n[0f] Transcript reset/replay/removal characterization", flush=True)

    real_build_ui = ChatSidebar._build_ui
    native_construction_trace: list[str] = []

    def build_requested_native(owner) -> None:
        native_construction_trace.append("build")
        real_build_ui(owner)

    with (
        patch.dict(os.environ, {"CHICKENBUTT_TRANSCRIPT": "native"}),
        patch.object(
            window_module,
            "ensure_md_css",
            side_effect=lambda: native_construction_trace.append("ensure"),
        ),
        patch.object(ChatSidebar, "_build_ui", build_requested_native),
        patch.object(ChatSidebar, "_restore_history", lambda _self: None),
        patch.object(ChatSidebar, "_refresh_models", lambda _self: False),
    ):
        requested_native = ChatSidebar(app, client=OllamaClient())
    pump(0.05)
    requested_sink = requested_native._transcript

    results.check(
        "requested native construction installs markdown CSS before building its sink",
        native_construction_trace == ["ensure", "build"]
        and requested_sink.mode == "native"
        and requested_sink._web is None
        and requested_sink._scroller is not None
        and requested_sink._chat_box is not None
        and requested_sink.widget is requested_sink._scroller,
    )
    results.check(
        "requested native construction starts with one exact empty-state child and no rows",
        requested_sink._empty_box is not None
        and direct_children(requested_sink._chat_box) == [requested_sink._empty_box]
        and direct_children(requested_sink._empty_box)
        == [
            requested_sink._empty_icon,
            requested_sink._empty_title,
            requested_sink._empty_sub,
        ]
        and requested_sink._empty_title.get_label() == "Start a conversation"
        and requested_sink._empty_sub.get_label()
        == (
            "Messages stream from your local Ollama models.\n"
            "Need a model?\n"
            "Type in the box: ollama pull <model-name>"
        )
        and requested_sink._empty_box.get_parent() is requested_sink._chat_box
        and requested_sink._native_rows == {},
    )

    class FailingWebTranscriptView:
        def __init__(self, **_kwargs) -> None:
            raise RuntimeError("forced WebKit constructor failure")

    fallback_construction_trace: list[str] = []

    def build_fallback_native(owner) -> None:
        fallback_construction_trace.append("build")
        real_build_ui(owner)

    fake_transcript_module = SimpleNamespace(
        WebTranscriptView=FailingWebTranscriptView,
    )
    with (
        patch.dict(os.environ, {"CHICKENBUTT_TRANSCRIPT": "webkit"}),
        patch.dict(sys.modules, {"transcript_view": fake_transcript_module}),
        patch.object(
            window_module,
            "ensure_md_css",
            side_effect=lambda: fallback_construction_trace.append("ensure"),
        ),
        patch.object(ChatSidebar, "_build_ui", build_fallback_native),
        patch.object(ChatSidebar, "_restore_history", lambda _self: None),
        patch.object(ChatSidebar, "_refresh_models", lambda _self: False),
    ):
        fallback_native = ChatSidebar(app, client=OllamaClient())
    pump(0.05)
    fallback_sink = fallback_native._transcript

    results.check(
        "failed WebKit construction selects a complete native sink",
        fallback_sink.mode == "native"
        and fallback_sink._web is None
        and fallback_sink._scroller is not None
        and fallback_sink._chat_box is not None
        and fallback_sink.widget is fallback_sink._scroller
        and fallback_sink._empty_box is not None
        and direct_children(fallback_sink._chat_box) == [fallback_sink._empty_box],
    )
    results.check(
        "WebKit constructor fallback does not install native markdown CSS afterward",
        fallback_construction_trace == ["build"],
    )
    results.check(
        "transcript adapter is the single owner of backend and native mutable state",
        all(
            name not in fallback_native.__dict__
            for name in (
                "_web",
                "scroller",
                "chat_box",
                "_native_rows",
                "_empty_box",
                "_empty_icon",
                "_empty_title",
                "_empty_sub",
            )
        )
        and fallback_sink._native_rows is not requested_sink._native_rows,
    )
    theme_calls: list[str] = []
    real_theme_sync = fallback_sink.sync_empty_brand_icon
    fallback_sink.sync_empty_brand_icon = lambda: theme_calls.append("sync")
    fallback_native._sync_empty_brand_icon()
    fallback_sink.sync_empty_brand_icon = real_theme_sync
    results.check(
        "retained style callback reaches the icon through the owner interface",
        theme_calls == ["sync"],
    )
    results.check(
        "retained transcript entrypoints are explicit owner delegators",
        "Compatibility delegator for retained transcript consumers and tests."
        in (ChatSidebar._render_empty_transcript.__doc__ or "")
        and "Compatibility delegator for retained transcript consumers and tests."
        in (ChatSidebar._apply_restored_transcript.__doc__ or "")
        and not hasattr(ChatSidebar, "_append_message")
        and not hasattr(ChatSidebar, "_native_remove_message")
        and not hasattr(ChatSidebar, "_native_action_bar")
        and not hasattr(ChatSidebar, "_native_edit_user"),
    )

    fallback_native._apply_restored_transcript(
        [
            {"id": "native-user", "role": "user", "content": "hello"},
            {"id": "native-assistant", "role": "assistant", "content": "**hi**"},
        ]
    )
    results.check(
        "native replay replaces empty state with exact tracked message rows",
        fallback_sink._empty_box is None
        and fallback_sink._empty_icon.get_parent() is None
        and fallback_sink._empty_title.get_parent() is None
        and fallback_sink._empty_sub.get_parent() is None
        and list(fallback_sink._native_rows) == ["native-user", "native-assistant"]
        and direct_children(fallback_sink._chat_box)
        == [
            fallback_sink._native_rows["native-user"],
            fallback_sink._native_rows["native-assistant"],
        ],
    )

    removed_user_row = fallback_sink._native_rows["native-user"]
    fallback_sink.remove_native_message("native-user")
    fallback_sink.remove_native_message("missing-id")
    results.check(
        "native row removal pops only the requested tracked row without restoring empty state",
        removed_user_row.get_parent() is None
        and list(fallback_sink._native_rows) == ["native-assistant"]
        and direct_children(fallback_sink._chat_box)
        == [fallback_sink._native_rows["native-assistant"]]
        and fallback_sink._empty_box is None,
    )

    stale_row = fallback_sink._native_rows["native-assistant"]
    fallback_native._render_empty_transcript()
    first_reset_empty = fallback_sink._empty_box
    results.check(
        "native empty rendering replaces visible rows but leaves the row map untouched",
        first_reset_empty is not None
        and direct_children(fallback_sink._chat_box) == [first_reset_empty]
        and fallback_sink._native_rows == {"native-assistant": stale_row}
        and stale_row.get_parent() is None,
    )
    fallback_native._apply_restored_transcript([])
    results.check(
        "empty native replay clears tracked rows and rebuilds a fresh empty state",
        fallback_sink._native_rows == {}
        and fallback_sink._empty_box is not None
        and fallback_sink._empty_box is not first_reset_empty
        and direct_children(fallback_sink._chat_box) == [fallback_sink._empty_box],
    )

    replay_calls: list[tuple] = []
    generated_prefixes: list[str] = []
    real_append_message = fallback_sink.append_native_row
    fallback_sink.append_native_row = (
        lambda role, content, **kwargs: replay_calls.append((role, content, kwargs))
    )
    fallback_sink.rebind_message_id_provider(lambda prefix: (
        generated_prefixes.append(prefix) or f"generated-{prefix}"
    ))
    fallback_native._apply_restored_transcript(
        [
            {"id": "kept-user", "role": "user", "content": "prompt"},
            {"id": "", "role": "", "content": None},
            {"role": "tool", "content": "tool output"},
        ]
    )
    results.check(
        "native replay preserves user rows and defaults falsey role/content/IDs exactly",
        replay_calls
        == [
            ("user", "prompt", {"message_id": "kept-user"}),
            (
                "assistant",
                "",
                {"markdown": True, "message_id": "generated-assi"},
            ),
            (
                "assistant",
                "tool output",
                {"markdown": True, "message_id": "generated-tool"},
            ),
        ]
        and generated_prefixes == ["assi", "tool"],
    )
    fallback_sink.append_native_row = real_append_message
    fallback_sink.rebind_message_id_provider(fallback_native._next_msg_id)

    class RemovalStore:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str | None]] = []

        def delete_message(self, message_id: str, *, conversation_id=None) -> None:
            self.calls.append((message_id, conversation_id))

    fallback_store = fallback_native._store
    native_store = RemovalStore()
    fallback_native._store = native_store
    fallback_native._conversation_id = "native-conversation"
    fallback_native._messages = [
        {"id": "native-final", "role": "assistant", "content": "last"},
    ]
    fallback_native._apply_restored_transcript(fallback_native._messages)
    fallback_native._delete_message("native-final")
    results.check(
        "deleting the final native message removes, clears, and restores empty state",
        native_store.calls == [("native-final", "native-conversation")]
        and fallback_native._messages == []
        and fallback_sink._native_rows == {}
        and fallback_sink._empty_box is not None
        and direct_children(fallback_sink._chat_box) == [fallback_sink._empty_box],
    )

    native_store.calls.clear()
    fallback_native._messages = [
        {"id": "native-keep", "role": "user", "content": "keep"},
        {"id": "native-ui-keep", "role": "assistant", "content": "keep row"},
        {"id": "native-drop", "role": "assistant", "content": "drop row"},
    ]
    fallback_native._apply_restored_transcript(fallback_native._messages)
    fallback_native._drop_messages_from(1, keep_ui_id="native-ui-keep")
    results.check(
        "native tail removal preserves keep_ui_id while deleting persisted tail rows",
        fallback_native._messages
        == [{"id": "native-keep", "role": "user", "content": "keep"}]
        and native_store.calls
        == [
            ("native-ui-keep", "native-conversation"),
            ("native-drop", "native-conversation"),
        ]
        and list(fallback_sink._native_rows) == ["native-keep", "native-ui-keep"]
        and direct_children(fallback_sink._chat_box)
        == [
            fallback_sink._native_rows["native-keep"],
            fallback_sink._native_rows["native-ui-keep"],
        ],
    )

    class RecordingWeb:
        def __init__(self) -> None:
            self.calls: list[tuple[str, object]] = []

        def reset(self, messages) -> None:
            self.calls.append(("reset", messages))

        def post(self, event) -> None:
            self.calls.append(("post", event))

    class WebHarness:
        _render_empty_transcript = ChatSidebar._render_empty_transcript
        _apply_restored_transcript = ChatSidebar._apply_restored_transcript

        def __init__(self) -> None:
            self._transcript = TranscriptAdapter.__new__(TranscriptAdapter)
            self._transcript.mode = "webkit"
            self._transcript._web = RecordingWeb()
            self._streaming = False
            self._loading_model = False
            self._store = RemovalStore()
            self.native_removals: list[str] = []
            self._conversation = ConversationLifecycleController(
                store=self._store,  # type: ignore[arg-type]
                transient_parent=SimpleNamespace(),
                get_current_model=lambda: None,
                is_loading_model=lambda: self._loading_model,
                is_load_failed=lambda: False,
                is_streaming=lambda: self._streaming,
                reset_greetings=lambda: None,
                clear_native_rows=lambda: None,
                render_empty_transcript=lambda: None,
                apply_restored_transcript=lambda _messages: None,
                mark_history_dirty=lambda: None,
                rebuild_history_list=lambda: False,
                refresh_chat_title=lambda: False,
                set_status=lambda _text: None,
                show_ephemeral_greeting=lambda: None,
                sync_composer_hint=lambda: None,
                select_model_name=lambda *_a, **_k: None,
                save_last_model=lambda _model: None,
                is_ephemeral_greeting=lambda _role, _content: False,
                request_stop=lambda: None,
                invalidate_active_stream=lambda: None,
                grab_input_focus=lambda: None,
            )
            self._conversation.conversation_id = "web-conversation"
            self._message_actions = MessageActionController(
                get_store=lambda: self._store,  # type: ignore[arg-type]
                conversation=self._conversation,
                is_streaming=lambda: self._streaming,
                is_loading_model=lambda: self._loading_model,
                get_current_model=lambda: None,
                is_webkit=lambda: True,
                post_transcript=self._transcript.post,
                reset_empty_transcript=self._transcript.reset_empty,
                remove_native_message=lambda mid: self.native_removals.append(mid),
                append_native_message=lambda *_a, **_k: None,
                start_assistant_stream=lambda **_k: None,
            )

        @property
        def _conversation_id(self):
            return self._conversation.conversation_id

        @_conversation_id.setter
        def _conversation_id(self, value) -> None:
            self._conversation.conversation_id = value

        @property
        def _messages(self):
            return self._conversation.messages

        @_messages.setter
        def _messages(self, value) -> None:
            self._conversation.messages = value

        def _delete_message(self, message_id: str) -> None:
            self._message_actions.delete_message(message_id)

        def _drop_messages_from(self, idx: int, *, keep_ui_id: str | None = None) -> None:
            self._message_actions.drop_messages_from(idx, keep_ui_id=keep_ui_id)

    web_owner = WebHarness()
    web_payload = [
        {"id": "web-user", "role": "user", "content": "question"},
        {"id": "web-assistant", "role": "assistant", "content": "answer"},
    ]
    web_owner._apply_restored_transcript(web_payload)
    web_owner._render_empty_transcript()
    results.check(
        "WebKit replay forwards the original payload and empty reset exactly",
        web_owner._transcript._web.calls
        == [
            ("reset", web_payload),
            ("reset", []),
        ]
        and web_owner.native_removals == [],
    )

    from transcript_view import WebTranscriptView

    reset_events: list[dict] = []
    reset_recorder = SimpleNamespace(post=lambda event: reset_events.append(event))
    WebTranscriptView.reset(
        reset_recorder,
        [
            {},
            {"id": "", "role": "", "content": ""},
            {"id": None, "role": None, "content": None},
        ],
    )
    results.check(
        "WebKit reset allocates missing IDs while preserving its exact role/content defaults",
        reset_events
        == [
            {
                "type": "conversation_reset",
                "messages": [
                    {"id": "hist-0", "role": "assistant", "content": ""},
                    {"id": "hist-1", "role": "", "content": ""},
                    {"id": "hist-2", "role": None, "content": None},
                ],
            }
        ],
    )

    web_owner._transcript._web.calls.clear()
    web_owner._messages = [
        {"id": "web-first", "role": "user", "content": "first"},
        {"id": "web-second", "role": "assistant", "content": "second"},
    ]
    web_owner._delete_message("web-first")
    results.check(
        "deleting through WebKit posts each removal before the final empty reset",
        web_owner._messages == []
        and web_owner._store.calls
        == [
            ("web-first", "web-conversation"),
            ("web-second", "web-conversation"),
        ]
        and web_owner._transcript._web.calls
        == [
            ("post", {"type": "message_removed", "id": "web-first"}),
            ("post", {"type": "message_removed", "id": "web-second"}),
            ("reset", []),
        ]
        and web_owner.native_removals == [],
    )

    web_owner._transcript._web.calls.clear()
    web_owner._store.calls.clear()
    web_owner._messages = [
        {"id": "web-keep", "role": "user", "content": "keep"},
        {"id": "web-ui-keep", "role": "assistant", "content": "keep row"},
        {"id": "web-drop", "role": "assistant", "content": "drop row"},
    ]
    web_owner._drop_messages_from(1, keep_ui_id="web-ui-keep")
    results.check(
        "WebKit tail removal preserves keep_ui_id and posts only other removals",
        web_owner._messages
        == [{"id": "web-keep", "role": "user", "content": "keep"}]
        and web_owner._store.calls
        == [
            ("web-ui-keep", "web-conversation"),
            ("web-drop", "web-conversation"),
        ]
        and web_owner._transcript._web.calls
        == [("post", {"type": "message_removed", "id": "web-drop"})],
    )
    fallback_native._store = fallback_store
    requested_native.set_visible(False)
    fallback_native.set_visible(False)


def characterize_status_message_and_greeting(
    results: Results,
    app: Adw.Application,
) -> None:
    """Lock Phase-13 status-row and ephemeral-greeting behavior."""
    print("\n[0g] Status-message and greeting characterization", flush=True)

    class RecordingWeb:
        def __init__(self) -> None:
            self.calls: list[dict] = []

        def post(self, event: dict) -> None:
            self.calls.append(event)

    class WebHarness:
        _show_ephemeral_greeting = ChatSidebar._show_ephemeral_greeting

        def __init__(self) -> None:
            self._transcript = TranscriptAdapter.__new__(TranscriptAdapter)
            self._transcript.mode = "webkit"
            self._transcript._web = RecordingWeb()
            self._messages: list[dict] = []
            self.send_btn = _HealthWidget()
            self.id_prefixes: list[str] = []
            self.persisted: list[tuple] = []
            self._composer_cli = ComposerCliController(
                client=OllamaClient(),
                post_status=lambda mid, text, *, streaming=False: (
                    self._transcript.post_status_message(
                        mid, text, streaming=streaming
                    )
                ),
                update_status=lambda mid, text, *, done=False: (
                    self._transcript.update_status_message(mid, text, done=done)
                ),
                next_msg_id=self._next_msg_id,
                get_current_model=lambda: None,
                set_status=lambda _text: None,
                on_cli_busy_changed=lambda _busy: None,
                on_pull_succeeded=lambda: None,
                format_bytes=window_module._fmt_bytes,
            )

        def _next_msg_id(self, prefix: str) -> str:
            self.id_prefixes.append(prefix)
            return f"{prefix}-{len(self.id_prefixes)}"

        def _persist_message(self, *args, **kwargs) -> None:
            self.persisted.append((args, kwargs))

        def _post_status_message(self, text: str, *, streaming: bool = False) -> str:
            return self._composer_cli.post_status_message(text, streaming=streaming)

        def _update_status_message(
            self, mid: str, text: str, *, done: bool = False
        ) -> None:
            self._composer_cli.update_status_message(mid, text, done=done)

    web = WebHarness()
    web_mid = web._post_status_message("Downloading", streaming=True)
    web._update_status_message(web_mid, "Halfway")
    web._update_status_message(web_mid, "Finished", done=True)
    results.check(
        "WebKit status create, replace, and done events retain one allocated ID",
        web_mid == "asst-1"
        and web.id_prefixes == ["asst"]
        and web._transcript._web.calls
        == [
            {
                "type": "message_added",
                "id": "asst-1",
                "role": "assistant",
                "text": "Downloading",
                "streaming": True,
            },
            {
                "type": "message_reset",
                "id": "asst-1",
                "text": "Halfway",
                "streaming": True,
            },
            {"type": "message_done", "id": "asst-1", "text": "Finished"},
        ],
    )
    web._post_status_message("One shot")
    results.check(
        "WebKit non-streaming status creation preserves the false streaming flag",
        web._transcript._web.calls[-1]
        == {
            "type": "message_added",
            "id": "asst-2",
            "role": "assistant",
            "text": "One shot",
            "streaming": False,
        },
    )
    results.check(
        "WebKit status rows remain outside messages and persistence",
        web._messages == [] and web.persisted == [],
    )

    web._messages = [{"id": "existing", "role": "user", "content": "hello"}]
    web.send_btn.sensitive = False
    calls_before_guard = list(web._transcript._web.calls)
    web._show_ephemeral_greeting()
    results.check(
        "WebKit greeting is a strict no-op when messages exist",
        web._transcript._web.calls == calls_before_guard
        and web.send_btn.sensitive is False,
    )
    web._messages = []
    web._show_ephemeral_greeting()
    results.check(
        "WebKit greeting posts exact empty-state copy and separately enables send",
        web._transcript._web.calls[-1]
        == {
            "type": "empty_state",
            "title": window_module.GREETING_TEXT,
            "subtitle": window_module.GREETING_SUB,
        }
        and web.send_btn.sensitive is True,
    )

    with (
        patch.dict(os.environ, {"CHICKENBUTT_TRANSCRIPT": "native"}),
        patch.object(ChatSidebar, "_restore_history", lambda _self: None),
        patch.object(ChatSidebar, "_refresh_models", lambda _self: False),
    ):
        native = ChatSidebar(app, client=OllamaClient())
    pump(0.05)
    sink = native._transcript
    native._messages = []
    native.send_btn.set_sensitive(False)
    persisted: list[tuple] = []
    native._persist_message = lambda *args, **kwargs: persisted.append((args, kwargs))
    id_prefixes: list[str] = []
    native._next_msg_id = lambda prefix: (  # type: ignore[method-assign]
        id_prefixes.append(prefix) or f"{prefix}-status"
    )
    native._composer_cli.rebind_next_msg_id(native._next_msg_id)
    native._transcript.rebind_message_id_provider(native._next_msg_id)
    primitive_calls: list[tuple] = []
    real_append_native_row = sink.append_native_row

    def record_native_row(role, content, **kwargs):
        primitive_calls.append((role, content, kwargs))
        return real_append_native_row(role, content, **kwargs)

    sink.append_native_row = record_native_row
    native_mid = native._post_status_message("Native start", streaming=True)
    first_row = sink._native_rows[native_mid]
    native._update_status_message(native_mid, "Native update")
    second_row = sink._native_rows[native_mid]
    native._update_status_message(native_mid, "Native done", done=True)
    final_row = sink._native_rows[native_mid]
    results.check(
        "native status create, update, and done reuse one ID through the Phase-12 row primitive",
        native_mid == "asst-status"
        and id_prefixes == ["asst"]
        and primitive_calls
        == [
            (
                "assistant",
                "Native start",
                {"message_id": "asst-status", "markdown": True},
            ),
            (
                "assistant",
                "Native update",
                {"message_id": "asst-status", "markdown": True},
            ),
            (
                "assistant",
                "Native done",
                {"message_id": "asst-status", "markdown": True},
            ),
        ]
        and first_row is not second_row
        and second_row is not final_row
        and first_row.get_parent() is None
        and second_row.get_parent() is None
        and final_row.get_parent() is sink._chat_box
        and list(sink._native_rows) == ["asst-status"],
    )
    results.check(
        "native status rows remain outside messages and persistence",
        native._messages == [] and persisted == [],
    )

    sink.replay([])
    attached_empty = sink._empty_box
    native.send_btn.set_sensitive(False)
    native._show_ephemeral_greeting()
    results.check(
        "native greeting reuses an attached empty state and substitutes exact copy",
        sink._empty_box is attached_empty
        and sink._empty_box.get_parent() is sink._chat_box
        and sink._empty_title.get_label() == window_module.GREETING_TEXT
        and sink._empty_sub.get_label() == window_module.GREETING_SUB
        and native.send_btn.get_sensitive(),
    )

    sink._chat_box.remove(sink._empty_box)
    detached_empty = sink._empty_box
    native.send_btn.set_sensitive(False)
    native._show_ephemeral_greeting()
    results.check(
        "native greeting recreates a detached empty state before substituting copy",
        sink._empty_box is not detached_empty
        and detached_empty.get_parent() is None
        and direct_children(sink._chat_box) == [sink._empty_box]
        and sink._empty_title.get_label() == window_module.GREETING_TEXT
        and sink._empty_sub.get_label() == window_module.GREETING_SUB
        and native.send_btn.get_sensitive(),
    )

    native._messages = [{"id": "existing", "role": "user", "content": "hello"}]
    sink._chat_box.remove(sink._empty_box)
    guarded_empty = sink._empty_box
    native.send_btn.set_sensitive(False)
    native._show_ephemeral_greeting()
    results.check(
        "native greeting message guard prevents empty-state recreation and send changes",
        sink._empty_box is guarded_empty
        and sink._empty_box.get_parent() is None
        and direct_children(sink._chat_box) == []
        and not native.send_btn.get_sensitive(),
    )

    status_calls: list[tuple] = []
    greeting_calls: list[tuple[str, str]] = []
    real_post_status = sink.post_status_message
    real_update_status = sink.update_status_message
    real_present_empty = sink.present_empty_state
    sink.post_status_message = (
        lambda message_id, text, **kwargs: status_calls.append(
            ("post", message_id, text, kwargs)
        )
    )
    sink.update_status_message = (
        lambda message_id, text, **kwargs: status_calls.append(
            ("update", message_id, text, kwargs)
        )
    )
    sink.present_empty_state = (
        lambda title, subtitle: greeting_calls.append((title, subtitle))
    )
    native._messages = []
    native.send_btn.set_sensitive(False)
    delegated_mid = native._post_status_message("Delegated", streaming=True)
    native._update_status_message(delegated_mid, "Progress")
    native._update_status_message(delegated_mid, "Done", done=True)
    native._show_ephemeral_greeting()
    results.check(
        "status and greeting window entrypoints delegate transcript branching to the owner",
        delegated_mid == "asst-status"
        and status_calls
        == [
            ("post", "asst-status", "Delegated", {"streaming": True}),
            ("update", "asst-status", "Progress", {"done": False}),
            ("update", "asst-status", "Done", {"done": True}),
        ]
        and greeting_calls
        == [(window_module.GREETING_TEXT, window_module.GREETING_SUB)]
        and native.send_btn.get_sensitive(),
    )
    results.check(
        "greeting message policy and send enablement remain window-owned",
        "_messages" in ChatSidebar._show_ephemeral_greeting.__code__.co_names
        and "send_btn" in ChatSidebar._show_ephemeral_greeting.__code__.co_names
        and "present_empty_state"
        in ChatSidebar._show_ephemeral_greeting.__code__.co_names
        and "is_webkit" not in ChatSidebar._post_status_message.__code__.co_names
        and "is_webkit" not in ChatSidebar._update_status_message.__code__.co_names
        and "is_webkit"
        not in ChatSidebar._show_ephemeral_greeting.__code__.co_names
        and "post_status_message"
        in ChatSidebar._post_status_message.__code__.co_names
        and "update_status_message"
        in ChatSidebar._update_status_message.__code__.co_names
        and isinstance(native._composer_cli, ComposerCliController),
    )

    sink.post_status_message = real_post_status
    sink.update_status_message = real_update_status
    sink.present_empty_state = real_present_empty
    sink.append_native_row = real_append_native_row
    native.set_visible(False)


class _ScriptedChatStream:
    """Deterministic chat_stream used by Phase-15 stream-surface tests."""

    def __init__(
        self,
        chunks: list[str],
        *,
        error: Exception | None = None,
        gate_after_first: bool = False,
    ) -> None:
        self.chunks = chunks
        self.error = error
        self.gate_after_first = gate_after_first
        self.gate = threading.Event()
        self.started = threading.Event()
        self.finished = threading.Event()

    def __call__(self, model, messages, *, cancel_event=None):
        self.started.set()
        try:
            for index, chunk in enumerate(self.chunks):
                if index > 0 and self.gate_after_first:
                    self.gate.wait(timeout=5)
                    self.gate.clear()
                if cancel_event is not None and cancel_event.is_set():
                    return
                yield chunk
            if self.error is not None:
                raise self.error
        finally:
            self.finished.set()

    def release(self) -> None:
        self.gate.set()


def _button_by_tooltip(container: Gtk.Widget, tooltip: str) -> Gtk.Button | None:
    for child in direct_children(container):
        if isinstance(child, Gtk.Button) and child.get_tooltip_text() == tooltip:
            return child
    return None


def characterize_streaming_and_native_intent(
    results: Results,
    app: Adw.Application,
) -> None:
    """Lock Phase-15 stream finalization and native intent surfaces."""
    print(
        "\n[0h] Streaming-update/finalization and native-intent characterization",
        flush=True,
    )

    def prepare_owner(owner: ChatSidebar) -> None:
        owner._streaming = False
        owner._stream_generation = 0
        owner._active_stream_cancel = None
        conversation = owner._store.create_conversation(model="stream-model")
        owner._conversation_id = conversation.id
        owner._model_session.set_current_model("stream-model")
        owner._messages = [{"id": "user-1", "role": "user", "content": "hi"}]
        try:
            owner._store.append_message(
                conversation.id,
                role="user",
                content="hi",
                message_id="user-1",
            )
        except Exception:  # noqa: BLE001
            pass
        owner._apply_health = lambda *_args, **_kwargs: None
        owner._streaming_engine._apply_health = owner._apply_health
        owner._commit_calls: list[tuple] = []
        real_commit = owner._streaming_engine.commit_assistant_result

        def record_commit(aid, final, **kwargs):
            owner._commit_calls.append((aid, final, kwargs))
            return real_commit(aid, final, **kwargs)

        owner._streaming_engine.commit_assistant_result = (  # type: ignore[method-assign]
            record_commit
        )

    def drive_stream(
        owner: ChatSidebar,
        *,
        mode: str = "new",
        assistant_id: str | None = None,
        seed_text: str = "",
        chunks: list[str] | None = None,
        error: Exception | None = None,
        gate_after_first: bool = False,
        events: list[dict] | None = None,
        scroll_calls: list[str] | None = None,
        mutate_before_flush=None,
        manual_flushes: int | None = None,
    ) -> tuple[_ScriptedChatStream, list]:
        flushers: list = []
        scripted = _ScriptedChatStream(
            chunks or [],
            error=error,
            gate_after_first=gate_after_first,
        )
        owner.client.chat_stream = scripted  # type: ignore[method-assign]
        if events is not None:
            owner._transcript.post = lambda event: events.append(dict(event))
        if scroll_calls is not None:
            owner._transcript.scroll_to_end = lambda: scroll_calls.append("scroll")

        def capture_timeout(interval, callback):
            # _set_status("Thinking…") may also schedule the composer-hint fade.
            if getattr(callback, "__name__", "") == "flush_stream":
                flushers.append(callback)
            return 1

        with patch.object(
            streaming_engine_module.GLib,
            "timeout_add",
            side_effect=capture_timeout,
        ):
            owner._start_assistant_stream(
                mode=mode,
                assistant_id=assistant_id,
                seed_text=seed_text,
            )
        assert flushers, "stream begin must schedule flush_stream"
        if mutate_before_flush is not None:
            mutate_before_flush()
        if gate_after_first:
            wait_until(lambda: scripted.started.is_set(), timeout=5)
            flushers[0]()
            scripted.release()
            wait_until(lambda: scripted.finished.is_set(), timeout=5)
            if manual_flushes is None:
                while flushers[0]():
                    pass
            else:
                for _ in range(manual_flushes):
                    flushers[0]()
        else:
            wait_until(lambda: scripted.finished.is_set(), timeout=5)
            if manual_flushes is None:
                while flushers[0]():
                    pass
            else:
                for _ in range(manual_flushes):
                    flushers[0]()
        return scripted, flushers

    # --- WebKit begin modes, deltas, and finalization ---
    with (
        patch.object(ChatSidebar, "_restore_history", lambda _self: None),
        patch.object(ChatSidebar, "_refresh_models", lambda _self: False),
    ):
        web_owner = ChatSidebar(app, client=OllamaClient())
    pump(0.05)
    prepare_owner(web_owner)
    web_events: list[dict] = []
    drive_stream(web_owner, mode="new", chunks=["Hello"], events=web_events)
    results.check(
        "WebKit new begin posts streaming message_added before deltas and done",
        web_events[0]
        == {
            "type": "message_added",
            "id": web_events[0].get("id"),
            "role": "assistant",
            "text": "",
            "streaming": True,
        }
        and web_events[0]["id"].startswith("asst-")
        and {"type": "message_delta", "id": web_events[0]["id"], "text": "Hello"}
        in web_events
        and web_events[-1]
        == {
            "type": "message_done",
            "id": web_events[0]["id"],
            "text": "Hello",
        }
        and web_owner._commit_calls[-1][0] == web_events[0]["id"]
        and web_owner._commit_calls[-1][1] == "Hello",
    )

    prepare_owner(web_owner)
    web_events.clear()
    drive_stream(
        web_owner,
        mode="replace",
        assistant_id="asst-replace",
        chunks=["Replaced"],
        events=web_events,
    )
    results.check(
        "WebKit replace begin resets the assistant row to an empty streaming body",
        web_events[0]
        == {
            "type": "message_reset",
            "id": "asst-replace",
            "streaming": True,
            "text": "",
        }
        and web_events[-1]
        == {
            "type": "message_done",
            "id": "asst-replace",
            "text": "Replaced",
        },
    )

    prepare_owner(web_owner)
    web_events.clear()
    drive_stream(
        web_owner,
        mode="continue",
        assistant_id="asst-continue",
        seed_text="Seed",
        chunks=[" more"],
        events=web_events,
    )
    results.check(
        "WebKit continue begin reseeds with a blank-line boundary and joins final text",
        web_events[0]
        == {
            "type": "message_reset",
            "id": "asst-continue",
            "streaming": True,
            "text": "Seed\n\n",
        }
        and web_events[-1]
        == {
            "type": "message_done",
            "id": "asst-continue",
            "text": "Seed\n\n more",
        },
    )

    prepare_owner(web_owner)
    web_events.clear()
    drive_stream(web_owner, mode="new", chunks=[], events=web_events)
    results.check(
        "WebKit empty success finalizes as (no response)",
        web_events[-1]
        == {
            "type": "message_done",
            "id": web_events[0]["id"],
            "text": "(no response)",
        }
        and web_owner._commit_calls[-1][1] == "",
    )

    prepare_owner(web_owner)
    web_events.clear()
    drive_stream(
        web_owner,
        mode="new",
        chunks=["Partial"],
        error=OllamaError("boom"),
        events=web_events,
    )
    results.check(
        "WebKit error with partial text posts message_error and allows empty commit flag",
        web_events[-1]
        == {
            "type": "message_error",
            "id": web_events[0]["id"],
            "text": "Partial\n\n[Error: boom]",
        }
        and web_owner._commit_calls[-1][2].get("allow_empty") is True
        and web_owner._commit_calls[-1][1] == "Partial",
    )

    prepare_owner(web_owner)
    web_events.clear()
    drive_stream(
        web_owner,
        mode="new",
        chunks=[],
        error=OllamaError("empty-fail"),
        events=web_events,
    )
    results.check(
        "WebKit error without partial text posts Error: prefix only",
        web_events[-1]
        == {
            "type": "message_error",
            "id": web_events[0]["id"],
            "text": "Error: empty-fail",
        },
    )

    prepare_owner(web_owner)
    web_events.clear()
    drive_stream(
        web_owner,
        mode="new",
        chunks=["One", "Two"],
        gate_after_first=True,
        events=web_events,
    )
    delta_texts = [
        event["text"] for event in web_events if event.get("type") == "message_delta"
    ]
    results.check(
        "WebKit paced flushes post discrete deltas before the terminal done event",
        delta_texts == ["One", "Two"]
        and web_events[-1]["type"] == "message_done"
        and web_events[-1]["text"] == "OneTwo",
    )

    # --- Native begin modes, serial currentness, finalization, scroll ---
    with (
        patch.dict(os.environ, {"CHICKENBUTT_TRANSCRIPT": "native"}),
        patch.object(ChatSidebar, "_restore_history", lambda _self: None),
        patch.object(ChatSidebar, "_refresh_models", lambda _self: False),
    ):
        native_owner = ChatSidebar(app, client=OllamaClient())
    pump(0.05)
    sink = native_owner._transcript
    prepare_owner(native_owner)

    body_calls: list[tuple] = []
    scroll_calls: list[str] = []
    prepare_owner(native_owner)
    native_owner._messages = [{"id": "user-1", "role": "user", "content": "hi"}]
    real_append = sink.append_native_row

    def wrap_append(role, content, **kwargs):
        body = real_append(role, content, **kwargs)
        body_calls.append((role, content, dict(kwargs), body))
        real_append_stream = body.append_stream
        real_finish = body.finish_stream
        real_plain = body.set_plain
        body.append_stream = lambda chunk: (
            body_calls.append(("append_stream", chunk, {}, body))
            or real_append_stream(chunk)
        )
        body.finish_stream = lambda: (
            body_calls.append(("finish_stream", "", {}, body)) or real_finish()
        )
        body.set_plain = lambda text: (
            body_calls.append(("set_plain", text, {}, body)) or real_plain(text)
        )
        return body

    sink.append_native_row = wrap_append  # type: ignore[method-assign]
    drive_stream(
        native_owner,
        mode="new",
        chunks=["NativeHi"],
        scroll_calls=scroll_calls,
    )
    typing_begin = next(
        call
        for call in body_calls
        if call[0] == "assistant" and call[2].get("typing") is True
    )
    final_row = next(
        call
        for call in body_calls
        if call[0] == "assistant"
        and call[2].get("markdown") is True
        and call[1] == "NativeHi"
    )
    results.check(
        "native new begin uses a typing row, streams deltas, finishes, then replaces with an action row",
        typing_begin[1] == "···"
        and ("append_stream", "NativeHi", {}, typing_begin[3]) in body_calls
        and ("finish_stream", "", {}, typing_begin[3]) in body_calls
        and final_row[2].get("message_id") == typing_begin[2].get("message_id")
        and list(sink._native_rows)
        == [typing_begin[2].get("message_id")]
        and "scroll" in scroll_calls
        and not native_owner._streaming,
    )

    body_calls.clear()
    scroll_calls.clear()
    prepare_owner(native_owner)
    sink.append_native_row = wrap_append  # type: ignore[method-assign]
    drive_stream(
        native_owner,
        mode="replace",
        assistant_id="native-replace",
        chunks=["Rep"],
        scroll_calls=scroll_calls,
    )
    results.check(
        "native replace removes then rebuilds the same assistant id as a typing row",
        any(
            call[0] == "assistant"
            and call[2].get("message_id") == "native-replace"
            and call[2].get("typing") is True
            for call in body_calls
        )
        and any(
            call[0] == "assistant"
            and call[1] == "Rep"
            and call[2].get("markdown") is True
            and call[2].get("message_id") == "native-replace"
            for call in body_calls
        ),
    )

    body_calls.clear()
    prepare_owner(native_owner)
    sink.append_native_row = wrap_append  # type: ignore[method-assign]
    drive_stream(
        native_owner,
        mode="continue",
        assistant_id="native-continue",
        seed_text="Seed",
        chunks=["Tail"],
    )
    continue_begin = next(
        call
        for call in body_calls
        if call[0] == "assistant"
        and call[2].get("message_id") == "native-continue"
        and call[2].get("typing") is True
    )
    results.check(
        "native continue reseeds the typing row and appends the stream seed before deltas",
        continue_begin[1] == "Seed\n\n"
        and ("append_stream", "Seed\n\n", {}, continue_begin[3]) in body_calls
        and ("append_stream", "Tail", {}, continue_begin[3]) in body_calls
        and native_owner._commit_calls[-1][1] == "Seed\n\nTail",
    )

    body_calls.clear()
    prepare_owner(native_owner)
    sink.append_native_row = wrap_append  # type: ignore[method-assign]
    drive_stream(native_owner, mode="new", chunks=[])
    empty_body = next(
        call
        for call in body_calls
        if call[0] == "assistant" and call[2].get("typing") is True
    )[3]
    results.check(
        "native empty success uses set_plain('(no response)') and skips action-row replacement",
        ("set_plain", "(no response)", {}, empty_body) in body_calls
        and not any(
            call[0] == "assistant" and call[2].get("markdown") is True
            for call in body_calls
        ),
    )

    body_calls.clear()
    prepare_owner(native_owner)
    error_css: list[str] = []
    real_append_for_error = sink.append_native_row

    def wrap_append_error(role, content, **kwargs):
        body = real_append_for_error(role, content, **kwargs)
        body_calls.append((role, content, dict(kwargs), body))
        real_append_stream = body.append_stream
        real_finish = body.finish_stream
        real_plain = body.set_plain
        body.append_stream = lambda chunk: (
            body_calls.append(("append_stream", chunk, {}, body))
            or real_append_stream(chunk)
        )
        body.finish_stream = lambda: (
            body_calls.append(("finish_stream", "", {}, body)) or real_finish()
        )

        def capture_plain(text):
            parent = body.get_parent()
            if parent is not None:
                error_css.extend(parent.get_css_classes())
            body_calls.append(("set_plain", text, {}, body))
            return real_plain(text)

        body.set_plain = capture_plain
        return body

    sink.append_native_row = wrap_append_error  # type: ignore[method-assign]
    drive_stream(
        native_owner,
        mode="new",
        chunks=["Half"],
        error=OllamaError("native-boom"),
    )
    err_body = next(
        call
        for call in body_calls
        if call[0] == "assistant" and call[2].get("typing") is True
    )[3]
    typing_id = next(
        call[2].get("message_id")
        for call in body_calls
        if call[0] == "assistant" and call[2].get("typing") is True
    )
    results.check(
        "native error with partial text set_plains the error, marks the bubble, then replaces using the partial final text",
        ("set_plain", "Half\n\n[Error: native-boom]", {}, err_body) in body_calls
        and "chat-error" in error_css
        and any(
            call[0] == "assistant"
            and call[2].get("markdown") is True
            and call[1] == "Half"
            and call[2].get("message_id") == typing_id
            for call in body_calls
        ),
    )

    body_calls.clear()
    prepare_owner(native_owner)
    sink.append_native_row = wrap_append  # type: ignore[method-assign]
    stale_serial = {"body": None}

    def bump_serial() -> None:
        body = next(
            call[3]
            for call in body_calls
            if call[0] == "assistant" and call[2].get("typing") is True
        )
        stale_serial["body"] = body
        body._render_serial = body._render_serial + 1

    drive_stream(
        native_owner,
        mode="new",
        chunks=["Stale"],
        mutate_before_flush=bump_serial,
        manual_flushes=3,
    )
    results.check(
        "native stale _render_serial rejects flush/finalize side effects",
        stale_serial["body"] is not None
        and ("append_stream", "Stale", {}, stale_serial["body"]) not in body_calls
        and ("finish_stream", "", {}, stale_serial["body"]) not in body_calls
        and native_owner._commit_calls == []
        and native_owner._streaming,
    )
    # Recover the abandoned stream controls for later assertions.
    native_owner._streaming_engine.stream_finished()

    # --- Native action-bar and edit-dialog intent dispatch ---
    prepare_owner(native_owner)
    intent_calls: list[tuple] = []
    actions = native_owner._message_actions
    actions.clipboard_set = lambda text: intent_calls.append(("copy", text))
    actions.regenerate_message = lambda mid: intent_calls.append(("regen", mid))
    actions.continue_message = lambda mid: intent_calls.append(("continue", mid))
    actions.delete_message = lambda mid: intent_calls.append(("delete", mid))
    actions.edit_resend_message = lambda mid, text: intent_calls.append(
        ("edit_resend", mid, text)
    )
    native_owner._messages = [
        {"id": "asst-actions", "role": "assistant", "content": "stored answer"},
        {"id": "user-edit", "role": "user", "content": "stored prompt"},
    ]
    assistant_body = MessageBody(role="assistant")
    assistant_bar = sink.build_native_action_bar(
        "asst-actions",
        assistant_body,
        "fallback answer",
        role="assistant",
        is_user=False,
    )
    _button_by_tooltip(assistant_bar, "Copy response").emit("clicked")
    _button_by_tooltip(assistant_bar, "Regenerate response").emit("clicked")
    _button_by_tooltip(assistant_bar, "Continue generating").emit("clicked")
    _button_by_tooltip(assistant_bar, "Delete message").emit("clicked")
    more = next(
        child
        for child in direct_children(assistant_bar)
        if isinstance(child, Gtk.MenuButton)
    )
    pop = more.get_popover()
    md_btn = pop.get_child().get_first_child()
    md_btn.emit("clicked")
    results.check(
        "native assistant action bar dispatches copy/regen/continue/delete/markdown intents",
        intent_calls
        == [
            ("copy", "stored answer"),
            ("regen", "asst-actions"),
            ("continue", "asst-actions"),
            ("delete", "asst-actions"),
            ("copy", "stored answer"),
        ],
    )

    intent_calls.clear()
    user_body = MessageBody(role="user")
    user_bar = sink.build_native_action_bar(
        "user-edit",
        user_body,
        "fallback prompt",
        role="user",
        is_user=True,
    )
    results.check(
        "native user action bar exposes copy/edit/regen/delete without continue/more",
        _button_by_tooltip(user_bar, "Copy message") is not None
        and _button_by_tooltip(user_bar, "Edit message") is not None
        and _button_by_tooltip(user_bar, "Regenerate response") is not None
        and _button_by_tooltip(user_bar, "Delete message") is not None
        and _button_by_tooltip(user_bar, "Continue generating") is None
        and not any(
            isinstance(child, Gtk.MenuButton) for child in direct_children(user_bar)
        ),
    )

    dialogs: list = []
    real_dialog = transcript_adapter_module.Adw.MessageDialog

    class TrackingDialog(real_dialog):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            dialogs.append(self)

    with patch.object(
        transcript_adapter_module.Adw, "MessageDialog", TrackingDialog
    ):
        sink.edit_native_user("user-edit", "initial prompt")
    edit_dialog = dialogs[0]
    scroller = edit_dialog.get_extra_child()
    entry = scroller.get_child()
    buf = entry.get_buffer()
    results.check(
        "native edit dialog is seeded with the current prompt text",
        buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
        == "initial prompt",
    )
    edit_dialog.emit("response", "cancel")
    results.check(
        "native edit dialog cancel does not resend",
        intent_calls == [],
    )
    buf.set_text("   ")
    edit_dialog.emit("response", "save")
    results.check(
        "native edit dialog empty/whitespace save is a no-op",
        intent_calls == [],
    )
    buf.set_text(" revised prompt ")
    edit_dialog.emit("response", "save")
    results.check(
        "native edit dialog valid save strips and resends through _edit_resend_message",
        intent_calls == [("edit_resend", "user-edit", "revised prompt")],
    )

    # Typing rows omit the action bar; final rows include it.
    sink.append_native_row = real_append  # type: ignore[method-assign]
    typing_body = sink.append_native_row(
        "assistant", "···", typing=True, message_id="typing-row"
    )
    typing_row = sink._native_rows["typing-row"]
    typing_column = typing_row.get_first_child()
    final_body = sink.append_native_row(
        "assistant", "Done", markdown=True, message_id="final-row"
    )
    final_row_widget = sink._native_rows["final-row"]
    final_column = final_row_widget.get_first_child()
    results.check(
        "native typing rows omit the action bar while final rows include it",
        typing_body is not None
        and final_body is not None
        and len(direct_children(typing_column)) == 2  # bubble + meta
        and len(direct_children(final_column)) == 3,  # bubble + actions + meta
    )

    stream_code = StreamingEngineController.start_assistant_stream.__code__
    stream_names = set(stream_code.co_names)
    for const in stream_code.co_consts:
        if hasattr(const, "co_names"):
            stream_names.update(const.co_names)
    results.check(
        "streaming engine uses the opaque handle protocol without MessageBody internals",
        "begin_stream" in stream_names
        and "is_current_stream" in stream_names
        and "stream_delta" in stream_names
        and "stream_error" in stream_names
        and "finalize_stream" in stream_names
        and "replace_final_row" in stream_names
        and "MessageBody" not in stream_names
        and "_render_serial" not in stream_names
        and "append_stream" not in stream_names
        and "finish_stream" not in stream_names
        and "set_plain" not in stream_names
        and "_append_message" not in stream_names
        and "_native_remove_message" not in stream_names
        and isinstance(native_owner._streaming_engine, StreamingEngineController),
    )
    results.check(
        "native action/edit construction lives on the adapter; intent terminates at message actions",
        hasattr(sink, "build_native_action_bar")
        and hasattr(sink, "edit_native_user")
        and hasattr(sink, "rebind_on_intent")
        and hasattr(sink, "rebind_current_text_provider")
        and not hasattr(ChatSidebar, "_native_action_bar")
        and not hasattr(ChatSidebar, "_native_edit_user")
        and not hasattr(ChatSidebar, "_native_remove_message")
        and "_messages" not in sink.build_native_action_bar.__code__.co_names
        and "_edit_resend_message"
        not in sink.edit_native_user.__code__.co_names
        and "handle_intent" in ChatSidebar._on_web_intent.__code__.co_names
        and isinstance(native_owner._message_actions, MessageActionController)
        and sink._on_intent == native_owner._message_actions.handle_intent,
    )

    web_owner.set_visible(False)
    native_owner.set_visible(False)


def _ancestor_of_type(widget, cls):
    current = widget
    while current is not None:
        if isinstance(current, cls):
            return current
        current = current.get_parent()
    return None


def _widgets_of_type(root, widget_type) -> list:
    found: list = []

    def walk(node) -> None:
        if isinstance(node, widget_type):
            found.append(node)
        child = node.get_first_child() if hasattr(node, "get_first_child") else None
        while child is not None:
            walk(child)
            child = child.get_next_sibling()

    if root is not None:
        walk(root)
    return found


def characterize_ui_construction(
    results: Results,
    app: Adw.Application,
) -> None:
    """Lock UI-construction contracts before any window_view extraction."""
    print("\n[0h] UI-construction characterization", flush=True)

    current: dict = {"owner": None}
    events: list[tuple] = []
    connect_events: list[dict] = []
    idle_events: list[dict] = []
    ensure_events: list[str] = []

    real_init = ChatSidebar.__init__
    real_build_ui = ChatSidebar._build_ui
    real_transcript_init = TranscriptAdapter.__init__
    real_geometry_init = ComposerGeometry.__init__
    real_sidebar_init = SidebarHistoryController.__init__
    real_model_init = ModelLoadController.__init__
    real_health_init = HealthProbeController.__init__
    real_cli_init = ComposerCliController.__init__
    real_conversation_init = ConversationLifecycleController.__init__
    real_actions_init = MessageActionController.__init__
    real_engine_init = StreamingEngineController.__init__
    real_idle = window_module.GLib.idle_add
    real_connect = GObject.Object.connect
    real_ensure = window_module.ensure_md_css

    def tracking_init(self, application, client=None):
        current["owner"] = self
        events.append(("ChatSidebar.__init__", "enter"))
        real_init(self, application, client)
        events.append(("ChatSidebar.__init__", "leave"))

    def tracking_build_ui(owner) -> None:
        events.append(
            (
                "build_ui_enter",
                {
                    "has_requested_mode": hasattr(owner, "_requested_transcript_mode"),
                    "requested_mode": getattr(owner, "_requested_transcript_mode", None),
                    "transcript": owner._transcript,
                    "composer_geometry": owner._composer_geometry,
                    "sidebar_history": owner._sidebar_history,
                    "model_session": owner._model_session,
                },
            )
        )
        real_build_ui(owner)
        events.append(
            (
                "build_ui_leave",
                {
                    "transcript": type(owner._transcript).__name__,
                    "composer_geometry": type(owner._composer_geometry).__name__,
                    "sidebar_history": type(owner._sidebar_history).__name__,
                    "load_overlay": owner._load_overlay is not None,
                },
            )
        )

    def tracking_ensure() -> None:
        ensure_events.append("ensure_md_css")
        events.append(("ensure_md_css", current["owner"] is not None))
        return real_ensure()

    def tracking_transcript_init(self, *, requested_mode, **kwargs):
        owner = current["owner"]
        assert owner is not None
        events.append(
            (
                "TranscriptAdapter",
                {
                    "requested_mode": requested_mode,
                    "owner_requested_mode": getattr(
                        owner, "_requested_transcript_mode", None
                    ),
                    "composer_geometry": owner._composer_geometry,
                    "sidebar_history": owner._sidebar_history,
                    "input": owner.input,
                    "ensure_before": list(ensure_events),
                },
            )
        )
        return real_transcript_init(self, requested_mode=requested_mode, **kwargs)

    def tracking_geometry_init(self, **kwargs):
        owner = current["owner"]
        assert owner is not None
        events.append(
            (
                "ComposerGeometry",
                {
                    "input": owner.input is not None,
                    "input_scroll": owner._input_scroll is not None,
                    "placeholder": getattr(owner, "_placeholder", None) is not None,
                    "char_label": owner._composer_char_label is not None,
                    "transcript": isinstance(owner._transcript, TranscriptAdapter),
                    "sidebar_history": owner._sidebar_history,
                },
            )
        )
        return real_geometry_init(self, **kwargs)

    def tracking_sidebar_init(self, **kwargs):
        owner = current["owner"]
        assert owner is not None
        events.append(
            (
                "SidebarHistoryController",
                {
                    "sidebar": owner._sidebar is not None,
                    "sidebar_btn": owner._sidebar_btn is not None,
                    "history_list": owner._history_list is not None,
                    "chat_title_label": owner._chat_title_label is not None,
                    "composer_geometry": isinstance(
                        owner._composer_geometry, ComposerGeometry
                    ),
                    "transcript": isinstance(owner._transcript, TranscriptAdapter),
                    "load_overlay": owner._load_overlay is not None,
                    "root_overlay": owner._root_overlay is not None,
                },
            )
        )
        return real_sidebar_init(self, **kwargs)

    def tracking_model_init(self, **kwargs):
        owner = current["owner"]
        assert owner is not None
        events.append(
            (
                "ModelLoadController",
                {
                    "load_overlay": owner._load_overlay is not None,
                    "load_title": owner._load_title is not None,
                    "load_model_label": owner._load_model_label is not None,
                    "load_status": owner._load_status is not None,
                    "load_progress": owner._load_progress is not None,
                    "load_spinner": owner._load_spinner is not None,
                    "health_banner": owner._health_banner is not None,
                    "model_combo": owner.model_combo is not None,
                    "input": owner.input is not None,
                    "send_btn": owner.send_btn is not None,
                    "sidebar_btn": owner._sidebar_btn is not None,
                    "history_list": owner._history_list is not None,
                    "sidebar_history": isinstance(
                        owner._sidebar_history, SidebarHistoryController
                    ),
                },
            )
        )
        return real_model_init(self, **kwargs)

    def tracking_health_init(self, **kwargs):
        owner = current["owner"]
        assert owner is not None
        events.append(
            (
                "HealthProbeController",
                {
                    "model_session": isinstance(owner._model_session, ModelLoadController),
                    "model_combo": owner.model_combo is not None,
                    "health_banner": owner._health_banner is not None,
                    "health_title": owner._health_title is not None,
                    "health_detail": owner._health_detail is not None,
                    "health_action": owner._health_action_btn is not None,
                },
            )
        )
        return real_health_init(self, **kwargs)

    def tracking_cli_init(self, **kwargs):
        events.append(("ComposerCliController", True))
        return real_cli_init(self, **kwargs)

    def tracking_conversation_init(self, **kwargs):
        owner = current["owner"]
        assert owner is not None
        events.append(
            (
                "ConversationLifecycleController",
                {
                    "transcript": isinstance(owner._transcript, TranscriptAdapter),
                    "sidebar_history": isinstance(
                        owner._sidebar_history, SidebarHistoryController
                    ),
                    "model_session": isinstance(owner._model_session, ModelLoadController),
                },
            )
        )
        return real_conversation_init(self, **kwargs)

    def tracking_actions_init(self, **kwargs):
        events.append(("MessageActionController", True))
        return real_actions_init(self, **kwargs)

    def tracking_engine_init(self, **kwargs):
        owner = current["owner"]
        assert owner is not None
        events.append(
            (
                "StreamingEngineController",
                {
                    "conversation": isinstance(
                        owner._conversation, ConversationLifecycleController
                    ),
                    "message_actions": isinstance(
                        owner._message_actions, MessageActionController
                    ),
                    "transcript": isinstance(owner._transcript, TranscriptAdapter),
                    "input": owner.input is not None,
                    "send_btn": owner.send_btn is not None,
                    "stop_btn": owner.stop_btn is not None,
                },
            )
        )
        return real_engine_init(self, **kwargs)

    def tracking_idle(callback, *args, **kwargs):
        owner = current["owner"]
        target = getattr(callback, "__self__", None)
        idle_events.append(
            {
                "name": getattr(callback, "__name__", ""),
                "target_type": type(target).__name__ if target is not None else None,
                "sidebar_history_exists": (
                    owner is not None and owner._sidebar_history is not None
                ),
                "target_is_sidebar_history": (
                    owner is not None and target is owner._sidebar_history
                ),
            }
        )
        return real_idle(callback, *args, **kwargs)

    def tracking_connect(self, detailed_signal, handler, *args):
        owner = current["owner"]
        if owner is not None and detailed_signal in ("toggled", "row-activated"):
            connect_events.append(
                {
                    "signal": detailed_signal,
                    "handler": getattr(handler, "__name__", str(handler)),
                    "sidebar_history_exists": owner._sidebar_history is not None,
                    "on_sidebar_btn": self is owner._sidebar_btn,
                    "on_history_list": self is owner._history_list,
                }
            )
        return real_connect(self, detailed_signal, handler, *args)

    with (
        patch.dict(os.environ, {"CHICKENBUTT_TRANSCRIPT": "native"}),
        patch.object(ChatSidebar, "__init__", tracking_init),
        patch.object(ChatSidebar, "_build_ui", tracking_build_ui),
        patch.object(ChatSidebar, "_restore_history", lambda _self: None),
        patch.object(ChatSidebar, "_refresh_models", lambda _self: False),
        patch.object(window_module, "ensure_md_css", side_effect=tracking_ensure),
        patch.object(TranscriptAdapter, "__init__", tracking_transcript_init),
        patch.object(ComposerGeometry, "__init__", tracking_geometry_init),
        patch.object(SidebarHistoryController, "__init__", tracking_sidebar_init),
        patch.object(ModelLoadController, "__init__", tracking_model_init),
        patch.object(HealthProbeController, "__init__", tracking_health_init),
        patch.object(ComposerCliController, "__init__", tracking_cli_init),
        patch.object(
            ConversationLifecycleController, "__init__", tracking_conversation_init
        ),
        patch.object(MessageActionController, "__init__", tracking_actions_init),
        patch.object(StreamingEngineController, "__init__", tracking_engine_init),
        patch.object(window_module.GLib, "idle_add", side_effect=tracking_idle),
        patch.object(GObject.Object, "connect", tracking_connect),
    ):
        owner = ChatSidebar(app, client=OllamaClient())
    pump(0.05)

    event_kinds = [e[0] for e in events]
    controller_event_names = [
        "TranscriptAdapter",
        "ComposerGeometry",
        "SidebarHistoryController",
        "ModelLoadController",
        "HealthProbeController",
        "ComposerCliController",
        "ConversationLifecycleController",
        "MessageActionController",
        "StreamingEngineController",
    ]
    results.check(
        "each UI/runtime controller is constructed exactly once during ChatSidebar init",
        all(event_kinds.count(name) == 1 for name in controller_event_names),
        str({name: event_kinds.count(name) for name in controller_event_names}),
    )

    build_enter = next(payload for kind, payload in events if kind == "build_ui_enter")
    results.check(
        "build_ui starts with requested transcript mode and no controllers yet",
        build_enter["has_requested_mode"] is True
        and build_enter["requested_mode"] == "native"
        and build_enter["transcript"] is None
        and build_enter["composer_geometry"] is None
        and build_enter["sidebar_history"] is None
        and build_enter["model_session"] is None,
    )

    transcript_event = next(payload for kind, payload in events if kind == "TranscriptAdapter")
    results.check(
        "transcript backend mode is selected before TranscriptAdapter construction",
        transcript_event["requested_mode"] == "native"
        and transcript_event["owner_requested_mode"] == "native"
        and transcript_event["ensure_before"] == ["ensure_md_css"]
        and transcript_event["composer_geometry"] is None
        and transcript_event["sidebar_history"] is None
        and transcript_event["input"] is None,
    )
    results.check(
        "ensure_md_css precedes build_ui and TranscriptAdapter for requested-native construction",
        event_kinds.index("ensure_md_css") < event_kinds.index("build_ui_enter")
        < event_kinds.index("TranscriptAdapter"),
    )

    geometry_event = next(payload for kind, payload in events if kind == "ComposerGeometry")
    results.check(
        "composer widgets exist before ComposerGeometry construction",
        geometry_event["input"]
        and geometry_event["input_scroll"]
        and geometry_event["placeholder"]
        and geometry_event["char_label"]
        and geometry_event["transcript"] is True
        and geometry_event["sidebar_history"] is None,
    )

    sidebar_event = next(
        payload for kind, payload in events if kind == "SidebarHistoryController"
    )
    results.check(
        "sidebar widgets and prior owners exist before SidebarHistoryController construction",
        sidebar_event["sidebar"]
        and sidebar_event["sidebar_btn"]
        and sidebar_event["history_list"]
        and sidebar_event["chat_title_label"]
        and sidebar_event["composer_geometry"]
        and sidebar_event["transcript"]
        and sidebar_event["load_overlay"]
        and sidebar_event["root_overlay"],
    )

    model_event = next(payload for kind, payload in events if kind == "ModelLoadController")
    results.check(
        "load-overlay and chrome widgets exist before ModelLoadController construction",
        all(model_event.values()),
    )
    health_event = next(payload for kind, payload in events if kind == "HealthProbeController")
    results.check(
        "health widgets and model session exist before HealthProbeController construction",
        all(health_event.values()),
    )
    conversation_event = next(
        payload for kind, payload in events if kind == "ConversationLifecycleController"
    )
    results.check(
        "conversation lifecycle waits for transcript/sidebar/model owners",
        all(conversation_event.values()),
    )
    engine_event = next(
        payload for kind, payload in events if kind == "StreamingEngineController"
    )
    results.check(
        "streaming engine waits for conversation/actions/transcript/composer widgets",
        all(engine_event.values()),
    )

    sidebar_connects = [
        ev
        for ev in connect_events
        if ev["on_sidebar_btn"] or ev["on_history_list"]
    ]
    results.check(
        "sidebar toggle/row signals connect only after SidebarHistoryController exists",
        len(sidebar_connects) >= 2
        and all(ev["sidebar_history_exists"] for ev in sidebar_connects)
        and any(ev["signal"] == "toggled" and ev["on_sidebar_btn"] for ev in sidebar_connects)
        and any(
            ev["signal"] == "row-activated" and ev["on_history_list"]
            for ev in sidebar_connects
        ),
        str(sidebar_connects),
    )
    sidebar_idles = [
        ev
        for ev in idle_events
        if ev["name"] in ("rebuild_history_list", "refresh_chat_title")
    ]
    results.check(
        "sidebar idle callbacks are scheduled only after the sidebar owner exists",
        len(sidebar_idles) == 2
        and all(ev["sidebar_history_exists"] for ev in sidebar_idles)
        and all(ev["target_is_sidebar_history"] for ev in sidebar_idles)
        and {ev["name"] for ev in sidebar_idles}
        == {"rebuild_history_list", "refresh_chat_title"},
        str(sidebar_idles),
    )

    required_attrs = (
        "_sidebar",
        "_sidebar_btn",
        "_history_list",
        "_chat_title_label",
        "_status_label",
        "_refresh_btn",
        "_clear_btn",
        "_sidebar_new_btn",
        "_settings_btn",
        "model_combo",
        "_health_banner",
        "_health_title",
        "_health_detail",
        "_health_action_btn",
        "_transcript",
        "input",
        "_input_scroll",
        "_placeholder",
        "_composer_hint",
        "_composer_char_label",
        "send_btn",
        "stop_btn",
        "_composer_geometry",
        "_root_overlay",
        "_load_overlay",
        "_load_title",
        "_load_model_label",
        "_load_status",
        "_load_progress",
        "_load_spinner",
        "_sidebar_history",
        "_model_session",
        "_health_probe",
        "_composer_cli",
        "_conversation",
        "_message_actions",
        "_streaming_engine",
    )
    missing = [name for name in required_attrs if getattr(owner, name, None) is None]
    results.check(
        "post-build widget/controller attribute contract is fully populated",
        missing == [] and owner._new_chat_btn is None,
        f"missing={missing} new_chat_btn={owner._new_chat_btn!r}",
    )
    results.check(
        "status label reuses the chat title subtitle widget",
        owner._status_label is owner._chat_title_label,
    )
    results.check(
        "requested transcript mode is consumed during construction",
        not hasattr(owner, "_requested_transcript_mode")
        and owner._transcript.mode == "native",
    )

    action_names = (
        "new-chat",
        "toggle-sidebar",
        "settings",
        "export-current-md",
        "export-current-json",
        "hide",
        "maximize",
        "close",
        "refresh-models",
    )
    missing_actions = [name for name in action_names if owner.lookup_action(name) is None]
    results.check(
        "Gio window actions required by the header/menu are present",
        missing_actions == [],
        str(missing_actions),
    )
    accel_app = owner.get_application()
    results.check(
        "window action accelerators match construction wiring",
        accel_app is not None
        and list(accel_app.get_accels_for_action("win.hide")) == ["Escape"]
        and list(accel_app.get_accels_for_action("win.maximize")) == ["F11"]
        # Gtk normalizes <Primary> to the platform modifier (<Control> on Linux).
        and list(accel_app.get_accels_for_action("win.close")) == ["<Control>w"]
        and list(accel_app.get_accels_for_action("win.refresh-models"))
        == ["<Control>r"],
    )

    header = _ancestor_of_type(owner._chat_title_label, Adw.HeaderBar)
    menu_buttons = _widgets_of_type(header, Gtk.MenuButton)
    results.check(
        "header chrome disables CSD title buttons and hosts sidebar/clear/refresh/menu",
        header is not None
        and header.get_show_end_title_buttons() is False
        and header.get_show_start_title_buttons() is False
        and is_descendant(owner._sidebar_btn, header)
        and is_descendant(owner._clear_btn, header)
        and is_descendant(owner._refresh_btn, header)
        and len(menu_buttons) == 1
        and owner._sidebar_btn.get_active() is False
        and owner._sidebar.get_visible() is False,
        f"header={header!r} menus={len(menu_buttons)}",
    )
    # pack_end: menu first (rightmost), then refresh (immediately left of menu).
    menu_btn = menu_buttons[0] if menu_buttons else None
    refresh_parent = owner._refresh_btn.get_parent() if owner._refresh_btn else None
    menu_parent = menu_btn.get_parent() if menu_btn is not None else None
    start_parent = owner._sidebar_btn.get_parent() if owner._sidebar_btn else None
    results.check(
        "header packs refresh with the menu on the end side (refresh left of menu)",
        menu_btn is not None
        and refresh_parent is not None
        and refresh_parent is menu_parent
        and child_index(refresh_parent, owner._refresh_btn)
        < child_index(refresh_parent, menu_btn),
        f"refresh_idx={child_index(refresh_parent, owner._refresh_btn) if refresh_parent else -1} "
        f"menu_idx={child_index(menu_parent, menu_btn) if menu_parent and menu_btn else -1}",
    )
    results.check(
        "header packs sidebar toggle and clear on the start side",
        start_parent is not None
        and start_parent is owner._clear_btn.get_parent()
        and child_index(start_parent, owner._sidebar_btn)
        < child_index(start_parent, owner._clear_btn),
    )

    results.check(
        "load-overlay tree is attached hidden with required descendants",
        owner._load_overlay is not None
        and owner._root_overlay is not None
        and owner._load_overlay.get_parent() is owner._root_overlay
        and owner._root_overlay.get_child() is not owner._load_overlay
        and owner._load_overlay.get_visible() is False
        and "load-overlay" in owner._load_overlay.get_css_classes()
        and is_descendant(owner._load_title, owner._load_overlay)
        and is_descendant(owner._load_model_label, owner._load_overlay)
        and is_descendant(owner._load_status, owner._load_overlay)
        and is_descendant(owner._load_progress, owner._load_overlay)
        and is_descendant(owner._load_spinner, owner._load_overlay)
        and owner._load_title.get_label() == "Loading model"
        and owner._load_status.get_label() == "Connecting to Ollama…",
    )
    results.check(
        "controllers remain owned by ChatSidebar after construction",
        isinstance(owner._transcript, TranscriptAdapter)
        and isinstance(owner._composer_geometry, ComposerGeometry)
        and isinstance(owner._sidebar_history, SidebarHistoryController)
        and isinstance(owner._model_session, ModelLoadController)
        and isinstance(owner._health_probe, HealthProbeController)
        and isinstance(owner._composer_cli, ComposerCliController)
        and isinstance(owner._conversation, ConversationLifecycleController)
        and isinstance(owner._message_actions, MessageActionController)
        and isinstance(owner._streaming_engine, StreamingEngineController)
        and owner._transcript is not getattr(owner._composer_geometry, "_transcript", None)
        and owner._sidebar_history._sidebar is owner._sidebar
        and owner._model_session._load_overlay is owner._load_overlay
        and owner._streaming_engine._transcript is owner._transcript,
    )

    # WebKit-request fallback still selects native inside the adapter, before
    # any later ChatSidebar controller wiring observes the mode.
    fallback_modes: list[str] = []

    class FailingWebTranscriptView:
        def __init__(self, **_kwargs) -> None:
            raise RuntimeError("forced WebKit constructor failure")

    real_ta_init = TranscriptAdapter.__init__

    def capture_fallback_init(self, *, requested_mode, **kwargs):
        real_ta_init(self, requested_mode=requested_mode, **kwargs)
        fallback_modes.append(self.mode)

    with (
        patch.dict(os.environ, {"CHICKENBUTT_TRANSCRIPT": "webkit"}),
        patch.dict(
            sys.modules,
            {"transcript_view": SimpleNamespace(WebTranscriptView=FailingWebTranscriptView)},
        ),
        patch.object(TranscriptAdapter, "__init__", capture_fallback_init),
        patch.object(ChatSidebar, "_restore_history", lambda _self: None),
        patch.object(ChatSidebar, "_refresh_models", lambda _self: False),
    ):
        fallback_owner = ChatSidebar(app, client=OllamaClient())
    pump(0.05)
    results.check(
        "WebKit constructor fallback resolves to native before adapter construction returns",
        fallback_modes == ["native"]
        and fallback_owner._transcript.mode == "native"
        and not hasattr(fallback_owner, "_requested_transcript_mode"),
        str(fallback_modes),
    )
    fallback_owner.set_visible(False)
    owner.set_visible(False)


def characterize_sidebar_history_ui(
    results: Results,
    app: Adw.Application,
) -> None:
    """Lock Phase-17 sidebar/history UI methods and construction wiring."""
    print("\n[0i] Sidebar/history-UI characterization", flush=True)

    toggle_entries: list[bool] = []
    row_entries: list[str] = []
    idle_names: list[str] = []
    real_toggle = ChatSidebar._on_sidebar_toggled
    real_row = ChatSidebar._on_history_row_activated
    real_idle = window_module.GLib.idle_add

    def tracking_toggle(self, btn):
        toggle_entries.append(bool(self._sidebar_syncing))
        return real_toggle(self, btn)

    def tracking_row(self, listbox, row):
        row_entries.append(row.get_name() or "")
        return real_row(self, listbox, row)

    def tracking_idle(callback, *args, **kwargs):
        idle_names.append(getattr(callback, "__name__", ""))
        return real_idle(callback, *args, **kwargs)

    with (
        patch.object(ChatSidebar, "_restore_history", lambda _self: None),
        patch.object(ChatSidebar, "_refresh_models", lambda _self: False),
        patch.object(ChatSidebar, "_on_sidebar_toggled", tracking_toggle),
        patch.object(ChatSidebar, "_on_history_row_activated", tracking_row),
        patch.object(window_module.GLib, "idle_add", side_effect=tracking_idle),
    ):
        owner = ChatSidebar(app, client=OllamaClient())
    pump(0.05)
    sink = owner._sidebar_history

    results.check(
        "construction schedules exactly one idle rebuild and one idle title refresh",
        idle_names.count("rebuild_history_list") == 1
        and idle_names.count("refresh_chat_title") == 1,
    )

    toggle_entries.clear()
    owner._sidebar_syncing = True
    owner._sidebar_btn.emit("toggled")
    results.check(
        "sidebar toggle signal delivers exactly once through the recursion guard",
        toggle_entries == [True],
    )

    row_entries.clear()
    real_switch = owner.switch_conversation
    owner.switch_conversation = lambda _cid: None  # type: ignore[method-assign]
    probe_row = Gtk.ListBoxRow()
    probe_row.set_name("probe-conversation")
    owner._history_list.emit("row-activated", probe_row)
    results.check(
        "history row-activated signal delivers exactly once",
        row_entries == ["probe-conversation"],
    )
    owner.switch_conversation = real_switch  # type: ignore[method-assign]

    action_calls: list[tuple] = []
    real_toggle_sidebar = owner.toggle_sidebar

    def record_toggle_sidebar(show=None):
        action_calls.append((show,))
        return real_toggle_sidebar(show)

    owner.toggle_sidebar = record_toggle_sidebar  # type: ignore[method-assign]
    action = owner.lookup_action("toggle-sidebar")
    assert action is not None
    action.activate(None)
    results.check(
        "win.toggle-sidebar action activates toggle_sidebar exactly once",
        action_calls == [(None,)],
    )
    owner.toggle_sidebar = real_toggle_sidebar  # type: ignore[method-assign]

    nested: list[str] = []
    real_toggle_sidebar = owner.toggle_sidebar

    def counting_toggle(show=None):
        nested.append(f"enter:{show}")
        result = real_toggle_sidebar(show)
        nested.append(f"leave:{show}")
        return result

    owner.toggle_sidebar = counting_toggle  # type: ignore[method-assign]
    # Keep rebuild from mutating the list while proving the syncing guard.
    real_controller_rebuild = sink.rebuild_history_list
    sink.rebuild_history_list = lambda: False  # type: ignore[method-assign]
    owner._sidebar_syncing = True
    owner._sidebar.set_visible(False)
    owner._sidebar_btn.set_active(False)
    owner._sidebar_syncing = False
    owner._history_dirty = False
    nested.clear()
    owner.toggle_sidebar(True)
    results.check(
        "toggle_sidebar syncs the toggle button under _sidebar_syncing without re-entry",
        owner._sidebar.get_visible() is True
        and owner._sidebar_btn.get_active() is True
        and owner._sidebar_syncing is False
        and nested == ["enter:True", "leave:True"],
    )
    owner.toggle_sidebar = real_toggle_sidebar  # type: ignore[method-assign]
    sink.rebuild_history_list = real_controller_rebuild  # type: ignore[method-assign]

    syncing_calls: list[str] = []
    owner._sidebar_syncing = True
    owner._on_sidebar_toggled(owner._sidebar_btn)
    owner._sidebar_syncing = False

    def capture_toggle(show=None):
        syncing_calls.append(f"toggle:{show}")

    owner.toggle_sidebar = capture_toggle  # type: ignore[method-assign]
    owner._on_sidebar_toggled(owner._sidebar_btn)
    results.check(
        "_on_sidebar_toggled is a no-op while syncing and otherwise forwards button state",
        syncing_calls == [f"toggle:{owner._sidebar_btn.get_active()}"],
    )
    owner.toggle_sidebar = real_toggle_sidebar  # type: ignore[method-assign]

    owner._history_dirty = False
    sink.mark_dirty()
    results.check(
        "_mark_history_dirty sets the dirty flag",
        owner._history_dirty is True,
    )

    title = owner._chat_title_label
    assert title is not None
    title.set_text("seed-title")
    owner._model_session._loading_model = True
    owner._streaming = False
    loading_guard = sink.refresh_chat_title()
    loading_text = title.get_text()
    owner._model_session._loading_model = False
    owner._streaming = True
    streaming_guard = sink.refresh_chat_title()
    streaming_text = title.get_text()
    owner._streaming = False
    saved_label = sink._chat_title_label
    sink._chat_title_label = None
    missing_label = sink.refresh_chat_title()
    sink._chat_title_label = saved_label
    results.check(
        "_refresh_chat_title guards missing label, loading, and streaming",
        missing_label is False
        and loading_guard is False
        and streaming_guard is False
        and loading_text == "seed-title"
        and streaming_text == "seed-title",
    )

    owner._conversation_id = ""
    sink.refresh_chat_title()
    empty_title = title.get_text()
    conv = owner._store.create_conversation(model="title-model")
    owner._store.append_message(
        conv.id, role="user", content="seed", message_id="title-seed"
    )
    owner._store._conn.execute(
        "UPDATE conversations SET title = ? WHERE id = ?",
        ("  Stored Title  ", conv.id),
    )
    owner._conversation_id = conv.id
    sink.refresh_chat_title()
    stored_title = title.get_text()
    long = "L" * 60
    owner._store._conn.execute(
        "UPDATE conversations SET title = ? WHERE id = ?",
        (long, conv.id),
    )
    sink.refresh_chat_title()
    truncated_title = title.get_text()
    real_get_conversation = owner._store.get_conversation

    def boom_get_conversation(_cid):
        raise RuntimeError("title-store-boom")

    owner._store.get_conversation = boom_get_conversation  # type: ignore[method-assign]
    sink.refresh_chat_title()
    fallback_title = title.get_text()
    owner._store.get_conversation = real_get_conversation  # type: ignore[method-assign]
    results.check(
        "_refresh_chat_title uses store title, truncates past 48, and falls back on errors",
        empty_title == "New conversation"
        and stored_title == "Stored Title"
        and truncated_title == ("L" * 45) + "…"
        and fallback_title == "New conversation",
    )

    owner._conversation_id = conv.id

    saved_list = owner._history_list
    owner._history_list = None
    missing_list = sink.rebuild_history_list()
    owner._history_list = saved_list

    # Seed a non-empty clean list, then prove the dirty short-circuit.
    owner._history_dirty = True
    sink.rebuild_history_list()
    first_child = owner._history_list.get_first_child()
    select_calls: list[str] = []
    real_select = sink.select_active_history_row

    def record_select():
        select_calls.append("select")
        return real_select()

    sink.select_active_history_row = record_select  # type: ignore[method-assign]
    owner._history_dirty = False
    short_circuit = sink.rebuild_history_list()
    results.check(
        "_rebuild_history_list short-circuits when clean and non-empty",
        missing_list is False
        and short_circuit is False
        and select_calls == ["select"]
        and owner._history_list.get_first_child() is first_child
        and owner._history_dirty is False
        and first_child is not None
        and first_child.get_name() == conv.id,
    )
    sink.select_active_history_row = real_select  # type: ignore[method-assign]

    real_list_conversations = owner._store.list_conversations

    def boom_list_conversations(**_kwargs):
        raise RuntimeError("list-boom")

    owner._store.list_conversations = boom_list_conversations  # type: ignore[method-assign]
    owner._history_dirty = True
    sink.rebuild_history_list()
    error_row = owner._history_list.get_first_child()
    error_child = error_row.get_child() if error_row is not None else None
    error_label = (
        error_child.get_label() if isinstance(error_child, Gtk.Label) else None
    )
    results.check(
        "_rebuild_history_list treats list_conversations failures as an empty list",
        error_label == "No chats yet"
        and error_row is not None
        and error_row.get_sensitive() is False
        and owner._history_dirty is False,
    )
    owner._store.list_conversations = real_list_conversations  # type: ignore[method-assign]

    # Empty-store path with a throwaway store that returns [].
    empty_store_calls: list[str] = []

    class EmptyStore:
        def list_conversations(self, *, limit=40, nonempty_only=True):
            empty_store_calls.append(f"limit={limit}")
            return []

        def get_conversation(self, conversation_id):
            return None

    real_store = owner._store
    empty_store = EmptyStore()
    owner._store = empty_store  # type: ignore[assignment]
    sink._store = empty_store
    owner._history_dirty = True
    sink.rebuild_history_list()
    empty_row = owner._history_list.get_first_child()
    empty_child = empty_row.get_child() if empty_row is not None else None
    results.check(
        "_rebuild_history_list renders the empty-state placeholder and clears dirty",
        empty_store_calls == ["limit=40"]
        and empty_row is not None
        and isinstance(empty_child, Gtk.Label)
        and empty_child.get_label() == "No chats yet"
        and empty_row.get_sensitive() is False
        and owner._history_dirty is False
        and empty_row.get_next_sibling() is None,
    )
    owner._store = real_store
    sink._store = real_store

    active = owner._store.create_conversation(model="active-model")
    other = owner._store.create_conversation(model="other-model")
    owner._store.append_message(
        active.id, role="user", content="active", message_id="active-seed"
    )
    owner._store.append_message(
        other.id, role="user", content="other", message_id="other-seed"
    )
    owner._store._conn.execute(
        "UPDATE conversations SET title = ? WHERE id = ?",
        ("Active Chat", active.id),
    )
    owner._store._conn.execute(
        "UPDATE conversations SET title = ? WHERE id = ?",
        ("X" * 50, other.id),
    )
    owner._conversation_id = active.id
    title_calls: list[str] = []
    real_refresh = sink.refresh_chat_title

    def record_refresh():
        title_calls.append("refresh")
        return real_refresh()

    sink.refresh_chat_title = record_refresh  # type: ignore[method-assign]
    owner._history_dirty = True
    sink.rebuild_history_list()
    rows = direct_children(owner._history_list)
    row_by_id = {
        row.get_name(): row
        for row in rows
        if isinstance(row, Gtk.ListBoxRow) and row.get_name()
    }
    active_outer = row_by_id[active.id].get_child()
    other_outer = row_by_id[other.id].get_child()
    active_title = active_outer.get_first_child().get_first_child().get_label()
    other_title = other_outer.get_first_child().get_first_child().get_label()
    selected = owner._history_list.get_selected_row()
    results.check(
        "_rebuild_history_list builds truncated rows, selects the active chat, and refreshes the title",
        set(row_by_id) >= {active.id, other.id}
        and active_title == "Active Chat"
        and other_title == ("X" * 33) + "…"
        and selected is row_by_id[active.id]
        and title_calls == ["refresh"]
        and owner._history_dirty is False,
    )
    sink.refresh_chat_title = real_refresh  # type: ignore[method-assign]

    owner._conversation_id = other.id
    owner._select_active_history_row()
    results.check(
        "_select_active_history_row selects the row matching _conversation_id",
        owner._history_list.get_selected_row() is row_by_id[other.id],
    )
    owner._conversation_id = ""
    owner._history_list.select_row(row_by_id[active.id])
    owner._select_active_history_row()
    results.check(
        "_select_active_history_row is a no-op without an active conversation id",
        owner._history_list.get_selected_row() is row_by_id[active.id],
    )

    switch_calls: list[str] = []
    sink.rebind_on_activate(lambda cid: switch_calls.append(cid))
    blank = Gtk.ListBoxRow()
    blank.set_name("")
    owner._on_history_row_activated(owner._history_list, blank)
    owner._on_history_row_activated(owner._history_list, row_by_id[active.id])
    results.check(
        "_on_history_row_activated ignores empty ids and switches on a real row",
        switch_calls == [active.id],
    )
    sink.rebind_on_activate(owner._conversation.switch_conversation)

    export_calls: list[tuple[str, str]] = []
    delete_calls: list[str] = []
    sink._on_export = (  # type: ignore[method-assign]
        lambda cid, fmt: export_calls.append((cid, fmt))
    )
    sink.rebind_on_delete(lambda cid: delete_calls.append(cid))
    pop = owner._make_chat_actions_popover(active.id)
    box = pop.get_child()
    md_btn = _button_by_tooltip(box, "Export Markdown")
    json_btn = _button_by_tooltip(box, "Export JSON")
    delete_btn = _button_by_tooltip(box, "Delete chat")
    md_btn.emit("clicked")
    json_btn.emit("clicked")
    delete_btn.emit("clicked")
    results.check(
        "_make_chat_actions_popover dispatches markdown/json export and delete confirm",
        md_btn is not None
        and json_btn is not None
        and delete_btn is not None
        and export_calls == [(active.id, "md"), (active.id, "json")]
        and delete_calls == [active.id],
    )

    # Rebuild attaches a live popover on each row's overflow button.
    owner._history_dirty = True
    owner._conversation_id = active.id
    sink.rebuild_history_list()
    live_row = next(
        row
        for row in direct_children(owner._history_list)
        if isinstance(row, Gtk.ListBoxRow) and row.get_name() == active.id
    )
    live_more = live_row.get_child().get_last_child()
    live_pop = live_more.get_popover()
    live_box = live_pop.get_child()
    results.check(
        "rebuilt history rows attach a chat-actions popover on the overflow button",
        isinstance(live_more, Gtk.MenuButton)
        and live_pop is not None
        and _button_by_tooltip(live_box, "Export Markdown") is not None
        and _button_by_tooltip(live_box, "Export JSON") is not None
        and _button_by_tooltip(live_box, "Delete chat") is not None,
    )

    rebound: list[str] = []
    sink.rebind_active_conversation_id(lambda: "rebound-id")
    sink.rebind_on_activate(lambda cid: rebound.append(f"activate:{cid}"))
    sink.rebind_on_delete(lambda cid: rebound.append(f"delete:{cid}"))
    sink.on_history_row_activated(owner._history_list, row_by_id[active.id])
    pop = sink.make_chat_actions_popover("rebind-delete")
    _button_by_tooltip(pop.get_child(), "Delete chat").emit("clicked")
    results.check(
        "Phase 22 activate/delete and active-ID providers can be rebound",
        rebound == [f"activate:{active.id}", "delete:rebind-delete"]
        and sink._get_active_conversation_id() == "rebound-id",
    )
    sink.rebind_active_conversation_id(
        lambda: owner._conversation.conversation_id or ""
    )
    sink.rebind_on_activate(owner._conversation.switch_conversation)
    sink.rebind_on_delete(owner._conversation.confirm_delete_conversation)

    results.check(
        "sidebar history controller owns dirty/syncing state and window entrypoints delegate",
        isinstance(sink, SidebarHistoryController)
        and "_history_dirty" not in owner.__dict__
        and "_sidebar_syncing" not in owner.__dict__
        and not hasattr(ChatSidebar, "_mark_history_dirty")
        and not hasattr(ChatSidebar, "_rebuild_history_list")
        and not hasattr(ChatSidebar, "_refresh_chat_title")
        and "toggle_sidebar" in ChatSidebar.toggle_sidebar.__code__.co_names
        and "Intentional public window entrypoint"
        in (ChatSidebar.toggle_sidebar.__doc__ or ""),
    )

    owner.set_visible(False)


class _CliClient:
    def __init__(self) -> None:
        self.pull_chunks: list[dict] = []
        self.pull_error: BaseException | None = None
        self.info_error: BaseException | None = None
        self.list_text = "MODEL-A"
        self.ps_text = "RUNNING-A"
        self.pull_calls: list[str] = []
        self.info_calls: list[str] = []

    def pull_model(self, model: str):
        self.pull_calls.append(model)
        if self.pull_error is not None:
            raise self.pull_error
        yield from self.pull_chunks

    def format_list_models(self) -> str:
        self.info_calls.append("list")
        if self.info_error is not None:
            raise self.info_error
        return self.list_text

    def format_ps_models(self) -> str:
        self.info_calls.append("ps")
        if self.info_error is not None:
            raise self.info_error
        return self.ps_text


class _CliTranscript:
    def __init__(self) -> None:
        self.posts: list[tuple[str, str, bool]] = []
        self.updates: list[tuple[str, str, bool]] = []

    def post_status_message(
        self, mid: str, text: str, *, streaming: bool = False
    ) -> None:
        self.posts.append((mid, text, streaming))

    def update_status_message(
        self, mid: str, text: str, *, done: bool = False
    ) -> None:
        self.updates.append((mid, text, done))


class _CliBuffer:
    def __init__(self, text: str = "") -> None:
        self.text = text

    def get_start_iter(self):
        return None

    def get_end_iter(self):
        return None

    def get_text(self, *_args):
        return self.text

    def set_text(self, text: str, _n: int = -1) -> None:
        self.text = text


class _CliInput:
    def __init__(self, text: str = "") -> None:
        self._buffer = _CliBuffer(text)

    def get_buffer(self) -> _CliBuffer:
        return self._buffer


class _CliHarness(ComposerCliController):
    """Deterministic ComposerCliController for Phase-19/20 characterization."""

    def __init__(self) -> None:
        self._transcript = _CliTranscript()
        self.input = _CliInput()
        self.send_btn = _HealthWidget()
        self.send_btn.sensitive = True
        self._messages: list[dict] = []
        self._streaming = False
        self._loading_model = False
        self._load_failed = False
        self._model = "alpha"
        self._health = SimpleNamespace(can_chat=True)
        self.id_prefixes: list[str] = []
        self.statuses: list[str] = []
        self.refresh_calls = 0
        self.order: list[object] = []
        self.persisted: list[tuple] = []
        super().__init__(
            client=_CliClient(),
            post_status=lambda mid, text, *, streaming=False: (
                self._transcript.post_status_message(mid, text, streaming=streaming)
            ),
            update_status=lambda mid, text, *, done=False: (
                self._transcript.update_status_message(mid, text, done=done)
            ),
            next_msg_id=self._alloc_id,
            get_current_model=lambda: self._model,
            set_status=self._record_status,
            on_cli_busy_changed=self._apply_send_sensitivity,
            on_pull_succeeded=self._record_refresh,
            format_bytes=window_module._fmt_bytes,
        )
        conversation = SimpleNamespace(
            messages=self._messages,
            conversation_id="cli-cid",
            next_msg_id=self._alloc_id,
            append_local=lambda message: self._messages.append(message),
            persist_message=lambda *_args, **_kwargs: None,
        )
        self._streaming_engine = StreamingEngineController(
            client=OllamaClient(),
            get_store=lambda: None,  # type: ignore[arg-type]
            conversation=conversation,  # type: ignore[arg-type]
            message_actions=SimpleNamespace(  # type: ignore[arg-type]
                api_messages=lambda: [],
                find_message_index=lambda _mid: -1,
            ),
            transcript=SimpleNamespace(  # type: ignore[arg-type]
                is_webkit=True,
                post=lambda _event: None,
                append_native_row=lambda *_a, **_k: None,
            ),
            get_current_model=lambda: self._model,
            is_loading_model=lambda: self._loading_model,
            get_health=lambda: self._health,
            refresh_models=lambda: True,
            apply_health=lambda _state: None,
            set_status=lambda _text: None,
            sync_composer_hint=lambda: None,
            is_cli_busy=lambda: self.is_busy(),
            try_command=lambda text: self.try_command(text),
            input_widget=self.input,
            send_control=None,
            stop_control=None,
        )
        self._streaming_engine.start_assistant_stream = (  # type: ignore[method-assign]
            lambda **_kwargs: None
        )
        self._streaming_engine._streaming = False

    def _send(self) -> None:
        """Exercise Phase-26 send guards against this CLI harness."""
        self._streaming_engine._streaming = self._streaming
        self._streaming_engine.input = self.input
        self._streaming_engine.send()

    def _alloc_id(self, prefix: str) -> str:
        self.id_prefixes.append(prefix)
        return f"{prefix}-{len(self.id_prefixes)}"

    def _record_status(self, text: str) -> None:
        self.order.append(("status", text))
        self.statuses.append(text)

    def _record_refresh(self) -> None:
        self.order.append("refresh")
        self.refresh_calls += 1

    def _apply_send_sensitivity(self, busy: bool) -> None:
        if busy:
            self.send_btn.set_sensitive(False)
            return
        self.send_btn.set_sensitive(
            bool(self._model)
            and not self._streaming
            and not self._loading_model
            and not self._load_failed
        )

    def set_busy(self, busy: bool) -> None:
        self.order.append(("busy", busy))
        self._ollama_cli_busy = busy
        self._on_cli_busy_changed(busy)

    def post_status_message(self, text: str, *, streaming: bool = False) -> str:
        mid = super().post_status_message(text, streaming=streaming)
        self.order.append(("post", mid, streaming))
        return mid

    def update_status_message(
        self, mid: str, text: str, *, done: bool = False
    ) -> None:
        self.order.append(("update", mid, done, text))
        super().update_status_message(mid, text, done=done)

    # Compatibility names retained so Phase-19 assertion strings stay meaningful.
    def _try_composer_command(self, text: str) -> bool:
        return self.try_command(text)

    def _composer_cmd_busy(self) -> bool:
        return self.is_busy()

    def _set_composer_cmd_busy(self, busy: bool) -> None:
        self.set_busy(busy)

    def _post_status_message(self, text: str, *, streaming: bool = False) -> str:
        return self.post_status_message(text, streaming=streaming)

    def _update_status_message(
        self, mid: str, text: str, *, done: bool = False
    ) -> None:
        self.update_status_message(mid, text, done=done)

    def _format_pull_progress(self, chunk: dict) -> str:
        return self.format_pull_progress(chunk)

    def _run_ollama_pull(self, model: str) -> None:
        self.run_pull(model)

    def _run_ollama_info(self, kind: str) -> None:
        self.run_info(kind)


def characterize_composer_cli_commands(results: Results) -> None:
    """Lock every Phase-20 composer-CLI method plus `_send`'s CLI integrations."""
    print("\n[0i] Composer CLI-command characterization", flush=True)

    threads: list[object] = []

    class CapturingThread:
        def __init__(self, *, target, daemon: bool = False) -> None:
            self.target = target
            self.daemon = daemon

        def start(self) -> None:
            threads.append(self)

    def run_with_worker(start) -> None:
        threads.clear()
        idles: list[tuple] = []
        with (
            patch.object(composer_cli_module.threading, "Thread", CapturingThread),
            patch.object(
                composer_cli_module.GLib,
                "idle_add",
                side_effect=lambda callback, *args: (
                    idles.append((callback, args)) or 1
                ),
            ),
        ):
            start()
            if threads:
                threads[-1].target()
            for callback, args in list(idles):
                callback(*args)

    fmt = _CliHarness().format_pull_progress
    results.check(
        "_format_pull_progress maps status underscores, bytes, percent, and digests",
        fmt({"status": "pulling_manifest"}) == "pulling manifest"
        and fmt(
            {"status": "downloading", "completed": 1024, "total": 2048}
        )
        == "downloading · 1.0 KB / 2.0 KB (50%)"
        and fmt({"status": "verifying", "digest": "sha256:abcdefghijklmnopqr"})
        == "verifying · sha256:abcde…"
        and fmt({}) == "Working",
    )

    busy = _CliHarness()
    busy._set_composer_cmd_busy(True)
    busy_flag = busy._composer_cmd_busy()
    busy.send_btn.sensitive = True
    busy._model = "alpha"
    busy._streaming = False
    busy._loading_model = False
    busy._load_failed = False
    busy._set_composer_cmd_busy(False)
    idle_enabled = busy.send_btn.sensitive
    busy._model = ""
    busy._set_composer_cmd_busy(False)
    idle_disabled = busy.send_btn.sensitive
    busy._set_composer_cmd_busy(True)
    results.check(
        "_set_composer_cmd_busy owns the flag and toggles only the send button",
        busy_flag is True
        and busy._composer_cmd_busy() is True
        and idle_enabled is True
        and idle_disabled is False
        and busy.send_btn.sensitive is False,
    )

    status = _CliHarness()
    mid = status._post_status_message("hello", streaming=True)
    status._update_status_message(mid, "next")
    status._update_status_message(mid, "done", done=True)
    results.check(
        "status create/update stay non-persisted and allocate one assistant ID",
        mid == "asst-1"
        and status.id_prefixes == ["asst"]
        and status._messages == []
        and status.persisted == []
        and status._transcript.posts == [("asst-1", "hello", True)]
        and status._transcript.updates
        == [
            ("asst-1", "next", False),
            ("asst-1", "done", True),
        ],
    )

    router = _CliHarness()
    routed: list[tuple] = []
    router.run_pull = lambda model: routed.append(("pull", model))  # type: ignore[method-assign]
    router.run_info = lambda kind: routed.append(("info", kind))  # type: ignore[method-assign]
    non_command = router._try_composer_command("plain chat")
    pull_ok = router._try_composer_command("  ollama pull llama3.2  ")
    list_ok = router._try_composer_command("ollama list")
    ps_ok = router._try_composer_command("OLLAMA PS")
    help_ok = router._try_composer_command("ollama rm unused")
    help_text = router._transcript.posts[-1][1] if router._transcript.posts else ""
    results.check(
        "_try_composer_command routes pull/list/ps, rejects non-commands, and helps unknowns",
        non_command is False
        and pull_ok is True
        and list_ok is True
        and ps_ok is True
        and help_ok is True
        and routed
        == [
            ("pull", "llama3.2"),
            ("info", "list"),
            ("info", "ps"),
        ]
        and "Composer command not recognized." in help_text
        and "`ollama pull <model-name>`" in help_text
        and "`ollama list`" in help_text
        and "`ollama ps`" in help_text,
    )

    already = _CliHarness()
    already._ollama_cli_busy = True
    already._run_ollama_pull("alpha")
    already._run_ollama_info("list")
    results.check(
        "pull and info reject when another composer command is already busy",
        already.client.pull_calls == []
        and already.client.info_calls == []
        and len(already._transcript.posts) == 2
        and all(
            "already running" in post[1] for post in already._transcript.posts
        ),
    )

    progress = _CliHarness()
    progress.client.pull_chunks = [
        {"status": "pulling_manifest"},
        {"status": "downloading", "completed": 10, "total": 100},
        {"status": "downloading", "completed": 40, "total": 100},
        {"status": "downloading", "completed": 40, "total": 100},
        {"status": "verifying sha256 digest"},
    ]
    progress.order.clear()
    run_with_worker(lambda: progress._run_ollama_pull("alpha"))

    def update_texts(owner: _CliHarness, *, done: bool | None = None) -> list[str]:
        texts: list[str] = []
        for item in owner.order:
            if not (isinstance(item, tuple) and item and item[0] == "update"):
                continue
            _kind, _mid, is_done, text = item
            if done is None or is_done is done:
                texts.append(text)
        return texts

    progressive = update_texts(progress, done=False)
    final_update = update_texts(progress, done=True)[-1]
    results.check(
        "pull progress replaces same-phase percentages, suppresses redundant UI, and completes",
        progressive
        == [
            "**Pulling** `alpha`…\n\n- pulling manifest",
            (
                "**Pulling** `alpha`…\n\n- pulling manifest\n"
                "- downloading · 10 B / 100 B (10%)"
            ),
            (
                "**Pulling** `alpha`…\n\n- pulling manifest\n"
                "- downloading · 40 B / 100 B (40%)"
            ),
            (
                "**Pulling** `alpha`…\n\n- pulling manifest\n"
                "- downloading · 40 B / 100 B (40%)\n"
                "- verifying sha256 digest"
            ),
        ]
        and "**Pull complete:** `alpha`" in final_update
        and progress.refresh_calls == 1
        and progress._composer_cmd_busy() is False
        and progress.order[-3:]
        == [
            (
                "update",
                "asst-1",
                True,
                final_update,
            ),
            ("busy", False),
            "refresh",
        ],
    )

    capped = _CliHarness()
    capped.client.pull_chunks = [
        {"status": f"phase-{index}"} for index in range(14)
    ]
    run_with_worker(lambda: capped._run_ollama_pull("beta"))
    last_cap = update_texts(capped, done=False)[-1]
    cap_lines = [
        line[2:]
        for line in last_cap.splitlines()
        if line.startswith("- ")
    ]
    results.check(
        "pull progress keeps a rolling 12-line history",
        cap_lines
        == [f"phase-{index}" for index in range(2, 14)],
    )

    eof = _CliHarness()
    eof.client.pull_chunks = [{"status": "downloading", "completed": 1, "total": 2}]
    run_with_worker(lambda: eof._run_ollama_pull("gamma"))
    results.check(
        "pull treats clean EOF without an explicit success chunk as success",
        eof.refresh_calls == 1
        and any(
            "**Pull complete:** `gamma`" in text
            for text in update_texts(eof, done=True)
        ),
    )

    for label, error in (
        ("OllamaError", OllamaError("pull denied")),
        ("generic exception", RuntimeError("socket dead")),
    ):
        failed = _CliHarness()
        failed.client.pull_error = error
        failed.order.clear()
        run_with_worker(lambda owner=failed: owner._run_ollama_pull("delta"))
        final = update_texts(failed, done=True)[-1]
        results.check(
            f"pull {label} finalizes the status row, clears busy, then restores status",
            f"**Pull failed:** `delta`" in final
            and str(error) in final
            and failed.refresh_calls == 0
            and failed._composer_cmd_busy() is False
            and failed.order[-3:]
            == [
                ("update", "asst-1", True, final),
                ("busy", False),
                ("status", "alpha"),
            ],
        )

    listed = _CliHarness()
    run_with_worker(lambda: listed._run_ollama_info("list"))
    list_final = update_texts(listed, done=True)[-1]
    results.check(
        "info list posts structured text and restores status after clearing busy",
        listed.client.info_calls == ["list"]
        and "**Installed models** (`ollama list`)" in list_final
        and "MODEL-A" in list_final
        and listed.order[-3:]
        == [
            ("update", "asst-1", True, list_final),
            ("busy", False),
            ("status", "alpha"),
        ],
    )

    psed = _CliHarness()
    run_with_worker(lambda: psed._run_ollama_info("ps"))
    ps_final = update_texts(psed, done=True)[-1]
    results.check(
        "info ps posts structured text through the same completion order",
        psed.client.info_calls == ["ps"]
        and "**Loaded models** (`ollama ps`)" in ps_final
        and "RUNNING-A" in ps_final
        and psed.order[-3:]
        == [
            ("update", "asst-1", True, ps_final),
            ("busy", False),
            ("status", "alpha"),
        ],
    )

    for label, error in (
        ("OllamaError", OllamaError("tags down")),
        ("generic exception", RuntimeError("ps boom")),
    ):
        failed_info = _CliHarness()
        failed_info.client.info_error = error
        run_with_worker(lambda owner=failed_info: owner._run_ollama_info("list"))
        info_final = update_texts(failed_info, done=True)[-1]
        results.check(
            f"info {label} finalizes failure text, clears busy, then restores status",
            f"**`ollama list` failed:** {error}" == info_final
            and failed_info._composer_cmd_busy() is False
            and failed_info.order[-3:]
            == [
                ("update", "asst-1", True, info_final),
                ("busy", False),
                ("status", "alpha"),
            ],
        )

    send_busy = _CliHarness()
    send_busy.input = _CliInput("ollama list")
    send_busy._ollama_cli_busy = True
    called: list[str] = []
    send_busy.try_command = (  # type: ignore[method-assign]
        lambda text: called.append(text) or True
    )
    send_busy._send()
    send_names = set(StreamingEngineController.send.__code__.co_names)
    results.check(
        "_send uses is_busy() and returns before command dispatch",
        called == []
        and send_busy.input.get_buffer().text == "ollama list"
        and send_busy._messages == []
        and "_is_cli_busy" in send_names
        and "_try_command" in send_names
        and "_ollama_cli_busy" not in send_names
        and "_try_composer_command" not in send_names,
    )

    send_cmd = _CliHarness()
    send_cmd.input = _CliInput("ollama list")
    dispatched: list[str] = []
    send_cmd.try_command = (  # type: ignore[method-assign]
        lambda text: dispatched.append(text) or True
    )
    send_cmd._send()
    results.check(
        "_send dispatches via try_command and clears the buffer",
        dispatched == ["ollama list"]
        and send_cmd.input.get_buffer().text == ""
        and send_cmd._messages == [],
    )

    send_plain = _CliHarness()
    send_plain.input = _CliInput("hello")
    send_plain._model = ""
    plain_dispatched: list[str] = []
    send_plain.try_command = (  # type: ignore[method-assign]
        lambda text: plain_dispatched.append(text) or False
    )
    send_plain._send()
    results.check(
        "_send asks try_command before chat when the CLI is idle",
        plain_dispatched == ["hello"]
        and send_plain.input.get_buffer().text == "hello",
    )

    results.check(
        "composer CLI owner exposes rebindable message-ID provider",
        "rebind_next_msg_id" in ComposerCliController.__dict__,
    )


def characterize_conversation_lifecycle(results: Results) -> None:
    """Lock Phase-22 conversation-lifecycle moves not covered elsewhere."""
    print("\n[0j] Conversation-lifecycle characterization", flush=True)

    class Msg:
        def __init__(self, mid: str, role: str, content: str) -> None:
            self.id = mid
            self.role = role
            self.content = content

    class Conv:
        def __init__(
            self, cid: str, *, model: str | None = "alpha", title: str = ""
        ) -> None:
            self.id = cid
            self.model = model
            self.title = title

    class LifecycleStore:
        def __init__(self) -> None:
            self.trace: list[object] = []
            self.conversations: dict[str, Conv] = {
                "active": Conv("active", title="Active"),
                "other": Conv("other", title="Other chat"),
                "next": Conv("next", title="Next"),
            }
            self.messages: dict[str, list[Msg]] = {
                "active": [Msg("u1", "user", "hello")],
                "other": [Msg("u2", "user", "there")],
                "next": [],
            }
            self.empty_ids: set[str] = {"next"}
            self.fail_set_active = False
            self.fail_delete = False
            self.fail_clear = False
            self.fail_create = False
            self.fail_ensure = False
            self.fail_append = False
            self.fail_list = False
            self.fail_restore = False
            self.created: list[str] = []
            self.appended: list[tuple] = []
            self.deleted: list[str] = []
            self.pruned_keep: list[str | None] = []
            self.active_id = "active"
            self.ensure_calls = 0

        def clear_messages(self, conversation_id: str) -> None:
            self.trace.append(("clear_messages", conversation_id))
            if self.fail_clear:
                raise RuntimeError("clear failed")
            self.messages[conversation_id] = []
            self.empty_ids.add(conversation_id)

        def create_conversation(self, *, model=None) -> Conv:
            self.trace.append(("create", model))
            if self.fail_create:
                raise RuntimeError("create failed")
            cid = f"new-{len(self.created) + 1}"
            self.created.append(cid)
            conv = Conv(cid, model=model)
            self.conversations[cid] = conv
            self.messages[cid] = []
            self.empty_ids.add(cid)
            self.active_id = cid
            return conv

        def prune_empty_conversations(self, *, keep_id) -> int:
            self.trace.append(("prune", keep_id))
            self.pruned_keep.append(keep_id)
            return 0

        def is_empty(self, conversation_id: str) -> bool:
            self.trace.append(("is_empty", conversation_id))
            return conversation_id in self.empty_ids

        def delete_conversation(self, conversation_id: str) -> None:
            self.trace.append(("delete", conversation_id))
            if self.fail_delete:
                raise RuntimeError("delete failed")
            self.deleted.append(conversation_id)
            self.conversations.pop(conversation_id, None)
            self.messages.pop(conversation_id, None)
            self.empty_ids.discard(conversation_id)
            if self.active_id == conversation_id:
                self.active_id = "next" if "next" in self.conversations else None

        def get_conversation(self, conversation_id: str):
            self.trace.append(("get", conversation_id))
            return self.conversations.get(conversation_id)

        def set_active(self, conversation_id: str) -> None:
            self.trace.append(("set_active", conversation_id))
            if self.fail_set_active:
                raise RuntimeError("set_active failed")
            self.active_id = conversation_id

        def list_messages(self, conversation_id: str):
            self.trace.append(("list_messages", conversation_id))
            if self.fail_list:
                raise RuntimeError("list failed")
            return list(self.messages.get(conversation_id, []))

        def get_active_conversation(self):
            self.trace.append("get_active")
            if self.fail_restore:
                raise RuntimeError("restore failed")
            if self.active_id is None:
                return None
            return self.conversations.get(self.active_id)

        def ensure_active(self, *, model=None) -> Conv:
            self.ensure_calls += 1
            self.trace.append(("ensure_active", model))
            if self.fail_ensure:
                raise RuntimeError("ensure failed")
            if self.active_id and self.active_id in self.conversations:
                return self.conversations[self.active_id]
            return self.create_conversation(model=model)

        def append_message(
            self, conversation_id: str, *, role, content, message_id=None
        ):
            self.trace.append(
                ("append", conversation_id, role, content, message_id)
            )
            if self.fail_append:
                raise RuntimeError("append failed")
            self.appended.append((conversation_id, role, content, message_id))
            mid = message_id or f"auto-{len(self.appended)}"
            self.messages.setdefault(conversation_id, []).append(
                Msg(mid, role, content)
            )
            self.empty_ids.discard(conversation_id)

    class LifecycleOwner:
        """Deterministic ConversationLifecycleController for Phase-21/22 tests."""

        def __init__(self) -> None:
            self.trace: list[object] = []
            self._streaming = False
            self._loading_model = False
            self._load_failed = False
            self._model = "alpha"
            self._store = LifecycleStore()
            self.input = _HealthWidget()
            self.idle_callbacks: list[object] = []
            self.switched: list[str] = []
            self.new_chat_calls = 0
            self.deleted_via_confirm: list[str] = []
            self.greetings = 0
            self.titles_refreshed = 0
            self.history_marked = 0
            self.history_rebuilt = 0
            self.statuses: list[str] = []
            self.stream_invalidated = 0
            self.stop_requested = 0
            self.hints = 0
            self.applied: list[list] = []
            self.rendered_empty = 0
            self.model_selects: list[tuple] = []
            self._conversation = ConversationLifecycleController(
                store=self._store,
                transient_parent=self,
                get_current_model=lambda: self._model,
                is_loading_model=lambda: self._loading_model,
                is_load_failed=lambda: self._load_failed,
                is_streaming=lambda: self._streaming,
                reset_greetings=lambda: self.trace.append("reset_greetings"),
                clear_native_rows=lambda: self.trace.append("clear_rows"),
                render_empty_transcript=self._render_empty_transcript,
                apply_restored_transcript=self._apply_restored_transcript,
                mark_history_dirty=self._mark_history_dirty,
                rebuild_history_list=self._rebuild_history_list,
                refresh_chat_title=self._refresh_chat_title,
                set_status=self._set_status,
                show_ephemeral_greeting=self._show_ephemeral_greeting,
                sync_composer_hint=self._sync_composer_hint,
                select_model_name=self._select_model_name,
                save_last_model=lambda _model: None,
                is_ephemeral_greeting=window_module._is_ephemeral_greeting,
                request_stop=self._request_stop,
                invalidate_active_stream=self._invalidate_active_stream,
                grab_input_focus=lambda: None,
            )
            self._conversation.conversation_id = "active"
            self._conversation.messages = [
                {"id": "u1", "role": "user", "content": "hello"}
            ]
            self._conversation.history_restored = True
            self._conversation.msg_counter = 0

        @property
        def _conversation_id(self):
            return self._conversation.conversation_id

        @_conversation_id.setter
        def _conversation_id(self, value) -> None:
            self._conversation.conversation_id = value

        @property
        def _messages(self):
            return self._conversation.messages

        @_messages.setter
        def _messages(self, value) -> None:
            self._conversation.messages = value

        @property
        def _history_restored(self):
            return self._conversation.history_restored

        @_history_restored.setter
        def _history_restored(self, value) -> None:
            self._conversation.history_restored = value

        @property
        def _msg_counter(self):
            return self._conversation.msg_counter

        @_msg_counter.setter
        def _msg_counter(self, value) -> None:
            self._conversation.msg_counter = value

        def clear_chat(self) -> None:
            self._conversation.clear_chat()

        def new_chat(self) -> None:
            self._conversation.new_chat()

        def switch_conversation(self, conversation_id: str) -> None:
            self._conversation.switch_conversation(conversation_id)

        def delete_conversation(self, conversation_id: str) -> None:
            self._conversation.delete_conversation(conversation_id)

        def _confirm_delete_conversation(self, conversation_id: str) -> None:
            self._conversation.confirm_delete_conversation(conversation_id)

        def _ensure_conversation(self) -> str:
            return self._conversation.ensure_conversation()

        def _persist_message(
            self, role: str, content: str, message_id: str | None = None
        ) -> None:
            self._conversation.persist_message(role, content, message_id)

        def _next_msg_id(self, prefix: str) -> str:
            return self._conversation.next_msg_id(prefix)

        def _restore_history(self) -> None:
            self._conversation.restore_history()

        def _conversation_display_title(self, conversation_id: str) -> str:
            return self._conversation.conversation_display_title(conversation_id)

        def _request_stop(self) -> None:
            self.stop_requested += 1

        def _invalidate_active_stream(self) -> None:
            self.stream_invalidated += 1

        def _mark_history_dirty(self) -> None:
            self.history_marked += 1
            self.trace.append("mark_dirty")

        def _rebuild_history_list(self) -> bool:
            self.history_rebuilt += 1
            self.trace.append("rebuild")
            return False

        def _render_empty_transcript(self) -> None:
            self.rendered_empty += 1
            self.trace.append("render_empty")

        def _set_status(self, text: str) -> None:
            self.statuses.append(text)

        def _show_ephemeral_greeting(self) -> None:
            self.greetings += 1
            self.trace.append("greeting")

        def _refresh_chat_title(self) -> bool:
            self.titles_refreshed += 1
            self.trace.append("refresh_title")
            return False

        def _sync_composer_hint(self) -> None:
            self.hints += 1

        def _apply_restored_transcript(self, messages: list) -> None:
            self.applied.append(list(messages))
            self.trace.append(("apply", len(messages)))

        def _select_model_name(self, name: str, *, warm: bool = False, greet: bool = False) -> None:
            self.model_selects.append((name, warm, greet))

    # --- new_chat: already-empty avoids a new DB row ---
    empty_new = LifecycleOwner()
    empty_new._messages = []
    empty_new._store.empty_ids.add("active")
    empty_new._history_restored = True
    before_created = list(empty_new._store.created)
    empty_new.new_chat()
    results.check(
        "already-empty new_chat focuses without creating another conversation row",
        empty_new._store.created == before_created
        and empty_new._conversation_id == "active"
        and empty_new._history_restored is True
        and empty_new.greetings == 1
        and "create" not in [t[0] for t in empty_new._store.trace if isinstance(t, tuple)],
    )

    # --- new_chat: nonempty path prunes, creates, clears restored flag ---
    nonempty_new = LifecycleOwner()
    nonempty_new.new_chat()
    results.check(
        "nonempty new_chat prunes empties, creates a row, and clears history_restored",
        nonempty_new._store.pruned_keep == [None]
        and nonempty_new._store.created == ["new-1"]
        and nonempty_new._conversation_id == "new-1"
        and nonempty_new._messages == []
        and nonempty_new._history_restored is False
        and "reset_greetings" in nonempty_new.trace
        and nonempty_new.history_marked >= 1
        and nonempty_new.history_rebuilt >= 1,
    )

    # --- clear_chat persistence ---
    cleared = LifecycleOwner()
    cleared.clear_chat()
    results.check(
        "clear_chat wipes in-memory and store messages for the active conversation",
        cleared._messages == []
        and ("clear_messages", "active") in cleared._store.trace
        and cleared.history_marked >= 1
        and cleared.rendered_empty >= 1
        and "reset_greetings" in cleared.trace,
    )
    clear_create = LifecycleOwner()
    clear_create._conversation_id = None
    clear_create.clear_chat()
    results.check(
        "clear_chat without an active id creates a conversation row",
        clear_create._conversation_id == "new-1"
        and ("create", "alpha") in clear_create._store.trace,
    )
    clear_fail = LifecycleOwner()
    clear_fail._store.fail_clear = True
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        clear_fail.clear_chat()
    results.check(
        "clear_chat logs store failure and still rebuilds the empty UI",
        "clear_chat persist: clear failed" in stdout.getvalue()
        and clear_fail._messages == []
        and clear_fail.rendered_empty >= 1,
    )

    # --- switch pruning + set_active failure continues ---
    switch_prune = LifecycleOwner()
    switch_prune._messages = []
    switch_prune._store.empty_ids.add("active")
    switch_prune.switch_conversation("other")
    results.check(
        "switch_conversation deletes the previous empty draft before loading the target",
        ("is_empty", "active") in switch_prune._store.trace
        and ("delete", "active") in switch_prune._store.trace
        and switch_prune._conversation_id == "other"
        and switch_prune._messages[0]["content"] == "there"
        and switch_prune._history_restored is True
        and switch_prune.applied
        and len(switch_prune.applied[-1]) == 1,
    )

    switch_fail = LifecycleOwner()
    switch_fail._store.fail_set_active = True
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        switch_fail.switch_conversation("other")
    results.check(
        "switch_conversation continues past set_active failure and still loads messages",
        "set_active: set_active failed" in stdout.getvalue()
        and switch_fail._conversation_id == "other"
        and switch_fail._messages[0]["id"] == "u2"
        and switch_fail._history_restored is True,
    )

    switch_empty = LifecycleOwner()
    switch_empty._store.messages["other"] = []
    switch_empty._store.empty_ids.add("other")
    switch_empty.switch_conversation("other")
    results.check(
        "switch_conversation onto an empty chat writes history_restored False and greets",
        switch_empty._messages == []
        and switch_empty._history_restored is False
        and switch_empty.rendered_empty >= 1
        and switch_empty.greetings >= 1,
    )

    # --- delete active vs inactive; store failure aborts ---
    delete_inactive = LifecycleOwner()
    delete_inactive.delete_conversation("other")
    results.check(
        "delete_conversation on an inactive chat removes it and rebuilds history only",
        delete_inactive._store.deleted == ["other"]
        and delete_inactive._conversation_id == "active"
        and delete_inactive.history_rebuilt >= 1
        and delete_inactive.switched == []
        and delete_inactive.new_chat_calls == 0,
    )

    delete_active = LifecycleOwner()
    delete_active._store.active_id = "next"
    real_switch = delete_active._conversation.switch_conversation
    delete_active._conversation.switch_conversation = (  # type: ignore[method-assign]
        lambda cid: delete_active.switched.append(cid)
    )
    delete_active.delete_conversation("active")
    results.check(
        "delete_conversation on the active chat switches to the next remaining conversation",
        delete_active._store.deleted == ["active"]
        and delete_active.switched == ["next"]
        and delete_active._conversation_id is None,
    )
    delete_active._conversation.switch_conversation = real_switch  # type: ignore[method-assign]

    delete_last = LifecycleOwner()
    delete_last._store.conversations = {"active": Conv("active")}
    delete_last._store.messages = {"active": [Msg("u1", "user", "x")]}
    delete_last._store.active_id = None
    real_new = delete_last._conversation.new_chat
    delete_last._conversation.new_chat = (  # type: ignore[method-assign]
        lambda: setattr(delete_last, "new_chat_calls", delete_last.new_chat_calls + 1)
    )
    delete_last.delete_conversation("active")
    results.check(
        "delete_conversation with no remaining chats falls back to new_chat",
        delete_last.new_chat_calls == 1,
    )
    delete_last._conversation.new_chat = real_new  # type: ignore[method-assign]

    delete_fail = LifecycleOwner()
    delete_fail._store.fail_delete = True
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        delete_fail.delete_conversation("other")
    results.check(
        "delete_conversation aborts immediately on store failure without UI follow-up",
        "delete_conversation: delete failed" in stdout.getvalue()
        and delete_fail.history_marked == 0
        and delete_fail.history_rebuilt == 0
        and delete_fail.switched == []
        and delete_fail.new_chat_calls == 0
        and "other" in delete_fail._store.conversations,
    )

    # --- confirm dialog ---
    class FakeDeleteDialog:
        instances: list["FakeDeleteDialog"] = []

        def __init__(self, *, transient_for, heading: str, body: str) -> None:
            self.transient_for = transient_for
            self.heading = heading
            self.body = body
            self.responses: list[tuple[str, str]] = []
            self.appearance: list[tuple] = []
            self.default = None
            self.close = None
            self.handler = None
            self.presented = False
            self.__class__.instances.append(self)

        def add_response(self, response_id: str, label: str) -> None:
            self.responses.append((response_id, label))

        def set_response_appearance(self, response_id: str, appearance) -> None:
            self.appearance.append((response_id, appearance))

        def set_default_response(self, response_id: str) -> None:
            self.default = response_id

        def set_close_response(self, response_id: str) -> None:
            self.close = response_id

        def connect(self, signal: str, handler) -> None:
            if signal == "response":
                self.handler = handler

        def present(self) -> None:
            self.presented = True

    confirm = LifecycleOwner()
    FakeDeleteDialog.instances.clear()
    deleted: list[str] = []
    confirm._conversation.delete_conversation = (  # type: ignore[method-assign]
        lambda cid: deleted.append(cid)
    )
    with patch.object(
        conversation_lifecycle_module.Adw, "MessageDialog", FakeDeleteDialog
    ):
        confirm._confirm_delete_conversation("other")
        dialog = FakeDeleteDialog.instances[-1]
        dialog.handler(dialog, "cancel")
        cancel_deleted = list(deleted)
        dialog.handler(dialog, "delete")
    results.check(
        "_confirm_delete_conversation presents a destructive dialog and deletes only on confirm",
        dialog.presented is True
        and dialog.heading == "Delete chat?"
        and "Other chat" in dialog.body
        and dialog.responses == [("cancel", "Cancel"), ("delete", "Delete")]
        and dialog.default == "cancel"
        and dialog.close == "cancel"
        and dialog.appearance
        and dialog.appearance[0][0] == "delete"
        and cancel_deleted == []
        and deleted == ["other"],
    )

    # --- ensure / persist / next_msg_id ---
    ensure_reuse = LifecycleOwner()
    reused = ensure_reuse._ensure_conversation()
    results.check(
        "_ensure_conversation reuses an existing id without touching the store",
        reused == "active"
        and ensure_reuse._store.ensure_calls == 0
        and ensure_reuse._conversation_id == "active",
    )
    ensure_create = LifecycleOwner()
    ensure_create._conversation_id = None
    ensure_create._store.active_id = None
    created_id = ensure_create._ensure_conversation()
    results.check(
        "_ensure_conversation calls ensure_active and records the resulting id",
        ensure_create._store.ensure_calls == 1
        and created_id == ensure_create._conversation_id
        and ("ensure_active", "alpha") in ensure_create._store.trace,
    )

    persist_user = LifecycleOwner()
    idles: list[object] = []
    with patch.object(
        conversation_lifecycle_module.GLib,
        "idle_add",
        side_effect=lambda cb, *args: idles.append(cb) or 1,
    ):
        persist_user._persist_message("user", "hi", message_id="user-fixed")
    results.check(
        "_persist_message forwards ids, ensures first, and dirties/titles only for user role",
        persist_user._store.appended
        == [("active", "user", "hi", "user-fixed")]
        and persist_user.history_marked == 1
        and idles == [persist_user._refresh_chat_title],
    )
    persist_asst = LifecycleOwner()
    idles.clear()
    with patch.object(
        conversation_lifecycle_module.GLib,
        "idle_add",
        side_effect=lambda cb, *args: idles.append(cb) or 1,
    ):
        persist_asst._persist_message("assistant", "yo", message_id="asst-fixed")
    results.check(
        "_persist_message does not dirty history or schedule title refresh for assistant role",
        persist_asst._store.appended
        == [("active", "assistant", "yo", "asst-fixed")]
        and persist_asst.history_marked == 0
        and idles == [],
    )
    persist_fail = LifecycleOwner()
    persist_fail._store.fail_append = True
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        persist_fail._persist_message("user", "nope", message_id="u-fail")
    results.check(
        "_persist_message logs ensure/append failure and continues without raising",
        "persist message failed: append failed" in stdout.getvalue()
        and persist_fail.history_marked == 0,
    )

    ids = LifecycleOwner()
    first = ids._next_msg_id("user")
    second = ids._next_msg_id("asst")
    third = ids._next_msg_id("user")
    import re as _re

    results.check(
        "_next_msg_id advances the counter and uses prefix-counter-sixhex format",
        ids._msg_counter == 3
        and first.startswith("user-1-")
        and second.startswith("asst-2-")
        and third.startswith("user-3-")
        and all(
            _re.fullmatch(r"(user|asst)-\d+-[0-9a-f]{6}", value)
            for value in (first, second, third)
        )
        and len({first, second, third}) == 3,
    )

    # --- history_restored on restore paths ---
    restore_ok = LifecycleOwner()
    restore_ok._history_restored = False
    restore_ok._messages = []
    restore_ok._restore_history()
    results.check(
        "_restore_history writes history_restored True when real messages load",
        restore_ok._history_restored is True
        and len(restore_ok._messages) == 1
        and restore_ok.applied,
    )
    restore_empty = LifecycleOwner()
    restore_empty._store.messages["active"] = []
    restore_empty._store.empty_ids.add("active")
    restore_empty._history_restored = True
    restore_empty._restore_history()
    results.check(
        "_restore_history writes history_restored False for an empty active chat",
        restore_empty._history_restored is False
        and restore_empty._messages == [],
    )
    restore_fail = LifecycleOwner()
    restore_fail._store.fail_restore = True
    restore_fail._history_restored = True
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        restore_fail._restore_history()
    results.check(
        "_restore_history writes history_restored False on restore failure",
        "restore history failed: restore failed" in stdout.getvalue()
        and restore_fail._history_restored is False,
    )

    loading_guard = LifecycleOwner()
    loading_guard._loading_model = True
    before = loading_guard._conversation_id
    loading_guard.new_chat()
    loading_guard.switch_conversation("other")
    results.check(
        "new_chat and switch_conversation are strict no-ops while a model is loading",
        loading_guard._conversation_id == before
        and loading_guard._store.created == []
        and loading_guard._messages[0]["id"] == "u1",
    )
    results.check(
        "conversation lifecycle controller owns projection state and ID allocation",
        isinstance(loading_guard._conversation, ConversationLifecycleController)
        and "messages_empty" in ConversationLifecycleController.__dict__
        and "next_msg_id" in ConversationLifecycleController.__dict__
        and "replace_messages" in ConversationLifecycleController.__dict__
        and "truncate_from" in ConversationLifecycleController.__dict__
        and "clear_chat" in ChatSidebar.clear_chat.__code__.co_names
        and "switch_conversation" in ChatSidebar.switch_conversation.__code__.co_names
        and "persist_message" in ChatSidebar._persist_message.__code__.co_names
        and not hasattr(ChatSidebar, "_mark_history_dirty")
        and not hasattr(ChatSidebar, "_rebuild_history_list"),
    )


def characterize_message_actions(
    results: Results,
    app: Adw.Application,
) -> None:
    """Lock Phase-23/24 group-L helpers, guards, routing, and commits."""
    print("\n[0k] Message-action characterization", flush=True)

    class ActionStore:
        def __init__(self) -> None:
            self.deleted: list[tuple[str, str | None]] = []
            self.updated: list[tuple[str, str]] = []
            self.appended: list[tuple] = []
            self.fail_delete = False
            self.fail_update = False

        def delete_message(self, message_id: str, *, conversation_id=None) -> None:
            if self.fail_delete:
                raise RuntimeError("delete failed")
            self.deleted.append((message_id, conversation_id))

        def update_message(self, message_id: str, content: str) -> None:
            if self.fail_update:
                raise RuntimeError("update failed")
            self.updated.append((message_id, content))

        def append_message(
            self, conversation_id: str, *, role, content, message_id=None
        ):
            self.appended.append((conversation_id, role, content, message_id))

    class FakeTranscript:
        def __init__(self, *, webkit: bool) -> None:
            self.mode = "webkit" if webkit else "native"
            self.posts: list[dict] = []
            self.resets = 0

        @property
        def is_webkit(self) -> bool:
            return self.mode == "webkit"

        def post(self, event: dict) -> None:
            self.posts.append(dict(event))

        def reset_empty(self) -> None:
            self.resets += 1

    class ActionOwner:
        """Deterministic MessageActionController harness for Phase-23/24 tests."""

        def __init__(self, *, webkit: bool = True) -> None:
            self._streaming = False
            self._loading_model = False
            self._model = "action-model"
            self._store = ActionStore()
            self._transcript = FakeTranscript(webkit=webkit)
            self.stream_starts: list[dict] = []
            self.native_removals: list[str] = []
            self.appends: list[tuple] = []
            self._conversation = ConversationLifecycleController(
                store=self._store,  # type: ignore[arg-type]
                transient_parent=SimpleNamespace(),
                get_current_model=lambda: self._model,
                is_loading_model=lambda: self._loading_model,
                is_load_failed=lambda: False,
                is_streaming=lambda: self._streaming,
                reset_greetings=lambda: None,
                clear_native_rows=lambda: None,
                render_empty_transcript=lambda: None,
                apply_restored_transcript=lambda _messages: None,
                mark_history_dirty=lambda: None,
                rebuild_history_list=lambda: False,
                refresh_chat_title=lambda: False,
                set_status=lambda _text: None,
                show_ephemeral_greeting=lambda: None,
                sync_composer_hint=lambda: None,
                select_model_name=lambda *_a, **_k: None,
                save_last_model=lambda _model: None,
                is_ephemeral_greeting=lambda _role, _content: False,
                request_stop=lambda: None,
                invalidate_active_stream=lambda: None,
                grab_input_focus=lambda: None,
            )
            self._conversation.conversation_id = "conv-action"
            self._conversation.messages = [
                {"id": "u1", "role": "user", "content": "hello"},
                {"id": "a1", "role": "assistant", "content": "world"},
            ]
            self._message_actions = MessageActionController(
                get_store=lambda: self._store,  # type: ignore[arg-type]
                conversation=self._conversation,
                is_streaming=lambda: self._streaming,
                is_loading_model=lambda: self._loading_model,
                get_current_model=lambda: self._model,
                is_webkit=lambda: self._transcript.is_webkit,
                post_transcript=self._transcript.post,
                reset_empty_transcript=self._transcript.reset_empty,
                remove_native_message=lambda mid: self.native_removals.append(mid),
                append_native_message=self._append_message,
                start_assistant_stream=self._start_assistant_stream,
            )

        @property
        def _messages(self):
            return self._conversation.messages

        @_messages.setter
        def _messages(self, value) -> None:
            self._conversation.messages = value

        @property
        def _conversation_id(self):
            return self._conversation.conversation_id

        def _start_assistant_stream(self, **kwargs) -> None:
            self.stream_starts.append(dict(kwargs))

        def _append_message(self, role, content, *, message_id=None, **kwargs):
            self.appends.append((role, content, message_id, dict(kwargs)))

        def _find_message_index(self, message_id: str) -> int:
            return self._message_actions.find_message_index(message_id)

        def _api_messages(self, messages=None):
            return self._message_actions.api_messages(messages)

        def _clipboard_set(self, text: str) -> None:
            self._message_actions.clipboard_set(text)

        def _delete_message(self, message_id: str) -> None:
            self._message_actions.delete_message(message_id)

        def _drop_messages_from(self, idx: int, *, keep_ui_id: str | None = None) -> None:
            self._message_actions.drop_messages_from(idx, keep_ui_id=keep_ui_id)

        def _regenerate_message(self, message_id: str) -> None:
            self._message_actions.regenerate_message(message_id)

        def _edit_resend_message(self, message_id: str, text: str) -> None:
            self._message_actions.edit_resend_message(message_id, text)

        def _continue_message(self, message_id: str) -> None:
            self._message_actions.continue_message(message_id)

        def _on_web_intent(self, payload: dict) -> bool:
            return self._message_actions.handle_intent(payload)

        def seed(
            self,
            messages: list[dict],
            *,
            streaming: bool = False,
            loading: bool = False,
            model: str | None = "action-model",
        ) -> None:
            self._messages = [dict(m) for m in messages]
            self._streaming = streaming
            self._loading_model = loading
            self._model = model
            self._store = ActionStore()
            self._transcript.posts.clear()
            self._transcript.resets = 0
            self.stream_starts.clear()
            self.native_removals.clear()
            self.appends.clear()

    owner = ActionOwner(webkit=True)

    # --- helpers: find / api / clipboard ---
    results.check(
        "_find_message_index returns the matching index or -1 for missing IDs",
        owner._find_message_index("a1") == 1
        and owner._find_message_index("missing") == -1
        and owner._find_message_index("") == -1,
    )
    results.check(
        "_api_messages filters to user/assistant roles with non-None content",
        owner._api_messages(
            [
                {"id": "u", "role": "user", "content": "q"},
                {"id": "s", "role": "system", "content": "sys"},
                {"id": "a", "role": "assistant", "content": "a"},
                {"id": "n", "role": "assistant", "content": None},
                {"id": "t", "role": "tool", "content": "tool"},
            ]
        )
        == [
            {"role": "user", "content": "q"},
            {"role": "assistant", "content": "a"},
        ]
        and owner._api_messages()
        == [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "world"},
        ],
    )

    clipboard_sets: list[str] = []

    class FakeClipboard:
        def set(self, text: str) -> None:
            clipboard_sets.append(text)

    class FakeDisplay:
        def get_clipboard(self):
            return FakeClipboard()

    with patch.object(
        message_actions_module.Gdk.Display, "get_default", return_value=None
    ):
        owner._clipboard_set("ignored")
    with patch.object(
        message_actions_module.Gdk.Display, "get_default", return_value=FakeDisplay()
    ):
        owner._clipboard_set("copied")
        owner._clipboard_set(None)  # type: ignore[arg-type]
    results.check(
        "_clipboard_set is a no-op without a display or with None text",
        clipboard_sets == ["copied"],
    )

    # --- delete / drop ---
    owner.seed(
        [
            {"id": "u1", "role": "user", "content": "hello"},
            {"id": "a1", "role": "assistant", "content": "world"},
            {"id": "u2", "role": "user", "content": "again"},
        ]
    )
    owner._delete_message("")
    owner._delete_message("missing")
    results.check(
        "_delete_message ignores empty and unknown IDs",
        owner._messages[0]["id"] == "u1"
        and owner._store.deleted == []
        and owner._transcript.posts == [],
    )

    busy = ActionOwner(webkit=True)
    busy.seed(busy._messages, streaming=True)
    busy._delete_message("u1")
    busy.seed(
        [
            {"id": "u1", "role": "user", "content": "hello"},
            {"id": "a1", "role": "assistant", "content": "world"},
        ],
        loading=True,
    )
    busy._delete_message("u1")
    results.check(
        "_delete_message is a no-op while streaming or loading a model",
        busy._messages[0]["id"] == "u1" and busy._store.deleted == [],
    )

    owner.seed(
        [
            {"id": "u1", "role": "user", "content": "hello"},
            {"id": "a1", "role": "assistant", "content": "world"},
        ]
    )
    owner._store.fail_delete = True
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        owner._delete_message("u1")
    results.check(
        "_delete_message continues UI cleanup when store delete fails",
        "delete persist: delete failed" in stdout.getvalue()
        and owner._messages == []
        and owner._transcript.posts
        == [
            {"type": "message_removed", "id": "u1"},
            {"type": "message_removed", "id": "a1"},
        ]
        and owner._transcript.resets == 1,
    )

    native_del = ActionOwner(webkit=False)
    native_del.seed(
        [
            {"id": "u1", "role": "user", "content": "hello"},
            {"id": "", "role": "assistant", "content": "no-id"},
            {"id": "a1", "role": "assistant", "content": "world"},
        ]
    )
    native_del._delete_message("u1")
    results.check(
        "native _delete_message skips blank IDs and removes remaining rows",
        native_del._messages == []
        and native_del._store.deleted
        == [("u1", "conv-action"), ("a1", "conv-action")]
        and native_del.native_removals == ["u1", "a1"]
        and native_del._transcript.resets == 1,
    )

    owner.seed(
        [
            {"id": "u1", "role": "user", "content": "keep"},
            {"id": "a1", "role": "assistant", "content": "drop"},
            {"id": "a2", "role": "assistant", "content": "also"},
        ]
    )
    owner._drop_messages_from(-1)
    owner._drop_messages_from(99)
    results.check(
        "_drop_messages_from ignores out-of-range indexes",
        len(owner._messages) == 3 and owner._store.deleted == [],
    )
    owner._drop_messages_from(1, keep_ui_id="a1")
    results.check(
        "_drop_messages_from keeps keep_ui_id in WebKit while deleting store rows",
        owner._messages == [{"id": "u1", "role": "user", "content": "keep"}]
        and owner._store.deleted
        == [("a1", "conv-action"), ("a2", "conv-action")]
        and owner._transcript.posts
        == [{"type": "message_removed", "id": "a2"}],
    )

    drop_fail = ActionOwner(webkit=False)
    drop_fail.seed(
        [
            {"id": "u1", "role": "user", "content": "keep"},
            {"id": "a1", "role": "assistant", "content": "drop"},
        ]
    )
    drop_fail._store.fail_delete = True
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        drop_fail._drop_messages_from(1)
    results.check(
        "_drop_messages_from continues native UI cleanup after persist failure",
        "drop persist: delete failed" in stdout.getvalue()
        and drop_fail._messages
        == [{"id": "u1", "role": "user", "content": "keep"}]
        and drop_fail.native_removals == ["a1"],
    )

    # --- regenerate ---
    regen = ActionOwner(webkit=True)
    regen.seed(regen._messages, streaming=True)
    regen._regenerate_message("a1")
    regen.seed(regen._messages, loading=True)
    regen._regenerate_message("a1")
    regen.seed(regen._messages, model=None)
    regen._regenerate_message("a1")
    regen.seed(regen._messages)
    regen._regenerate_message("")
    regen._regenerate_message("missing")
    results.check(
        "_regenerate_message guards empty/missing IDs, busy flags, and missing model",
        regen.stream_starts == [] and regen._messages[0]["id"] == "u1",
    )

    regen.seed(
        [
            {"id": "u1", "role": "user", "content": "hello"},
            {"id": "a1", "role": "assistant", "content": "world"},
            {"id": "u2", "role": "user", "content": "again"},
        ]
    )
    regen._regenerate_message("u1")
    results.check(
        "user-role regenerate drops later turns and starts a new assistant stream",
        [m["id"] for m in regen._messages] == ["u1"]
        and regen._store.deleted
        == [("a1", "conv-action"), ("u2", "conv-action")]
        and regen.stream_starts
        == [
            {
                "mode": "new",
                "api_messages": [{"role": "user", "content": "hello"}],
            }
        ],
    )

    regen.seed(
        [
            {"id": "u1", "role": "user", "content": "hello"},
            {"id": "sys", "role": "system", "content": "nope"},
        ]
    )
    regen._regenerate_message("sys")
    results.check(
        "_regenerate_message ignores unsupported roles",
        regen.stream_starts == [] and len(regen._messages) == 2,
    )

    regen.seed(
        [
            {"id": "u1", "role": "user", "content": "hello"},
            {"id": "a1", "role": "assistant", "content": "old"},
            {"id": "u2", "role": "user", "content": "later"},
        ]
    )
    regen._store.fail_delete = True
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        regen._regenerate_message("a1")
    results.check(
        "assistant regenerate deletes the row/tail, posts removals, and starts replace",
        "regen tail delete: delete failed" in stdout.getvalue()
        and "regen delete: delete failed" in stdout.getvalue()
        and regen._messages == [{"id": "u1", "role": "user", "content": "hello"}]
        and regen._transcript.posts
        == [{"type": "message_removed", "id": "u2"}]
        and regen.stream_starts
        == [
            {
                "mode": "replace",
                "assistant_id": "a1",
                "api_messages": [{"role": "user", "content": "hello"}],
            }
        ],
    )

    native_regen = ActionOwner(webkit=False)
    native_regen.seed(
        [
            {"id": "u1", "role": "user", "content": "hello"},
            {"id": "a1", "role": "assistant", "content": "old"},
            {"id": "a2", "role": "assistant", "content": "tail"},
        ]
    )
    native_regen._regenerate_message("a1")
    results.check(
        "native assistant regenerate removes UI rows for the replaced tail",
        native_regen.native_removals == ["a2"]
        and native_regen._messages
        == [{"id": "u1", "role": "user", "content": "hello"}]
        and native_regen.stream_starts[0]["mode"] == "replace"
        and native_regen.stream_starts[0]["assistant_id"] == "a1",
    )

    # --- edit_resend ---
    edit = ActionOwner(webkit=True)
    edit.seed(edit._messages)
    edit._edit_resend_message("u1", "   ")
    edit._edit_resend_message("", "fresh")
    edit.seed(edit._messages, streaming=True)
    edit._edit_resend_message("u1", "fresh")
    edit.seed(edit._messages, loading=True)
    edit._edit_resend_message("u1", "fresh")
    edit.seed(edit._messages, model=None)
    edit._edit_resend_message("u1", "fresh")
    edit.seed(edit._messages)
    edit._edit_resend_message("missing", "fresh")
    edit._edit_resend_message("a1", "fresh")
    results.check(
        "_edit_resend_message guards blank text, IDs, busy flags, model, and role",
        edit.stream_starts == []
        and edit._messages[0]["content"] == "hello"
        and edit._store.updated == [],
    )

    edit.seed(
        [
            {"id": "u1", "role": "user", "content": "hello"},
            {"id": "a1", "role": "assistant", "content": "world"},
        ]
    )
    edit._store.fail_update = True
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        edit._edit_resend_message("u1", "  revised prompt  ")
    results.check(
        "WebKit edit_resend trims text, survives persist failure, drops tail, and streams",
        "edit_resend persist: update failed" in stdout.getvalue()
        and edit._messages
        == [{"id": "u1", "role": "user", "content": "revised prompt"}]
        and edit._store.deleted == [("a1", "conv-action")]
        and edit._transcript.posts
        == [
            {"type": "message_removed", "id": "a1"},
            {
                "type": "message_added",
                "id": "u1",
                "role": "user",
                "text": "revised prompt",
                "streaming": False,
            },
        ]
        and edit.stream_starts
        == [
            {
                "mode": "new",
                "api_messages": [
                    {"role": "user", "content": "revised prompt"}
                ],
            }
        ],
    )

    native_edit = ActionOwner(webkit=False)
    native_edit.seed(
        [
            {"id": "u1", "role": "user", "content": "hello"},
            {"id": "a1", "role": "assistant", "content": "world"},
        ]
    )
    native_edit._edit_resend_message("u1", "native revise")
    results.check(
        "native edit_resend replaces the user bubble through remove+append",
        native_edit.native_removals == ["a1", "u1"]
        and native_edit.appends
        == [("user", "native revise", "u1", {})]
        and native_edit.stream_starts[0]["mode"] == "new",
    )

    # --- continue ---
    cont = ActionOwner(webkit=True)
    cont.seed(cont._messages, streaming=True)
    cont._continue_message("a1")
    cont.seed(cont._messages, loading=True)
    cont._continue_message("a1")
    cont.seed(cont._messages, model=None)
    cont._continue_message("a1")
    cont.seed(cont._messages)
    cont._continue_message("")
    cont._continue_message("missing")
    cont._continue_message("u1")
    results.check(
        "_continue_message guards empty/missing IDs, busy flags, model, and role",
        cont.stream_starts == [],
    )

    cont.seed(
        [
            {"id": "u1", "role": "user", "content": "hello"},
            {"id": "a1", "role": "assistant", "content": "partial"},
            {"id": "u2", "role": "user", "content": "later"},
        ]
    )
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        cont._continue_message("a1")
    results.check(
        "_continue_message only allows the latest assistant message",
        "continue: only the latest assistant message" in stdout.getvalue()
        and cont.stream_starts == [],
    )

    cont.seed(
        [
            {"id": "u1", "role": "user", "content": "hello"},
            {"id": "a1", "role": "assistant", "content": "partial answer"},
        ]
    )
    cont._continue_message("a1")
    results.check(
        "_continue_message starts a continue stream with seed and synthetic user turn",
        cont.stream_starts
        == [
            {
                "mode": "continue",
                "assistant_id": "a1",
                "seed_text": "partial answer",
                "api_messages": [
                    {"role": "user", "content": "hello"},
                    {"role": "assistant", "content": "partial answer"},
                    {
                        "role": "user",
                        "content": (
                            "Continue your previous response without repeating "
                            "what you already wrote."
                        ),
                    },
                ],
            }
        ],
    )

    # --- _on_web_intent routing ---
    routed: list[tuple] = []
    route = ActionOwner(webkit=True)
    route._message_actions.clipboard_set = lambda text: routed.append(("copy", text))
    route._message_actions.regenerate_message = lambda mid: routed.append(
        ("regen", mid)
    )
    route._message_actions.continue_message = lambda mid: routed.append(
        ("continue", mid)
    )
    route._message_actions.delete_message = lambda mid: routed.append(("delete", mid))
    route._message_actions.edit_resend_message = lambda mid, text: routed.append(
        ("edit_resend", mid, text)
    )
    results.check(
        "_on_web_intent routes copy/regenerate/continue/delete/edit_resend exactly",
        route._on_web_intent({"type": "copy_text", "text": ""}) is False
        and route._on_web_intent({"type": "copy_text", "text": "clip"}) is False
        and route._on_web_intent({"type": "ready"}) is False
        and route._on_web_intent({"type": "regenerate", "id": "a1"}) is False
        and route._on_web_intent({"type": "continue", "id": "a1"}) is False
        and route._on_web_intent({"type": "delete_message", "id": "u1"}) is False
        and route._on_web_intent(
            {"type": "edit_resend", "id": "u1", "text": "x"}
        )
        is False
        and route._on_web_intent({"type": "unknown"}) is False
        and routed
        == [
            ("copy", "clip"),
            ("regen", "a1"),
            ("continue", "a1"),
            ("delete", "u1"),
            ("edit_resend", "u1", "x"),
        ],
    )

    # --- completed regenerate/continue commits on both transcript modes ---
    def prepare_owner(sidebar: ChatSidebar) -> None:
        sidebar._streaming = False
        sidebar._stream_generation = 0
        sidebar._active_stream_cancel = None
        conversation = sidebar._store.create_conversation(model="stream-model")
        sidebar._conversation_id = conversation.id
        sidebar._model_session.set_current_model("stream-model")
        sidebar._apply_health = lambda *_args, **_kwargs: None
        sidebar._streaming_engine._apply_health = sidebar._apply_health

    def drive_from_action(
        sidebar: ChatSidebar,
        *,
        start,
        chunks: list[str],
    ) -> None:
        flushers: list = []
        scripted = _ScriptedChatStream(chunks)
        sidebar.client.chat_stream = scripted  # type: ignore[method-assign]

        def capture_timeout(interval, callback):
            if getattr(callback, "__name__", "") == "flush_stream":
                flushers.append(callback)
            return 1

        with patch.object(
            streaming_engine_module.GLib,
            "timeout_add",
            side_effect=capture_timeout,
        ):
            start()
        assert flushers, "action must schedule flush_stream"
        wait_until(lambda: scripted.finished.is_set(), timeout=5)
        while flushers[0]():
            pass

    for mode_name, env_mode in (("WebKit", "webkit"), ("native", "native")):
        with (
            patch.object(ChatSidebar, "_restore_history", lambda _self: None),
            patch.object(ChatSidebar, "_refresh_models", lambda _self: False),
            patch.dict(os.environ, {"CHICKENBUTT_TRANSCRIPT": env_mode}),
        ):
            live = ChatSidebar(app, client=OllamaClient())
        pump(0.05)
        prepare_owner(live)
        cid = live._conversation_id
        assert cid is not None
        user_live = f"user-live-{env_mode}"
        asst_live = f"asst-live-{env_mode}"
        live._store.append_message(
            cid, role="user", content="hi", message_id=user_live
        )
        live._store.append_message(
            cid, role="assistant", content="old answer", message_id=asst_live
        )
        live._messages = [
            {"id": user_live, "role": "user", "content": "hi"},
            {"id": asst_live, "role": "assistant", "content": "old answer"},
        ]
        drive_from_action(
            live,
            start=lambda mid=asst_live: live._regenerate_message(mid),
            chunks=["brand ", "new"],
        )
        persisted = live._store.list_messages(cid)
        results.check(
            f"{mode_name} regenerate completes replace commit in memory and store",
            live._messages
            == [
                {"id": user_live, "role": "user", "content": "hi"},
                {
                    "id": asst_live,
                    "role": "assistant",
                    "content": "brand new",
                },
            ]
            and [(m.id, m.role, m.content) for m in persisted]
            == [
                (user_live, "user", "hi"),
                (asst_live, "assistant", "brand new"),
            ]
            and not live._streaming,
        )

        prepare_owner(live)
        cid = live._conversation_id
        assert cid is not None
        user_cont = f"user-cont-{env_mode}"
        asst_cont = f"asst-cont-{env_mode}"
        live._store.append_message(
            cid, role="user", content="hi", message_id=user_cont
        )
        live._store.append_message(
            cid,
            role="assistant",
            content="Seed text",
            message_id=asst_cont,
        )
        live._messages = [
            {"id": user_cont, "role": "user", "content": "hi"},
            {"id": asst_cont, "role": "assistant", "content": "Seed text"},
        ]
        drive_from_action(
            live,
            start=lambda mid=asst_cont: live._continue_message(mid),
            chunks=[" more"],
        )
        persisted = live._store.list_messages(cid)
        results.check(
            f"{mode_name} continue completes update commit in memory and store",
            live._messages
            == [
                {"id": user_cont, "role": "user", "content": "hi"},
                {
                    "id": asst_cont,
                    "role": "assistant",
                    "content": "Seed text\n\n more",
                },
            ]
            and [(m.id, m.role, m.content) for m in persisted]
            == [
                (user_cont, "user", "hi"),
                (asst_cont, "assistant", "Seed text\n\n more"),
            ]
            and not live._streaming,
        )
        live.set_visible(False)

    stream_names = set(
        StreamingEngineController.start_assistant_stream.__code__.co_names
    )
    for const in StreamingEngineController.start_assistant_stream.__code__.co_consts:
        if hasattr(const, "co_names"):
            stream_names.update(const.co_names)
    commit_names = set(
        StreamingEngineController.commit_assistant_result.__code__.co_names
    )
    results.check(
        "message-action controller owns group L; thin ChatSidebar entrypoints remain",
        isinstance(owner._message_actions, MessageActionController)
        and "find_message_index" in MessageActionController.__dict__
        and "api_messages" in MessageActionController.__dict__
        and "clipboard_set" in MessageActionController.__dict__
        and "delete_message" in MessageActionController.__dict__
        and "drop_messages_from" in MessageActionController.__dict__
        and "regenerate_message" in MessageActionController.__dict__
        and "edit_resend_message" in MessageActionController.__dict__
        and "continue_message" in MessageActionController.__dict__
        and "handle_intent" in MessageActionController.__dict__
        and "find_message_index" in ChatSidebar._find_message_index.__code__.co_names
        and "api_messages" in ChatSidebar._api_messages.__code__.co_names
        and "handle_intent" in ChatSidebar._on_web_intent.__code__.co_names
        and "api_messages" in stream_names
        and "find_message_index" in commit_names
        and not hasattr(ChatSidebar, "_commit_assistant_result")
        and not hasattr(ChatSidebar, "_native_action_bar")
        and not hasattr(ChatSidebar, "_native_edit_user")
        and not hasattr(ChatSidebar, "_native_remove_message"),
    )


def characterize_send_and_midstream_errors(
    results: Results,
    app: Adw.Application,
) -> None:
    """Lock Phase-25 direct `_send` coverage and mid-stream error health."""
    print("\n[0l] Send and mid-stream error characterization", flush=True)

    class SendTranscript:
        def __init__(self, owner: "SendHarness", *, webkit: bool) -> None:
            self._owner = owner
            self.mode = "webkit" if webkit else "native"
            self.posts: list[dict] = []

        @property
        def is_webkit(self) -> bool:
            return self.mode == "webkit"

        def post(self, event: dict) -> None:
            self.posts.append(dict(event))

        def append_native_row(self, role, content, *, message_id=None, **kwargs):
            self._owner.appends.append((role, content, message_id, dict(kwargs)))
            self._owner.order.append(
                ("append_message", role, content, message_id)
            )
            return None

    class SendCli:
        def __init__(self) -> None:
            self.busy = False
            self.commands: list[str] = []
            self.command_result = False

        def is_busy(self) -> bool:
            return self.busy

        def try_command(self, text: str) -> bool:
            self.commands.append(text)
            return self.command_result

    class TraceMessages(list):
        def __init__(self, owner: "SendHarness") -> None:
            super().__init__()
            self._owner = owner

        def append(self, message):  # type: ignore[override]
            self._owner.order.append(("messages_append", dict(message)))
            return super().append(message)

    class SendConversation:
        def __init__(self, owner: "SendHarness") -> None:
            self._owner = owner
            self.messages: list[dict] = []
            self.conversation_id = "send-cid"

        def next_msg_id(self, prefix: str) -> str:
            mid = f"{prefix}-{len(self._owner.ids) + 1}"
            self._owner.ids.append(mid)
            self._owner.order.append(("next_msg_id", prefix, mid))
            return mid

        def append_local(self, message: dict[str, str]) -> None:
            self.messages.append(message)

        def persist_message(
            self, role: str, content: str, message_id: str | None = None
        ) -> None:
            self._owner.persisted.append((role, content, message_id))
            self._owner.order.append(("persist", role, content, message_id))

    class SendHarness:
        def __init__(self, *, webkit: bool = True) -> None:
            self.order: list[object] = []
            self._loading_model = False
            self._model = "send-model"
            self._health = SimpleNamespace(can_chat=True)
            self._composer_cli = SendCli()
            self.input = _CliInput("hello")
            self._transcript = SendTranscript(self, webkit=webkit)
            self.refresh_calls = 0
            self.ids: list[str] = []
            self.persisted: list[tuple] = []
            self.hints = 0
            self.stream_starts: list[dict] = []
            self.appends: list[tuple] = []
            self._conversation = SendConversation(self)
            self._streaming_engine = StreamingEngineController(
                client=OllamaClient(),
                get_store=lambda: None,  # type: ignore[arg-type]
                conversation=self._conversation,  # type: ignore[arg-type]
                message_actions=SimpleNamespace(  # type: ignore[arg-type]
                    api_messages=lambda: [],
                    find_message_index=lambda _mid: -1,
                ),
                transcript=self._transcript,  # type: ignore[arg-type]
                get_current_model=lambda: self._model,
                is_loading_model=lambda: self._loading_model,
                get_health=lambda: self._health,
                refresh_models=self._refresh_models,
                apply_health=lambda _state: None,
                set_status=lambda _text: None,
                sync_composer_hint=self._sync_composer_hint,
                is_cli_busy=self._composer_cli.is_busy,
                try_command=self._composer_cli.try_command,
                input_widget=self.input,
                send_control=None,
                stop_control=None,
            )
            self._streaming_engine.start_assistant_stream = (  # type: ignore[method-assign]
                self._start_assistant_stream
            )

        @property
        def _messages(self) -> list[dict]:
            return self._conversation.messages

        @_messages.setter
        def _messages(self, value: list[dict]) -> None:
            self._conversation.messages = value

        @property
        def _streaming(self) -> bool:
            return self._streaming_engine._streaming

        @_streaming.setter
        def _streaming(self, value: bool) -> None:
            self._streaming_engine._streaming = bool(value)

        def _refresh_models(self) -> bool:
            self.refresh_calls += 1
            self.order.append("refresh_models")
            return True

        def _sync_composer_hint(self) -> None:
            self.hints += 1
            self.order.append("sync_composer_hint")

        def _start_assistant_stream(self, **kwargs) -> None:
            self.stream_starts.append(dict(kwargs))
            self.order.append(("start_stream", dict(kwargs)))

        def _send(self) -> None:
            self._streaming_engine.input = self.input
            self._streaming_engine.send()

    # --- empty / busy / command / health / model guards ---
    empty = SendHarness()
    empty.input = _CliInput("   \n\t  ")
    empty._send()
    results.check(
        "_send ignores blank/whitespace-only composer input",
        empty.order == []
        and empty._messages == []
        and empty._composer_cli.commands == []
        and empty.input.get_buffer().text == "   \n\t  ",
    )

    streaming = SendHarness()
    streaming.input = _CliInput("still typing")
    streaming._streaming = True
    streaming._send()
    results.check(
        "_send is a no-op while an assistant stream is active",
        streaming.order == []
        and streaming._composer_cli.commands == []
        and streaming.input.get_buffer().text == "still typing",
    )

    loading = SendHarness()
    loading.input = _CliInput("still typing")
    loading._loading_model = True
    loading._send()
    results.check(
        "_send is a no-op while a model load is in progress",
        loading.order == []
        and loading._composer_cli.commands == []
        and loading.input.get_buffer().text == "still typing",
    )

    cli_busy = SendHarness()
    cli_busy.input = _CliInput("ollama list")
    cli_busy._composer_cli.busy = True
    cli_busy._send()
    results.check(
        "_send is a no-op while the composer CLI is busy",
        cli_busy.order == []
        and cli_busy._composer_cli.commands == []
        and cli_busy.input.get_buffer().text == "ollama list",
    )

    command = SendHarness()
    command.input = _CliInput("ollama pull llama3.2")
    command._composer_cli.command_result = True
    command._send()
    results.check(
        "_send routes composer commands through try_command and clears the buffer",
        command._composer_cli.commands == ["ollama pull llama3.2"]
        and command.input.get_buffer().text == ""
        and command._messages == []
        and command.stream_starts == []
        and command.order == [],
    )

    unhealthy = SendHarness()
    unhealthy.input = _CliInput("ping")
    unhealthy._health = SimpleNamespace(can_chat=False)
    unhealthy._send()
    results.check(
        "_send re-probes models when health cannot chat and does not send",
        unhealthy.refresh_calls == 1
        and unhealthy.order == ["refresh_models"]
        and unhealthy.input.get_buffer().text == "ping"
        and unhealthy._messages == []
        and unhealthy.stream_starts == [],
    )

    no_model = SendHarness()
    no_model.input = _CliInput("ping")
    no_model._model = None
    no_model._send()
    results.check(
        "_send is a no-op when no model is selected after command/health checks",
        no_model._composer_cli.commands == ["ping"]
        and no_model.input.get_buffer().text == "ping"
        and no_model._messages == []
        and no_model.stream_starts == []
        and no_model.refresh_calls == 0,
    )

    # --- successful WebKit path ordering ---
    web_send = SendHarness(webkit=True)
    web_send.input = _CliInput("  hello world  ")
    web_send._messages = TraceMessages(web_send)
    real_post = web_send._transcript.post

    def traced_post(event):
        web_send.order.append(("transcript_post", dict(event)))
        return real_post(event)

    web_send._transcript.post = traced_post  # type: ignore[method-assign]
    web_send._send()
    uid = web_send.ids[0]
    results.check(
        "WebKit _send clears buffer, posts transcript, then appends/persists/hints/starts",
        web_send.input.get_buffer().text == ""
        and list(web_send._messages)
        == [{"id": uid, "role": "user", "content": "hello world"}]
        and web_send.persisted == [("user", "hello world", uid)]
        and web_send.hints == 1
        and web_send.stream_starts == [{"mode": "new"}]
        and web_send.appends == []
        and web_send.order
        == [
            ("next_msg_id", "user", uid),
            (
                "transcript_post",
                {
                    "type": "message_added",
                    "id": uid,
                    "role": "user",
                    "text": "hello world",
                    "streaming": False,
                },
            ),
            (
                "messages_append",
                {"id": uid, "role": "user", "content": "hello world"},
            ),
            ("persist", "user", "hello world", uid),
            "sync_composer_hint",
            ("start_stream", {"mode": "new"}),
        ],
    )

    # --- successful native path ordering ---
    native_send = SendHarness(webkit=False)
    native_send.input = _CliInput("native hi")
    native_send._messages = TraceMessages(native_send)
    native_send._send()
    nuid = native_send.ids[0]
    results.check(
        "native _send appends the transcript row before projection/persist/hint/stream",
        native_send.input.get_buffer().text == ""
        and native_send.appends == [("user", "native hi", nuid, {})]
        and native_send._transcript.posts == []
        and native_send.order
        == [
            ("next_msg_id", "user", nuid),
            ("append_message", "user", "native hi", nuid),
            (
                "messages_append",
                {"id": nuid, "role": "user", "content": "native hi"},
            ),
            ("persist", "user", "native hi", nuid),
            "sync_composer_hint",
            ("start_stream", {"mode": "new"}),
        ]
        and native_send.stream_starts == [{"mode": "new"}],
    )

    # --- mid-stream non-cancellation error: classify_error + allow_empty ---
    def prepare_owner(owner: ChatSidebar) -> None:
        owner._streaming = False
        owner._stream_generation = 0
        owner._active_stream_cancel = None
        conversation = owner._store.create_conversation(model="stream-model")
        owner._conversation_id = conversation.id
        owner._model_session.set_current_model("stream-model")
        owner._messages = [{"id": "user-1", "role": "user", "content": "hi"}]
        owner._apply_health = lambda *_args, **_kwargs: None
        owner._streaming_engine._apply_health = owner._apply_health
        owner._commit_calls: list[tuple] = []
        real_commit = owner._streaming_engine.commit_assistant_result

        def record_commit(aid, final, **kwargs):
            owner._commit_calls.append((aid, final, kwargs))
            return real_commit(aid, final, **kwargs)

        owner._streaming_engine.commit_assistant_result = (  # type: ignore[method-assign]
            record_commit
        )

    def drive_stream(
        owner: ChatSidebar,
        *,
        chunks: list[str],
        error: Exception | None = None,
    ) -> None:
        flushers: list = []
        scripted = _ScriptedChatStream(chunks, error=error)
        owner.client.chat_stream = scripted  # type: ignore[method-assign]

        def capture_timeout(interval, callback):
            if getattr(callback, "__name__", "") == "flush_stream":
                flushers.append(callback)
            return 1

        with patch.object(
            streaming_engine_module.GLib,
            "timeout_add",
            side_effect=capture_timeout,
        ):
            owner._start_assistant_stream(mode="new")
        assert flushers, "stream begin must schedule flush_stream"
        wait_until(lambda: scripted.finished.is_set(), timeout=5)
        while flushers[0]():
            pass

    with (
        patch.object(ChatSidebar, "_restore_history", lambda _self: None),
        patch.object(ChatSidebar, "_refresh_models", lambda _self: False),
    ):
        live = ChatSidebar(app, client=OllamaClient())
    pump(0.05)
    prepare_owner(live)
    health_calls: list[HealthState] = []

    def capture_health(state):
        health_calls.append(state)

    live._apply_health = capture_health
    live._streaming_engine._apply_health = capture_health
    drive_stream(
        live,
        chunks=["Half"],
        error=OllamaError("CUDA out of memory while generating"),
    )
    results.check(
        "mid-stream OllamaError reclassifies health via classify_error(context=stream)",
        len(health_calls) == 1
        and health_calls[0].kind == HealthKind.OOM
        and health_calls[0].model == "stream-model"
        and health_calls[0].action == "retry_load"
        and "CUDA out of memory" in (health_calls[0].raw or ""),
    )
    results.check(
        "mid-stream error commits the partial text with allow_empty=True",
        live._commit_calls
        and live._commit_calls[-1][1] == "Half"
        and live._commit_calls[-1][2].get("allow_empty") is True
        and live._commit_calls[-1][2].get("mode") == "new"
        and not live._streaming,
    )

    prepare_owner(live)
    health_calls.clear()
    live._apply_health = capture_health
    live._streaming_engine._apply_health = capture_health
    drive_stream(
        live, chunks=[], error=OllamaError("stream interrupted unexpectedly")
    )
    results.check(
        "empty mid-stream error uses STREAM_LOST health and still allow_empty commits",
        len(health_calls) == 1
        and health_calls[0].kind == HealthKind.STREAM_LOST
        and live._commit_calls[-1][1] == ""
        and live._commit_calls[-1][2].get("allow_empty") is True
        and any(
            m.get("id") == live._commit_calls[-1][0]
            and m.get("content") == "(no response)"
            for m in live._messages
        ),
    )
    live.set_visible(False)

    stream_names = set(
        StreamingEngineController.start_assistant_stream.__code__.co_names
    )
    for const in StreamingEngineController.start_assistant_stream.__code__.co_consts:
        if hasattr(const, "co_names"):
            stream_names.update(const.co_names)
    results.check(
        "streaming engine owns send/start/commit; thin ChatSidebar entrypoints remain",
        isinstance(live._streaming_engine, StreamingEngineController)
        and "send" in StreamingEngineController.__dict__
        and "start_assistant_stream" in StreamingEngineController.__dict__
        and "commit_assistant_result" in StreamingEngineController.__dict__
        and "request_stop" in StreamingEngineController.__dict__
        and "invalidate_active_stream" in StreamingEngineController.__dict__
        and "send" in ChatSidebar._send.__code__.co_names
        and "start_assistant_stream"
        in ChatSidebar._start_assistant_stream.__code__.co_names
        and not hasattr(ChatSidebar, "_commit_assistant_result")
        and not hasattr(ChatSidebar, "_stream_finished")
        and not hasattr(ChatSidebar, "_append_message")
        and not hasattr(ChatSidebar, "_scroll_to_end")
        and "classify_error" in stream_names
        and "_apply_health" in stream_names,
    )


def main() -> int:
    results = Results()

    TMP = Path(tempfile.mkdtemp(prefix="cb-sidebar-interactions-"))
    os.environ["CHICKENBUTT_DB"] = str(TMP / "db.sqlite")
    os.environ["XDG_CONFIG_HOME"] = str(TMP / "config")
    os.environ["XDG_DATA_HOME"] = str(TMP / "data")

    settings_dir = TMP / "config" / "chickenbutt"
    settings_path = settings_dir / "settings.json"
    characterize_settings(results, settings_dir, settings_path)

    # Seed a stale settings file with the old, no-longer-read sidebar_open
    # key set to true, BEFORE constructing any window — proves it's ignored
    # rather than merely untested.
    settings_dir.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps({"sidebar_open": True}), encoding="utf-8"
    )

    Adw.init()
    characterize_health_probe(results)
    characterize_model_load(results)
    characterize_composer_cli_commands(results)
    characterize_conversation_lifecycle(results)
    app = Adw.Application(
        application_id="dev.local.chickenbutt.sidebarinteractions",
        flags=Gio.ApplicationFlags.NON_UNIQUE,
    )
    holder: dict = {"win": None}

    def on_activate(a):
        holder["win"] = ChatSidebar(a, client=OllamaClient())
        holder["win"].present()

    app.connect("activate", on_activate)
    app.register()
    app.activate()
    win: ChatSidebar = holder["win"]
    assert win is not None
    pump(0.5)
    characterize_transcript_reset_replay_removal(results, app)
    characterize_status_message_and_greeting(results, app)
    characterize_streaming_and_native_intent(results, app)
    characterize_message_actions(results, app)
    characterize_send_and_midstream_errors(results, app)
    characterize_ui_construction(results, app)
    characterize_sidebar_history_ui(results, app)
    characterize_composer_geometry(results, win)
    characterize_export(results, win, TMP)
    results.check(
        "window wires the extracted health owner through narrow dependencies",
        isinstance(win._health_probe, HealthProbeController)
        and win._health_probe.client is win.client
        and win._health_probe.model_combo is win.model_combo
        and win._health_probe._refresh_btn is win._refresh_btn
        and win._health_probe._health_banner is win._health_banner
        and win._health_probe._get_current_model() == win._model
        and win._health_probe._messages_empty() == (not win._messages)
        and win._health is win._health_probe.health
        and all(
            name not in win.__dict__
            for name in (
                "_health",
                "_suppress_model_select",
                "_health_action_id",
                "_health_action_model",
            )
        ),
    )
    results.check(
        "window wires the canonical model owner and read-only compatibility queries",
        isinstance(win._model_session, ModelLoadController)
        and win._model_session.client is win.client
        and win._model_session.model_combo is win.model_combo
        and win._model_session._load_overlay is win._load_overlay
        and win._model_session._messages_empty() == (not win._messages)
        and win._health_probe._get_current_model()
        == win._model_session.current_model
        and win._health_probe._is_loading() == win._model_session.is_loading
        and win._health_probe._is_load_failed() == win._model_session.has_failed
        and win._model == win._model_session.current_model
        and win._loading_model == win._model_session.is_loading
        and win._load_failed == win._model_session.has_failed
        and all(
            getattr(ChatSidebar, name).fset is None
            for name in ("_model", "_loading_model", "_load_failed")
        )
        and all(
            name not in win.__dict__
            for name in (
                "_model",
                "_loading_model",
                "_load_failed",
                "_load_generation",
                "_stop_load",
                "_load_pulse_id",
                "_load_indeterminate",
                "_greeted_models",
            )
        ),
    )
    results.check(
        "window wires the extracted sidebar/history owner through narrow dependencies",
        isinstance(win._sidebar_history, SidebarHistoryController)
        and win._sidebar_history._store is win._store
        and win._sidebar_history._sidebar is win._sidebar
        and win._sidebar_history._sidebar_btn is win._sidebar_btn
        and win._sidebar_history._history_list is win._history_list
        and win._sidebar_history._chat_title_label is win._chat_title_label
        and win._sidebar_history._is_loading_model() == win._loading_model
        and win._sidebar_history._is_streaming() == win._streaming
        and win._sidebar_history._get_active_conversation_id()
        == (win._conversation_id or "")
        and "_history_dirty" not in win.__dict__
        and "_sidebar_syncing" not in win.__dict__,
    )
    results.check(
        "window wires the extracted composer-CLI owner and rewires _send immediately",
        isinstance(win._composer_cli, ComposerCliController)
        and win._composer_cli.client is win.client
        and win._composer_cli.is_busy() is False
        and "_ollama_cli_busy" not in win.__dict__
        and isinstance(win._streaming_engine, StreamingEngineController)
        and win._streaming_engine._is_cli_busy == win._composer_cli.is_busy
        and win._streaming_engine._try_command == win._composer_cli.try_command
        and "send" in ChatSidebar._send.__code__.co_names
        and "rebind_next_msg_id" in ComposerCliController.__dict__
        and "post_status_message"
        in ChatSidebar._post_status_message.__code__.co_names
        and "try_command" in ChatSidebar._try_composer_command.__code__.co_names,
    )
    results.check(
        "window wires the extracted conversation-lifecycle owner and migrates providers",
        isinstance(win._conversation, ConversationLifecycleController)
        and win._conversation._store is win._store
        and win._messages is win._conversation.messages
        and win._conversation_id == win._conversation.conversation_id
        and "_messages" not in win.__dict__
        and "_conversation_id" not in win.__dict__
        and "_msg_counter" not in win.__dict__
        and "_history_restored" not in win.__dict__
        and getattr(win._model_session._ensure_conversation, "__self__", None)
        is win._conversation
        and getattr(win._model_session._messages_empty, "__self__", None)
        is win._conversation
        and getattr(win._health_probe._messages_empty, "__self__", None)
        is win._conversation
        and getattr(win._health_probe._active_conversation_model, "__self__", None)
        is win._conversation
        and getattr(win._composer_cli._next_msg_id, "__self__", None)
        is win._conversation
        and getattr(win._transcript._message_id_provider, "__self__", None)
        is win._conversation
        and getattr(win._sidebar_history._on_activate, "__self__", None)
        is win._conversation
        and getattr(win._sidebar_history._on_delete, "__self__", None)
        is win._conversation
        and getattr(win._conversation_exporter._title_provider, "__self__", None)
        is win._conversation
        and not hasattr(ChatSidebar, "_mark_history_dirty")
        and not hasattr(ChatSidebar, "_rebuild_history_list"),
    )

    # === [1] Startup: sidebar hidden, toggle inactive ===
    print("\n[1] Startup sidebar state (despite a stale sidebar_open=true settings file)", flush=True)
    results.check("sidebar hidden on startup", win._sidebar.get_visible() is False)
    results.check(
        "stale sidebar_open=true in settings.json was ignored",
        win._sidebar.get_visible() is False,
    )
    results.check("sidebar toggle button inactive on startup", win._sidebar_btn.get_active() is False)

    # === [2] Opening/closing still works ===
    print("\n[2] Opening and closing the sidebar", flush=True)
    win.toggle_sidebar(True)
    pump(0.1)
    results.check("toggle_sidebar(True) opens it", win._sidebar.get_visible() is True)
    results.check("toggle button reflects open state", win._sidebar_btn.get_active() is True)
    win.toggle_sidebar(False)
    pump(0.1)
    results.check("toggle_sidebar(False) closes it", win._sidebar.get_visible() is False)
    results.check("toggle button reflects closed state", win._sidebar_btn.get_active() is False)

    # === [3] Model dropdown lives in the sidebar's Model Selection block ===
    print("\n[3] Model dropdown location", flush=True)
    results.check(
        "exactly one model dropdown, a descendant of the sidebar",
        win.model_combo is not None and is_descendant(win.model_combo, win._sidebar),
    )
    scroller = direct_child_ancestor(win._history_list, win._sidebar)
    model_block = direct_child_ancestor(win.model_combo, win._sidebar)
    foot = direct_child_ancestor(win._settings_btn, win._sidebar)
    idx_scroller = child_index(win._sidebar, scroller)
    idx_model = child_index(win._sidebar, model_block)
    idx_foot = child_index(win._sidebar, foot)
    results.check(
        "model selection appears above the conversation list",
        -1 not in (idx_scroller, idx_model) and idx_model < idx_scroller,
        f"scroller={idx_scroller} model={idx_model}",
    )
    results.check(
        "model selection appears before the Settings footer",
        -1 not in (idx_model, idx_foot) and idx_model < idx_foot,
        f"model={idx_model} foot={idx_foot}",
    )
    model_labels = [
        child.get_label()
        for child in direct_children(model_block)
        if isinstance(child, Gtk.Label)
    ]
    results.check(
        "model selection header reads Model Selection",
        model_labels == ["Model Selection"],
        str(model_labels),
    )
    results.check(
        "model selection block draws a separator below the dropdown",
        model_block is not None
        and "chat-sidebar-model-block" in model_block.get_css_classes(),
    )
    w, h = win.model_combo.get_size_request()
    results.check("model dropdown is no longer fixed to 320px wide", w != 320, f"size_request={(w, h)}")
    results.check("model dropdown keeps its 38px height", h == 38, f"size_request={(w, h)}")

    # === [4] Health banner stays in the main chat column ===
    print("\n[4] Health banner location", flush=True)
    chat_column = win._transcript.widget.get_parent()
    outer = chat_column.get_parent()
    results.check(
        "health banner is not a descendant of the sidebar",
        not is_descendant(win._health_banner, win._sidebar),
    )
    results.check(
        "health banner shares the main-content container with the transcript",
        win._health_banner.get_parent() is outer,
    )

    # === [5] Model selection and last-model persistence still work ===
    print("\n[5] Model selection and last-model persistence (real refresh/select/load chain)", flush=True)
    # Let the real cold-start model probe/warm-up (kicked off from __init__)
    # settle first — otherwise our explicit _refresh_models() call below
    # just no-ops against the in-flight real one (_loading_model guard) and
    # we'd observe the real model instead of the fake ones we're about to
    # substitute.
    wait_until(lambda: not win._loading_model, timeout=60.0)
    pump(0.2)
    win.client.list_models = lambda: ["fake-model-a", "fake-model-b"]
    win.client.is_model_loaded = lambda model: True
    win._refresh_models()
    ok = wait_until(lambda: win._model == "fake-model-a" and not win._loading_model, timeout=15.0)
    pump(0.2)
    results.check("initial refresh selects and loads the first fake model", ok, str(win._model))
    from window import _load_last_model

    results.check(
        "last-model persisted after initial load",
        _load_last_model() == "fake-model-a",
        str(_load_last_model()),
    )
    win.model_combo.set_selected(1)
    ok = wait_until(lambda: win._model == "fake-model-b" and not win._loading_model, timeout=15.0)
    pump(0.2)
    results.check("selecting a different model in the dropdown still loads it", ok, str(win._model))
    results.check(
        "last-model persistence follows the new selection",
        _load_last_model() == "fake-model-b",
        str(_load_last_model()),
    )

    # === [6] Representative GTK click targets report the pointer cursor ===
    print("\n[6] GTK pointer cursor on representative click targets", flush=True)
    for label, widget in (
        ("sidebar toggle", win._sidebar_btn),
        ("clear conversation", win._clear_btn),
        ("refresh models", win._refresh_btn),
        ("model dropdown", win.model_combo),
        ("sidebar new chat", win._sidebar_new_btn),
        ("sidebar settings", win._settings_btn),
        ("health banner action", win._health_action_btn),
        ("send", win.send_btn),
        ("stop", win.stop_btn),
    ):
        results.check(f"{label} reports pointer cursor", cursor_name(widget) == "pointer", str(cursor_name(widget)))

    # === [7] A generated conversation row + its overflow button ===
    print("\n[7] Conversation row + overflow control pointer cursor", flush=True)
    conv = win._store.create_conversation(model="fake-model-a")
    win._store.append_message(conv.id, role="user", content="hi", message_id="m1")
    win._history_dirty = True
    win._sidebar_history.rebuild_history_list()
    pump(0.1)
    row = win._history_list.get_first_child()
    found_row = None
    while row is not None:
        if row.get_name() == conv.id:
            found_row = row
            break
        row = row.get_next_sibling()
    results.check("generated conversation row found", found_row is not None)
    if found_row is not None:
        results.check("conversation row reports pointer cursor", cursor_name(found_row) == "pointer")
        outer_box = found_row.get_child()
        more_btn = outer_box.get_last_child() if outer_box is not None else None
        results.check(
            "row's overflow (more) button reports pointer cursor",
            more_btn is not None and cursor_name(more_btn) == "pointer",
        )

    # === [8] WebKit: links, code controls, message-action buttons vs. plain text ===
    if win._transcript.is_webkit:
        print("\n[8] WebKit computed cursor: pointer for interactive elements, not prose", flush=True)
        web = win._transcript._web
        wait_until(lambda: web._ready, timeout=20.0)
        pump(0.3)
        web._view.evaluate_javascript(
            "window.chickenbuttApply({"
            "type: 'conversation_reset',"
            "messages: [{id: 'cursor-check', role: 'assistant', "
            "content: 'Plain prose. [a link](https://example.com/safe)\\n\\n"
            "```python\\nprint(1)\\n```\\n'}]"
            "});",
            -1, None, None, None, None, None,
        )
        pump(0.5)
        captured: dict = {}
        report = eval_js_value(
            web,
            "(function(){"
            "  const root = document.querySelector('[data-id=\"cursor-check\"]');"
            "  function cur(sel) {"
            "    const el = root.querySelector(sel);"
            "    return el ? getComputedStyle(el).cursor : null;"
            "  }"
            "  return JSON.stringify({"
            "    link: cur('a'),"
            "    copyBtn: cur('[data-copy]'),"
            "    expandBtn: cur('[data-expand]'),"
            "    actionBtn: cur('.msg-actions [data-action]') || cur('.msg-actions button'),"
            "    prose: cur('p'),"
            "  });"
            "})();",
            captured,
        )
        results.check("link computed cursor is pointer", (report or {}).get("link") == "pointer", str(report))
        results.check("code copy control computed cursor is pointer", (report or {}).get("copyBtn") == "pointer", str(report))
        results.check("code expand control computed cursor is pointer", (report or {}).get("expandBtn") == "pointer", str(report))
        results.check(
            "message-action control computed cursor is pointer",
            (report or {}).get("actionBtn") == "pointer",
            str(report),
        )
        results.check(
            "noninteractive prose text does NOT compute to pointer",
            (report or {}).get("prose") not in ("pointer", None),
            str(report),
        )
    else:
        print("\n[8] Skipped (native transcript mode)", flush=True)

    # === [9] A genuinely new window construction also starts closed ===
    print("\n[9] A fresh ChatSidebar construction starts closed again", flush=True)
    # Re-assert the stale flag right before this specific construction, in
    # case anything upstream rewrote settings.json without it.
    data = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.is_file() else {}
    data["sidebar_open"] = True
    settings_path.write_text(json.dumps(data), encoding="utf-8")

    app2 = Adw.Application(
        application_id="dev.local.chickenbutt.sidebarinteractions2",
        flags=Gio.ApplicationFlags.NON_UNIQUE,
    )
    holder2: dict = {"win": None}

    def on_activate2(a):
        holder2["win"] = ChatSidebar(a, client=OllamaClient())
        holder2["win"].present()

    app2.connect("activate", on_activate2)
    app2.register()
    app2.activate()
    win2: ChatSidebar = holder2["win"]
    assert win2 is not None
    pump(0.3)
    results.check(
        "a freshly constructed second window also starts with the sidebar hidden",
        win2._sidebar.get_visible() is False,
    )
    results.check(
        "its sidebar toggle button is also inactive",
        win2._sidebar_btn.get_active() is False,
    )

    print("\n=== Summary ===", flush=True)
    print(f"Passed: {len(results.ok)}  Failed: {len(results.fail)}", flush=True)
    for f in results.fail:
        print(f"  - {f}", flush=True)
    return 1 if results.fail else 0


if __name__ == "__main__":
    try:
        code = main()
        os._exit(code)
    except Exception:
        import traceback

        traceback.print_exc()
        os._exit(2)
