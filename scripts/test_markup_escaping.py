#!/usr/bin/env python3
"""Regression: dynamic text reaching Adw row subtitles is Pango-safe.

Adw.PreferencesRow:use-markup defaults to TRUE, so subtitles are parsed as
Pango markup. The context-usage label for tiny usage is "... tokens (<1%)",
whose "<1" was parsed as the start of a tag and aborted rendering with
  Failed to set text '150 / 262,144 tokens (<1%)' from markup due to error
  parsing markup: "1%)<" is not a valid name

Proof here is a real Pango.parse_markup() run, not substring matching:
escaped text must parse AND round-trip to the identical visible string,
while the unescaped original must genuinely fail (so this test can fail).
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import gi

gi.require_version("Pango", "1.0")
from gi.repository import GLib, Pango  # noqa: E402

from connection_settings import _markup_safe  # noqa: E402
from model_fit import context_usage_view  # noqa: E402


class Results:
    def __init__(self) -> None:
        self.ok: list[str] = []
        self.fail: list[str] = []

    def check(self, name: str, cond: bool, detail: str = "") -> None:
        (self.ok if cond else self.fail).append(name)
        print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f" — {detail}" if detail else ""), flush=True)


def parses(markup: str) -> tuple[bool, str]:
    """Return (parsed_ok, recovered_plain_text)."""
    try:
        ok, _attrs, text, _accel = Pango.parse_markup(markup, -1, "\x00")
        return bool(ok), text
    except GLib.Error as exc:
        return False, str(exc)


def main() -> int:
    r = Results()

    print("\n[1] The reported failure: tiny usage renders '(<1%)'", flush=True)
    tiny = context_usage_view(used_tokens=150, budget=262_144, estimated=False)
    r.check("[1] label contains the '<1%' form", "<1%" in tiny.label, tiny.label)

    print("\n[2] Unescaped label really is invalid markup (this test can fail)", flush=True)
    raw_ok, raw_detail = parses(tiny.label)
    r.check("[2] raw label is rejected by Pango", not raw_ok, raw_detail)

    print("\n[3] Escaped label parses and round-trips exactly", flush=True)
    esc_ok, esc_text = parses(_markup_safe(tiny.label))
    r.check("[3] escaped label parses", esc_ok, esc_text)
    r.check("[3] round-trips to the identical visible text", esc_text == tiny.label,
            f"{esc_text!r} vs {tiny.label!r}")

    print("\n[4] Ordinary percentages still render unchanged", flush=True)
    normal = context_usage_view(used_tokens=42_000, budget=100_000, estimated=False)
    r.check("[4] label shows a plain percentage", "42%" in normal.label, normal.label)
    n_ok, n_text = parses(_markup_safe(normal.label))
    r.check("[4] escaped label parses", n_ok, n_text)
    r.check("[4] round-trips unchanged", n_text == normal.label, f"{n_text!r} vs {normal.label!r}")
    r.check("[4] escaping is a no-op for markup-free text",
            _markup_safe(normal.label) == normal.label, _markup_safe(normal.label))

    print("\n[5] Other markup metacharacters in dynamic values", flush=True)
    for hostile in ("qwen<3:8b", "Tom & Jerry", '"quoted"', "a>b", "<b>bold</b>"):
        ok, text = parses(_markup_safe(hostile))
        r.check(f"[5] {hostile!r} parses and round-trips", ok and text == hostile, f"{text!r}")

    print("\n=== Summary ===", flush=True)
    print(f"  {len(r.ok)} passed, {len(r.fail)} failed", flush=True)
    if r.fail:
        for n in r.fail:
            print(f"  - {n}", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
