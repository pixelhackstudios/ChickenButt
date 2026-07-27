"""Minimal Ollama HTTP client with chat streaming."""

from __future__ import annotations

import http.client
import json
import socket
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator
from typing import Any


class OllamaError(Exception):
    pass


class OllamaClient:
    def __init__(self, base_url: str = "http://127.0.0.1:11434", timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        stream: bool = False,
    ):
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            return urllib.request.urlopen(req, timeout=None if stream else self.timeout)
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                raw = exc.read().decode("utf-8", errors="replace")
                try:
                    payload = json.loads(raw)
                    detail = str(payload.get("error") or raw).strip()
                except json.JSONDecodeError:
                    detail = raw.strip()
            except Exception:  # noqa: BLE001
                detail = ""
            if detail:
                raise OllamaError(detail) from exc
            raise OllamaError(f"Ollama HTTP {exc.code} for {path}") from exc
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", None) or str(exc)
            raise OllamaError(f"Cannot reach Ollama at {self.base_url}: {reason}") from exc

    def list_models(self) -> list[str]:
        with self._request("GET", "/api/tags") as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        models = payload.get("models") or []
        names = [m.get("name", "") for m in models if m.get("name")]
        return sorted(names, key=str.lower)

    def list_running_models(self) -> list[str]:
        """Names currently loaded in memory (from /api/ps)."""
        try:
            with self._request("GET", "/api/ps") as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except OllamaError:
            return []
        models = payload.get("models") or []
        names: list[str] = []
        for m in models:
            name = m.get("name") or m.get("model") or ""
            if name:
                names.append(name)
        return names

    def is_model_loaded(self, model: str) -> bool:
        if not model:
            return False
        running = self.list_running_models()
        if model in running:
            return True
        # Tags may include :latest; match prefix / without tag
        base = model.split(":")[0]
        for name in running:
            if name == model or name.split(":")[0] == base or name.startswith(model):
                return True
        return False

    def load_model(
        self,
        model: str,
        *,
        should_stop: Callable[[], bool] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Warm a model into memory via /api/generate (empty prompt).

        Yields NDJSON chunks so the UI can show status / byte progress when
        Ollama provides them (pull-style completed/total, or status strings).
        """
        if not model:
            raise OllamaError("No model selected")
        body = {
            "model": model,
            "prompt": "",
            "stream": True,
        }
        with self._request("POST", "/api/generate", body=body, stream=True) as resp:
            while True:
                if should_stop and should_stop():
                    break
                line = resp.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    continue
                if err := chunk.get("error"):
                    raise OllamaError(str(err))
                yield chunk
                if chunk.get("done"):
                    break

    def chat_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        cancel_event: threading.Event | None = None,
    ) -> Iterator[str]:
        """Stream a chat completion.

        Uses http.client directly (rather than urlopen) so a cancellation
        can shut down the exact connection socket from another thread and
        wake a blocked readline() immediately, instead of waiting for the
        model to produce another token. Normal generation gets no socket
        timeout — a model that pauses for a long time is not an error.
        """
        parsed = urllib.parse.urlsplit(self.base_url)
        conn_cls = (
            http.client.HTTPSConnection
            if parsed.scheme == "https"
            else http.client.HTTPConnection
        )
        conn = conn_cls(parsed.hostname, parsed.port)
        body = json.dumps(
            {"model": model, "messages": messages, "stream": True}
        ).encode("utf-8")

        watcher: threading.Thread | None = None
        # Set once this call is done (normally, on error, or cancelled) so
        # the watcher — woken via cancel_event purely to release it — can
        # tell "actually cancelled" apart from "just cleaning up" and skip
        # the shutdown() in the latter case.
        stream_finished = threading.Event()

        def _watch(sock_holder: "list[socket.socket | None]") -> None:
            cancel_event.wait()
            if stream_finished.is_set():
                return
            sock = sock_holder[0]
            if sock is not None:
                try:
                    sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

        sock_holder: list[socket.socket | None] = [None]
        try:
            try:
                conn.putrequest("POST", "/api/chat")
                conn.putheader("Content-Type", "application/json")
                conn.putheader("Accept", "application/json")
                conn.putheader("Content-Length", str(len(body)))
                conn.endheaders(body)
                sock_holder[0] = conn.sock
                if cancel_event is not None:
                    watcher = threading.Thread(
                        target=_watch,
                        args=(sock_holder,),
                        daemon=True,
                        name="ollama-chat-stream-watcher",
                    )
                    watcher.start()
                resp = conn.getresponse()
            except OSError as exc:
                # A cancel_event.set() right after connect (before the
                # model produced even the response headers) also shows up
                # here as a socket error from the watcher's shutdown() —
                # that's a clean cancellation, not a connection failure.
                if cancel_event is not None and cancel_event.is_set():
                    return
                raise OllamaError(
                    f"Cannot reach Ollama at {self.base_url}: {exc}"
                ) from exc

            if resp.status >= 400:
                detail = resp.read().decode("utf-8", errors="replace")
                try:
                    payload = json.loads(detail)
                    detail = str(payload.get("error") or detail).strip()
                except json.JSONDecodeError:
                    detail = detail.strip()
                raise OllamaError(detail or f"Ollama HTTP {resp.status} for /api/chat")

            saw_done = False
            while True:
                if cancel_event is not None and cancel_event.is_set():
                    break
                try:
                    line = resp.readline()
                except OSError:
                    if cancel_event is not None and cancel_event.is_set():
                        break
                    raise OllamaError(
                        "Connection to Ollama was lost during streaming"
                    ) from None
                if not line:
                    if cancel_event is not None and cancel_event.is_set():
                        break
                    if saw_done:
                        break
                    # A graceful close (no RST) looks identical to our own
                    # cancellation shutdown at the socket level — this is
                    # only reached when cancel_event was never set, so it's
                    # Ollama ending the response early, not us.
                    raise OllamaError(
                        "Ollama closed the response before generation completed"
                    )
                line = line.strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    continue
                if err := chunk.get("error"):
                    raise OllamaError(str(err))
                msg = chunk.get("message") or {}
                content = msg.get("content") or ""
                if content:
                    yield content
                if chunk.get("done"):
                    saw_done = True
                    break
        finally:
            try:
                conn.close()
            except OSError:
                pass
            if cancel_event is not None:
                # Order matters: mark done before waking the watcher, so it
                # can tell "just cleaning up" apart from a real cancel that
                # raced in at the same moment.
                stream_finished.set()
                cancel_event.set()
                if watcher is not None:
                    watcher.join(timeout=2)

    def pull_model(
        self,
        model: str,
        *,
        should_stop: Callable[[], bool] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Download a model via POST /api/pull (stream=true).

        Yields NDJSON status objects, e.g.::
            {"status":"pulling manifest"}
            {"status":"downloading","digest":"...","total":N,"completed":M}
            {"status":"success"}
        """
        if not model or not str(model).strip():
            raise OllamaError("No model name for pull")
        body = {"name": str(model).strip(), "stream": True}
        # Pulls can take a long time — stream with no socket timeout.
        with self._request("POST", "/api/pull", body=body, stream=True) as resp:
            while True:
                if should_stop and should_stop():
                    break
                line = resp.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    continue
                if err := chunk.get("error"):
                    raise OllamaError(str(err))
                yield chunk
                # Ollama marks completion with status success or done flag
                status = (chunk.get("status") or "").lower()
                if status == "success" or chunk.get("done") is True:
                    break

    def format_list_models(self) -> str:
        """Human-readable installed model list (from /api/tags)."""
        with self._request("GET", "/api/tags") as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        models = payload.get("models") or []
        if not models:
            return "_No models installed._"
        lines = ["| Name | Size | Modified |", "| --- | --- | --- |"]
        for m in sorted(models, key=lambda x: (x.get("name") or "").lower()):
            name = m.get("name") or "?"
            size = m.get("size")
            size_s = _fmt_bytes(size) if isinstance(size, (int, float)) else "—"
            modified = m.get("modified_at") or m.get("modified") or "—"
            if isinstance(modified, str) and "T" in modified:
                modified = modified.split("T", 1)[0]
            lines.append(f"| `{name}` | {size_s} | {modified} |")
        return "\n".join(lines)

    def format_ps_models(self) -> str:
        """Human-readable loaded models (from /api/ps)."""
        with self._request("GET", "/api/ps") as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        models = payload.get("models") or []
        if not models:
            return "_No models currently loaded in memory._"
        lines = ["| Name | Size | VRAM |", "| --- | --- | --- |"]
        for m in models:
            name = m.get("name") or m.get("model") or "?"
            size = m.get("size")
            size_s = _fmt_bytes(size) if isinstance(size, (int, float)) else "—"
            vram = m.get("size_vram")
            vram_s = _fmt_bytes(vram) if isinstance(vram, (int, float)) else "—"
            lines.append(f"| `{name}` | {size_s} | {vram_s} |")
        return "\n".join(lines)


def _fmt_bytes(n: int | float) -> str:
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024.0:
            if unit == "B":
                return f"{int(n)} {unit}"
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"
