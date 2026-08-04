#!/usr/bin/env python3
"""Phase 0 acceptance: settings schema, client options/metrics, model profiles.

Does not require a live Ollama server or GTK UI for core coverage. Uses a
local stub for stream/on_done and body-shape checks.
"""

from __future__ import annotations

import json
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app_settings  # noqa: E402
from model_profile import (  # noqa: E402
    ModelProfileService,
    metrics_from_done_chunk,
)
from ollama_client import (  # noqa: E402
    OllamaClient,
    OllamaError,
    build_chat_body,
    build_generate_body,
    descriptor_from_show,
    descriptor_from_tags_entry,
)


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


class CapturingStub:
    """Accept one connection, capture request body, serve NDJSON chat."""

    def __init__(self, chunks: list[dict] | None = None) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self.request_body: bytes = b""
        self.chunks = chunks or [
            {"message": {"content": "hi"}, "done": False},
            {
                "message": {"content": ""},
                "done": True,
                "eval_count": 10,
                "eval_duration": 500_000_000,
                "prompt_eval_count": 5,
                "prompt_eval_duration": 100_000_000,
            },
        ]
        self._thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def start(self) -> None:
        def run() -> None:
            conn, _ = self.sock.accept()
            try:
                conn.settimeout(5)
                buf = b""
                while b"\r\n\r\n" not in buf:
                    data = conn.recv(4096)
                    if not data:
                        break
                    buf += data
                header, _, rest = buf.partition(b"\r\n\r\n")
                clen = 0
                for line in header.decode("latin-1", errors="replace").split("\r\n"):
                    if line.lower().startswith("content-length:"):
                        clen = int(line.split(":", 1)[1].strip())
                body = rest
                while len(body) < clen:
                    body += conn.recv(4096)
                self.request_body = body[:clen]
                conn.sendall(
                    b"HTTP/1.1 200 OK\r\n"
                    b"Content-Type: application/x-ndjson\r\n"
                    b"Transfer-Encoding: chunked\r\n"
                    b"Connection: close\r\n"
                    b"\r\n"
                )
                for obj in self.chunks:
                    payload = (json.dumps(obj) + "\n").encode("utf-8")
                    conn.sendall(
                        f"{len(payload):x}\r\n".encode() + payload + b"\r\n"
                    )
                conn.sendall(b"0\r\n\r\n")
            except OSError:
                pass
            finally:
                try:
                    conn.close()
                except OSError:
                    pass

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass
        if self._thread is not None:
            self._thread.join(timeout=2)


class HangStub:
    """Send one content chunk then hang until client cancels."""

    def __init__(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self.accepted = threading.Event()

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def start(self) -> None:
        def run() -> None:
            conn, _ = self.sock.accept()
            self.accepted.set()
            try:
                conn.settimeout(5)
                buf = b""
                while b"\r\n\r\n" not in buf:
                    data = conn.recv(4096)
                    if not data:
                        break
                    buf += data
                # drain body best-effort
                conn.settimeout(0.2)
                try:
                    while conn.recv(4096):
                        pass
                except OSError:
                    pass
                conn.settimeout(None)
                conn.sendall(
                    b"HTTP/1.1 200 OK\r\n"
                    b"Content-Type: application/x-ndjson\r\n"
                    b"Transfer-Encoding: chunked\r\n"
                    b"\r\n"
                )
                payload = (
                    json.dumps({"message": {"content": "x"}, "done": False}) + "\n"
                ).encode()
                conn.sendall(f"{len(payload):x}\r\n".encode() + payload + b"\r\n")
                while True:
                    data = conn.recv(4096)
                    if not data:
                        break
            except OSError:
                pass
            finally:
                try:
                    conn.close()
                except OSError:
                    pass

        threading.Thread(target=run, daemon=True).start()

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass


def test_settings_compat(r: Results, tmp: Path) -> None:
    print("\n[1] Settings storage compatibility", flush=True)
    path = tmp / "settings.json"
    directory = tmp

    # Old file: only last_model
    path.write_text(json.dumps({"last_model": "qwen3:8b"}) + "\n", encoding="utf-8")
    loaded = app_settings.load_settings(path)
    r.check("old last_model-only file loads", loaded.get("last_model") == "qwen3:8b")
    r.check(
        "missing ollama receives defaults",
        isinstance(loaded.get("ollama"), dict)
        and loaded["ollama"]["base_url"] == app_settings.DEFAULT_BASE_URL,
    )
    r.check(
        "missing model_profiles is empty mapping",
        loaded.get("model_profiles") == {},
    )

    # Unknown keys preserved
    path.write_text(
        json.dumps({"last_model": "a", "keep_me": True, "nested": {"x": 1}}) + "\n",
        encoding="utf-8",
    )
    loaded2 = app_settings.load_settings(path)
    r.check("unknown top-level keys preserved", loaded2.get("keep_me") is True)
    r.check("unknown nested objects preserved", loaded2.get("nested") == {"x": 1})

    # Corrupt file fails safely
    path.write_text("{broken", encoding="utf-8")
    r.check("corrupt file yields empty raw read", app_settings._read_settings(path) == {})
    norm = app_settings.load_settings(path)
    r.check("corrupt file normalizes to defaults", "ollama" in norm and "model_profiles" in norm)

    # Non-mapping root
    path.write_text("[1,2]", encoding="utf-8")
    r.check("array root yields empty raw", app_settings._read_settings(path) == {})

    # Atomic write round-trip with update_settings
    path.unlink(missing_ok=True)

    def mut(data: dict) -> None:
        data["last_model"] = "mistral:7b"
        data["extra_flag"] = "yes"

    written = app_settings.update_settings(
        mut, settings_dir=directory, settings_path=path
    )
    r.check("update_settings writes last_model", written.get("last_model") == "mistral:7b")
    r.check("update_settings preserves extra", written.get("extra_flag") == "yes")
    disk = json.loads(path.read_text(encoding="utf-8"))
    r.check("disk has ollama defaults", "ollama" in disk)
    r.check("disk has model_profiles", "model_profiles" in disk)


def test_request_body_shapes(r: Results) -> None:
    print("\n[2] Request body omission and field placement", flush=True)
    bare = build_chat_body("m", [{"role": "user", "content": "hi"}])
    r.check(
        "unset profile body matches legacy keys",
        set(bare.keys()) == {"model", "messages", "stream"},
        str(bare.keys()),
    )
    r.check("stream true", bare["stream"] is True)

    with_opts = build_chat_body(
        "m",
        [],
        options={"num_ctx": 8192, "temperature": 0.2},
        keep_alive="5m",
        think=True,
    )
    r.check("options nested under options", with_opts.get("options") == {"num_ctx": 8192, "temperature": 0.2})
    r.check("keep_alive top-level", with_opts.get("keep_alive") == "5m")
    r.check("think top-level", with_opts.get("think") is True)
    r.check("empty options dict omitted", "options" not in build_chat_body("m", [], options={}))

    gen = build_generate_body("m")
    r.check(
        "generate bare matches warm-up shape",
        set(gen.keys()) == {"model", "prompt", "stream"} and gen["prompt"] == "",
        str(gen),
    )
    gen2 = build_generate_body("m", options={"num_ctx": 4096}, keep_alive=0)
    r.check("generate options nested", gen2.get("options") == {"num_ctx": 4096})
    r.check("generate keep_alive top-level", gen2.get("keep_alive") == 0)


def test_stream_on_done_and_cancel(r: Results) -> None:
    print("\n[3] Stream yields strings; on_done once; cancel silent", flush=True)

    stub = CapturingStub()
    stub.start()
    client = OllamaClient(base_url=stub.base_url, timeout=5.0)
    done_chunks: list[dict] = []

    pieces = list(
        client.chat_stream(
            "m",
            [{"role": "user", "content": "x"}],
            options={"num_ctx": 2048},
            keep_alive="10m",
            think=False,
            on_done=done_chunks.append,
        )
    )
    r.check("content still arrives as strings", pieces == ["hi"], str(pieces))
    r.check("on_done fires exactly once", len(done_chunks) == 1, str(len(done_chunks)))
    r.check("on_done receives done chunk", done_chunks[0].get("done") is True)
    stub.close()

    body = json.loads(stub.request_body.decode("utf-8"))
    r.check("live request options nested", body.get("options") == {"num_ctx": 2048})
    r.check("live keep_alive top-level", body.get("keep_alive") == "10m")
    r.check("live think top-level", body.get("think") is False)

    # Bare body over the wire
    stub2 = CapturingStub(
        chunks=[
            {"message": {"content": "a"}, "done": False},
            {"message": {"content": ""}, "done": True, "eval_count": 1},
        ]
    )
    stub2.start()
    client2 = OllamaClient(base_url=stub2.base_url, timeout=5.0)
    list(client2.chat_stream("m", []))
    bare_body = json.loads(stub2.request_body.decode("utf-8"))
    r.check(
        "empty profile wire body is legacy-shaped",
        set(bare_body.keys()) == {"model", "messages", "stream"},
        str(bare_body.keys()),
    )
    stub2.close()

    # Cancel: no on_done
    hang = HangStub()
    hang.start()
    client3 = OllamaClient(base_url=hang.base_url)
    cancel = threading.Event()
    done3: list[dict] = []
    err3: Exception | None = None
    got3: list[str] = []

    def work() -> None:
        nonlocal err3
        try:
            for p in client3.chat_stream(
                "m", [], cancel_event=cancel, on_done=done3.append
            ):
                got3.append(p)
        except Exception as exc:  # noqa: BLE001
            err3 = exc

    t = threading.Thread(target=work, daemon=True)
    t.start()
    hang.accepted.wait(timeout=5)
    time.sleep(0.25)
    cancel.set()
    t.join(timeout=5)
    r.check("cancel does not raise", err3 is None, repr(err3))
    r.check("cancel received pre-stop content", got3 == ["x"], str(got3))
    r.check("no on_done after cancel without done event", done3 == [], str(done3))
    hang.close()


def test_metrics_safe(r: Results) -> None:
    print("\n[4] Metrics calculation safe with missing/zero", flush=True)
    empty = metrics_from_done_chunk({})
    r.check("empty chunk rates are None", empty["generation_tokens_per_sec"] is None)
    r.check("empty peak is None", empty["peak_context_tokens"] is None)

    zero = metrics_from_done_chunk(
        {"eval_count": 10, "eval_duration": 0, "prompt_eval_count": 0, "prompt_eval_duration": 1}
    )
    r.check("zero duration yields None gen rate", zero["generation_tokens_per_sec"] is None)

    good = metrics_from_done_chunk(
        {
            "eval_count": 10,
            "eval_duration": 500_000_000,
            "prompt_eval_count": 20,
            "prompt_eval_duration": 1_000_000_000,
        }
    )
    r.check(
        "gen tps ~20",
        good["generation_tokens_per_sec"] is not None
        and abs(good["generation_tokens_per_sec"] - 20.0) < 0.01,
        str(good["generation_tokens_per_sec"]),
    )
    r.check(
        "prompt tps ~20",
        good["prompt_tokens_per_sec"] is not None
        and abs(good["prompt_tokens_per_sec"] - 20.0) < 0.01,
        str(good["prompt_tokens_per_sec"]),
    )
    r.check("peak context is sum", good["peak_context_tokens"] == 30)
    r.check("None chunk is safe", metrics_from_done_chunk(None)["eval_count"] is None)


def test_profile_digest_policy(r: Results, tmp: Path) -> None:
    print("\n[5] Name prefs + digest observation invalidation", flush=True)
    path = tmp / "profiles.json"
    svc = ModelProfileService(settings_dir=tmp, settings_path=path)

    svc.set_preferences(
        "qwen3:8b",
        options={"num_ctx": 8192, "temperature": 0.4},
        keep_alive="5m",
        context_tier="8k",
        response_style="precise",
    )
    svc.ensure_digest("qwen3:8b", "sha256:aaa")
    svc.record_metrics(
        "qwen3:8b",
        {"eval_count": 8, "eval_duration": 400_000_000, "done": True},
        digest="sha256:aaa",
    )
    prof = svc.get_profile("qwen3:8b")
    r.check("prefs stored by name", prof.get("options", {}).get("num_ctx") == 8192)
    r.check(
        "metrics under observations",
        isinstance(prof.get("observations"), dict)
        and isinstance(prof["observations"].get("last_metrics"), dict),
    )
    r.check(
        "last metrics gen rate present",
        prof["observations"]["last_metrics"].get("generation_tokens_per_sec") is not None,
    )

    # Digest change
    svc.ensure_digest("qwen3:8b", "sha256:bbb")
    prof2 = svc.get_profile("qwen3:8b")
    r.check("context prefs retained after digest change", prof2.get("options", {}).get("num_ctx") == 8192)
    r.check("temperature retained", prof2.get("options", {}).get("temperature") == 0.4)
    r.check("keep_alive retained", prof2.get("keep_alive") == "5m")
    r.check("context_tier retained", prof2.get("context_tier") == "8k")
    r.check("response_style retained", prof2.get("response_style") == "precise")
    obs = prof2.get("observations") or {}
    r.check("stale last_metrics cleared", "last_metrics" not in obs, str(obs))
    r.check("new digest recorded", obs.get("digest") == "sha256:bbb")
    r.check("last_seen_digest updated", prof2.get("last_seen_digest") == "sha256:bbb")

    params = svc.request_params("qwen3:8b")
    r.check("request_params carries options", params.options == {"num_ctx": 8192, "temperature": 0.4})
    r.check("request_params keep_alive", params.keep_alive == "5m")
    empty = svc.request_params("never-configured:7b")
    r.check("unknown model empty params", empty.is_empty())


def test_descriptor_normalization(r: Results) -> None:
    print("\n[6] Metadata normalization helpers", flush=True)
    tags = descriptor_from_tags_entry(
        {
            "name": "ornith:9b",
            "digest": "sha256:abc",
            "size": 5600000000,
            "details": {
                "parameter_size": "9B",
                "quantization_level": "Q4_K_M",
                "family": "llama",
            },
            "modified_at": "2026-01-01T00:00:00Z",
        }
    )
    r.check("tags descriptor name", tags is not None and tags.name == "ornith:9b")
    r.check("tags digest", tags.digest == "sha256:abc")
    r.check("tags quant", tags.quantization == "Q4_K_M")

    show = descriptor_from_show(
        {
            "model": "ornith:9b",
            "details": {
                "parameter_size": "9B",
                "quantization_level": "Q4_K_M",
                "family": "llama",
            },
            "model_info": {"llama.context_length": 32768},
            "capabilities": ["completion"],
        },
        name_fallback="ornith:9b",
    )
    r.check("show context_length from model_info", show.context_length == 32768)
    r.check("show capabilities", "completion" in show.capabilities)


def test_connect_timeout_not_on_stream(r: Results) -> None:
    print("\n[7] Connection timeout is client non-stream only", flush=True)
    client = OllamaClient(base_url="http://127.0.0.1:9", timeout=0.05)
    r.check("client stores connect timeout", client.timeout == 0.05)
    # Stream path: hang stub — should not fail from urlopen timeout attribute
    hang = HangStub()
    hang.start()
    client2 = OllamaClient(base_url=hang.base_url, timeout=0.01)
    cancel = threading.Event()
    err: Exception | None = None
    start = time.time()

    def work() -> None:
        nonlocal err
        try:
            for _ in client2.chat_stream("m", [], cancel_event=cancel):
                pass
        except Exception as exc:  # noqa: BLE001
            err = exc

    t = threading.Thread(target=work, daemon=True)
    t.start()
    hang.accepted.wait(timeout=5)
    time.sleep(0.3)
    # Still streaming after many multiples of connect timeout
    still_alive = t.is_alive()
    cancel.set()
    t.join(timeout=5)
    elapsed = time.time() - start
    r.check(
        "stream survived beyond connect timeout",
        still_alive and elapsed >= 0.25,
        f"alive={still_alive} elapsed={elapsed:.2f} err={err!r}",
    )
    r.check("stream cancel clean", err is None, repr(err))
    hang.close()


def test_warm_and_chat_same_params(r: Results, tmp: Path) -> None:
    print("\n[8] Warm-up and chat receive same profile params", flush=True)
    path = tmp / "same_params.json"
    svc = ModelProfileService(settings_dir=tmp, settings_path=path)
    svc.set_preferences(
        "alpha:1",
        options={"num_ctx": 4096, "temperature": 0.1},
        keep_alive="2m",
        think=True,
    )
    params = svc.request_params("alpha:1")
    chat_body = build_chat_body(
        "alpha:1",
        [],
        options=params.options,
        keep_alive=params.keep_alive,
        think=params.think,
    )
    gen_body = build_generate_body(
        "alpha:1",
        options=params.options,
        keep_alive=params.keep_alive,
    )
    r.check("shared num_ctx on chat", chat_body["options"]["num_ctx"] == 4096)
    r.check("shared num_ctx on load", gen_body["options"]["num_ctx"] == 4096)
    r.check("shared keep_alive on both", chat_body["keep_alive"] == gen_body["keep_alive"] == "2m")
    r.check("think only on chat body", chat_body.get("think") is True and "think" not in gen_body)


def main() -> int:
    r = Results()
    with tempfile.TemporaryDirectory(prefix="cb-phase0-") as td:
        root = Path(td)
        s1 = root / "settings"
        s1.mkdir()
        test_settings_compat(r, s1)
        test_request_body_shapes(r)
        test_stream_on_done_and_cancel(r)
        test_metrics_safe(r)
        p1 = root / "prof"
        p1.mkdir()
        test_profile_digest_policy(r, p1)
        test_descriptor_normalization(r)
        test_connect_timeout_not_on_stream(r)
        same = root / "same"
        same.mkdir()
        test_warm_and_chat_same_params(r, same)

    print(
        f"\nPhase 0 results: {len(r.ok)} passed, {len(r.fail)} failed",
        flush=True,
    )
    if r.fail:
        print("FAILED:", ", ".join(r.fail), flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
