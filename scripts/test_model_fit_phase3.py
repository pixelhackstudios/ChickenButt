#!/usr/bin/env python3
"""Phase 3: passive Model Fit helpers — no request mutation."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from model_fit import (  # noqa: E402
    UNAVAILABLE,
    CONTEXT_WARN_RATIO,
    capabilities_label,
    context_budget,
    context_usage_view,
    estimate_conversation_tokens,
    format_bytes,
    format_tokens,
    format_tps,
    gpu_resident_portion,
    last_metrics_if_current,
    match_running_model,
    merge_descriptor,
)
from ollama_client import ModelDescriptor, RunningModelInfo, build_chat_body  # noqa: E402
from model_profile import ModelProfileService  # noqa: E402
import tempfile
import json


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
    print("\n[1] Formatting and labels", flush=True)
    r.check("bytes none → Unavailable", format_bytes(None) == UNAVAILABLE)
    r.check("bytes positive", "GB" in format_bytes(5_600_000_000) or "MB" in format_bytes(5_600_000_000))
    r.check("tokens", format_tokens(8192) == "8,192")
    r.check("tps", "tok/s" in format_tps(42.7))
    r.check("tps none", format_tps(None) == UNAVAILABLE)
    portion = gpu_resident_portion(1000, 950)
    r.check(
        "GPU-resident portion wording",
        "portion" in portion.lower() or "%" in portion,
        portion,
    )
    r.check(
        "not utilization",
        "utilization" not in portion.lower(),
        portion,
    )
    r.check(
        "missing residency unavailable",
        gpu_resident_portion(None, 100) == UNAVAILABLE,
    )
    r.check("caps empty", capabilities_label(()) == UNAVAILABLE)
    r.check("caps join", "thinking" in capabilities_label(("completion", "thinking")))

    print("\n[2] Running model match + merge", flush=True)
    running = [
        RunningModelInfo(
            name="ornith:9b",
            size=1000,
            size_vram=900,
            context_length=8192,
            digest="sha256:abc",
        )
    ]
    r.check("exact match", match_running_model("ornith:9b", running) is not None)
    r.check("no match", match_running_model("other:1", running) is None)
    show = ModelDescriptor(
        name="ornith:9b",
        parameter_size="9B",
        quantization="Q4_K_M",
        context_length=32768,
        capabilities=("completion",),
    )
    tags = ModelDescriptor(name="ornith:9b", digest="sha256:abc", size=5_000_000)
    merged = merge_descriptor(show, tags)
    r.check("merged size from tags", merged is not None and merged.size == 5_000_000)
    r.check("merged quant from show", merged.quantization == "Q4_K_M")
    r.check("merged digest from tags", merged.digest == "sha256:abc")

    print("\n[3] Digest-scoped metrics", flush=True)
    profile = {
        "last_seen_digest": "sha256:abc",
        "observations": {
            "digest": "sha256:abc",
            "last_metrics": {
                "generation_tokens_per_sec": 40.0,
                "prompt_tokens_per_sec": 100.0,
                "peak_context_tokens": 500,
            },
        },
    }
    m = last_metrics_if_current(profile, current_digest="sha256:abc")
    r.check("metrics match digest", m is not None and m["generation_tokens_per_sec"] == 40.0)
    r.check(
        "metrics cleared on digest mismatch",
        last_metrics_if_current(profile, current_digest="sha256:other") is None,
    )
    profile2 = {
        "last_seen_digest": "sha256:new",
        "observations": {
            "digest": "sha256:old",
            "last_metrics": {"generation_tokens_per_sec": 1.0},
        },
    }
    r.check(
        "obs digest != last_seen → hide",
        last_metrics_if_current(profile2, current_digest=None) is None,
    )

    print("\n[4] Context usage estimated + warning", flush=True)
    msgs = [
        {"role": "user", "content": "hello world " * 50},
        {"role": "assistant", "content": "reply " * 50},
    ]
    est = estimate_conversation_tokens(msgs)
    r.check("estimate positive", est > 0, str(est))
    budget = context_budget(
        allocated_ctx=8192, max_ctx=32768, profile_num_ctx=4096
    )
    r.check("budget prefers allocated", budget == 8192)
    view = context_usage_view(used_tokens=est, budget=8192, estimated=True)
    r.check("estimated label", view.label.lower().startswith("estimated"), view.label)
    r.check("no warn at low usage", view.warn is False)
    high = context_usage_view(
        used_tokens=int(8192 * CONTEXT_WARN_RATIO) + 1,
        budget=8192,
        estimated=True,
    )
    r.check("warn at threshold", high.warn is True, high.label)
    measured = context_usage_view(used_tokens=100, budget=8192, estimated=False)
    r.check(
        "measured not estimated prefix",
        not measured.label.lower().startswith("estimated"),
        measured.label,
    )
    tiny = context_usage_view(used_tokens=23, budget=16384, estimated=False)
    r.check(
        "tiny nonzero usage shows <1%",
        "<1%" in tiny.label and "0%" not in tiny.label,
        tiny.label,
    )
    zero = context_usage_view(used_tokens=0, budget=16384, estimated=True)
    r.check("true zero still 0%", "(0%)" in zero.label, zero.label)
    missing = context_usage_view(used_tokens=10, budget=None, estimated=True)
    r.check("no budget → Unavailable", missing.label == UNAVAILABLE)

    print("\n[5] Fit does not invent request options", flush=True)
    body = build_chat_body("m", [{"role": "user", "content": "x"}])
    r.check("chat body still bare", set(body.keys()) == {"model", "messages", "stream"})

    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "s.json"
        path.write_text("{}\n", encoding="utf-8")
        svc = ModelProfileService(settings_dir=Path(td), settings_path=path)
        r.check("empty profile still empty params", svc.request_params("ornith:9b").is_empty())
        # Recording metrics does not set options
        svc.ensure_digest("ornith:9b", "sha256:abc")
        svc.record_metrics(
            "ornith:9b",
            {"eval_count": 10, "eval_duration": 500_000_000, "done": True},
            digest="sha256:abc",
        )
        r.check(
            "metrics alone do not create request options",
            svc.request_params("ornith:9b").is_empty(),
        )
        disk = json.loads(path.read_text(encoding="utf-8"))
        prof = disk["model_profiles"]["ornith:9b"]
        r.check("no options key from metrics", "options" not in prof)

    print(f"\nPhase 3 results: {len(r.ok)} passed, {len(r.fail)} failed", flush=True)
    if r.fail:
        print("FAILED:", ", ".join(r.fail), flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
