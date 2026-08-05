#!/usr/bin/env python3
"""Phase 2: per-model basics — tiers, styles, reset, no request when empty."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from model_profile import (  # noqa: E402
    ModelProfileService,
    build_options_from_prefs,
    keep_alive_id_for_value,
)
from ollama_client import build_chat_body, build_generate_body  # noqa: E402


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


def main() -> int:
    r = Results()
    with tempfile.TemporaryDirectory(prefix="cb-phase2-") as td:
        directory = Path(td)
        path = directory / "settings.json"
        path.write_text("{}\n", encoding="utf-8")
        svc = ModelProfileService(settings_dir=directory, settings_path=path)

        print("\n[1] Empty profile omits optional request fields", flush=True)
        params = svc.request_params("alpha:1")
        r.check("empty is_empty", params.is_empty())
        body = build_chat_body("alpha:1", [], options=params.options, keep_alive=params.keep_alive, think=params.think)
        r.check(
            "chat body legacy keys only",
            set(body.keys()) == {"model", "messages", "stream"},
            str(body.keys()),
        )
        gen = build_generate_body("alpha:1", options=params.options, keep_alive=params.keep_alive)
        r.check(
            "generate body legacy keys only",
            set(gen.keys()) == {"model", "prompt", "stream"},
            str(gen.keys()),
        )

        print("\n[2] Context tier and response style are independent", flush=True)
        svc.apply_model_basics(
            "alpha:1",
            context_tier="8k",
            response_style="precise",
            keep_alive="5m",
            clear_keep_alive=False,
            clear_think=True,
        )
        p = svc.request_params("alpha:1")
        r.check("num_ctx 8192", p.options and p.options.get("num_ctx") == 8192, str(p.options))
        r.check("temperature 0.2", p.options and p.options.get("temperature") == 0.2, str(p.options))
        r.check("keep_alive 5m", p.keep_alive == "5m")
        chat = build_chat_body("alpha:1", [], options=p.options, keep_alive=p.keep_alive)
        r.check("options nested", "options" in chat and chat["options"]["num_ctx"] == 8192)
        r.check("keep_alive top-level", chat.get("keep_alive") == "5m")

        # Change only style to creative — context remains
        prof = svc.get_profile("alpha:1")
        svc.apply_model_basics(
            "alpha:1",
            context_tier=str(prof.get("context_tier") or "8k"),
            response_style="creative",
            keep_alive="5m",
            clear_keep_alive=False,
            clear_think=True,
        )
        p2 = svc.request_params("alpha:1")
        r.check("ctx unchanged after style change", p2.options and p2.options.get("num_ctx") == 8192)
        r.check("creative temp 1.0", p2.options and p2.options.get("temperature") == 1.0)

        # Custom temperature marks custom style path
        svc.apply_model_basics(
            "alpha:1",
            context_tier="8k",
            response_style="custom",
            temperature_custom=0.42,
            keep_alive="5m",
            clear_keep_alive=False,
            clear_think=True,
        )
        p3 = svc.request_params("alpha:1")
        r.check("custom temperature", p3.options and abs(p3.options.get("temperature", -1) - 0.42) < 0.001)
        r.check("ctx still 8k under custom style", p3.options and p3.options.get("num_ctx") == 8192)
        r.check(
            "profile response_style custom",
            svc.get_profile("alpha:1").get("response_style") == "custom",
        )

        print("\n[3] Per-name isolation", flush=True)
        svc.apply_model_basics(
            "beta:2",
            context_tier="4k",
            response_style="balanced",
            clear_keep_alive=True,
            clear_think=True,
        )
        pa = svc.request_params("alpha:1")
        pb = svc.request_params("beta:2")
        r.check("alpha still custom temp", pa.options and abs(pa.options.get("temperature", -1) - 0.42) < 0.001)
        r.check("beta num_ctx 4096", pb.options and pb.options.get("num_ctx") == 4096)
        r.check("beta omits temperature (balanced)", pb.options is not None and "temperature" not in pb.options)

        print("\n[4] Reset clears prefs, keeps observations", flush=True)
        svc.ensure_digest("alpha:1", "sha256:obs1")
        svc.record_metrics(
            "alpha:1",
            {"eval_count": 3, "eval_duration": 100_000_000, "done": True},
            digest="sha256:obs1",
        )
        before = svc.get_profile("alpha:1")
        r.check("has options before reset", "options" in before)
        r.check(
            "has metrics before reset",
            isinstance(before.get("observations"), dict)
            and "last_metrics" in before["observations"],
        )
        svc.reset_preferences("alpha:1")
        after = svc.get_profile("alpha:1")
        r.check("options gone", "options" not in after)
        r.check("context_tier gone", "context_tier" not in after)
        r.check("response_style gone", "response_style" not in after)
        r.check("keep_alive gone", "keep_alive" not in after)
        r.check(
            "observations kept",
            isinstance(after.get("observations"), dict)
            and after["observations"].get("digest") == "sha256:obs1"
            and "last_metrics" in after["observations"],
        )
        r.check("request empty after reset", svc.request_params("alpha:1").is_empty())

        print("\n[5] Max output and keep-alive mapping", flush=True)
        svc.apply_model_basics(
            "gamma:3",
            context_tier="auto",
            response_style="balanced",
            num_predict=512,
            keep_alive=-1,
            clear_keep_alive=False,
            clear_think=True,
        )
        pg = svc.request_params("gamma:3")
        r.check("num_predict 512", pg.options and pg.options.get("num_predict") == 512)
        r.check("keep forever -1", pg.keep_alive == -1)
        r.check("keep id forever", keep_alive_id_for_value(-1) == "forever")
        r.check(
            "auto omits num_ctx",
            pg.options is not None and "num_ctx" not in pg.options,
        )

        print("\n[6] build_options helpers", flush=True)
        opts = build_options_from_prefs(
            context_tier="16k", response_style="precise", num_predict=0
        )
        r.check("16k+precise", opts == {"num_ctx": 16384, "temperature": 0.2}, str(opts))
        opts2 = build_options_from_prefs(context_tier="auto", response_style="balanced")
        r.check("auto+balanced empty options", opts2 is None, str(opts2))

        # Warm-up and chat share params
        shared = svc.request_params("gamma:3")
        cb = build_chat_body("gamma:3", [], options=shared.options, keep_alive=shared.keep_alive)
        gb = build_generate_body("gamma:3", options=shared.options, keep_alive=shared.keep_alive)
        r.check("shared options", cb.get("options") == gb.get("options"))
        r.check("shared keep_alive", cb.get("keep_alive") == gb.get("keep_alive"))

        disk = json.loads(path.read_text(encoding="utf-8"))
        r.check(
            "stored under exact name beta:2",
            "beta:2" in (disk.get("model_profiles") or {}),
        )

    print(f"\nPhase 2 results: {len(r.ok)} passed, {len(r.fail)} failed", flush=True)
    if r.fail:
        print("FAILED:", ", ".join(r.fail), flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
