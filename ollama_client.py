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
from dataclasses import dataclass
from typing import Any


class OllamaError(Exception):
    pass


@dataclass(frozen=True)
class ModelDescriptor:
    """Normalized installed-model metadata (tags + show)."""

    name: str
    digest: str | None = None
    size: int | None = None
    parameter_size: str | None = None
    quantization: str | None = None
    family: str | None = None
    context_length: int | None = None
    capabilities: tuple[str, ...] = ()
    modified_at: str | None = None


@dataclass(frozen=True)
class RunningModelInfo:
    """Normalized loaded-model row from ``/api/ps``."""

    name: str
    model: str | None = None
    size: int | None = None
    size_vram: int | None = None
    context_length: int | None = None
    digest: str | None = None
    expires_at: str | None = None


def build_chat_body(
    model: str,
    messages: list[dict[str, str]],
    *,
    stream: bool = True,
    options: dict[str, Any] | None = None,
    keep_alive: Any = None,
    think: Any = None,
) -> dict[str, Any]:
    """Build a chat request body; omit unset optional fields."""
    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": stream,
    }
    if options:
        body["options"] = options
    if keep_alive is not None:
        body["keep_alive"] = keep_alive
    if think is not None:
        body["think"] = think
    return body


def build_generate_body(
    model: str,
    *,
    prompt: str = "",
    stream: bool = True,
    options: dict[str, Any] | None = None,
    keep_alive: Any = None,
) -> dict[str, Any]:
    """Build a generate/load request body; omit unset optional fields."""
    body: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "stream": stream,
    }
    if options:
        body["options"] = options
    if keep_alive is not None:
        body["keep_alive"] = keep_alive
    return body


def _context_length_from_model_info(model_info: Any) -> int | None:
    """Find architecture-specific ``*.context_length`` in show.model_info."""
    if not isinstance(model_info, dict):
        return None
    # Prefer exact suffix matches; take the first positive int.
    for key, value in model_info.items():
        if not isinstance(key, str):
            continue
        if key.endswith(".context_length") or key == "context_length":
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)) and int(value) > 0:
                return int(value)
    return None


def _capabilities_from_show(payload: dict[str, Any]) -> tuple[str, ...]:
    caps: list[str] = []
    raw = payload.get("capabilities")
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, str) and item.strip():
                caps.append(item.strip())
    # Older shapes: details / projector / etc.
    details = payload.get("details")
    if isinstance(details, dict):
        fam = details.get("family") or details.get("families")
        if isinstance(fam, str) and "vision" in fam.lower() and "vision" not in caps:
            caps.append("vision")
    return tuple(dict.fromkeys(caps))


def descriptor_from_tags_entry(entry: dict[str, Any]) -> ModelDescriptor | None:
    name = entry.get("name") or entry.get("model")
    if not isinstance(name, str) or not name.strip():
        return None
    details = entry.get("details") if isinstance(entry.get("details"), dict) else {}
    size = entry.get("size")
    size_i = int(size) if isinstance(size, (int, float)) and not isinstance(size, bool) else None
    digest = entry.get("digest")
    if digest is not None:
        digest = str(digest) if digest else None
    param = details.get("parameter_size") if details else entry.get("parameter_size")
    quant = details.get("quantization_level") if details else entry.get("quantization_level")
    family = details.get("family") if details else None
    if isinstance(family, list):
        family = family[0] if family else None
    modified = entry.get("modified_at") or entry.get("modified")
    return ModelDescriptor(
        name=name,
        digest=digest if isinstance(digest, str) else None,
        size=size_i,
        parameter_size=str(param) if param is not None else None,
        quantization=str(quant) if quant is not None else None,
        family=str(family) if family is not None else None,
        context_length=None,
        capabilities=(),
        modified_at=str(modified) if modified is not None else None,
    )


def descriptor_from_show(payload: dict[str, Any], *, name_fallback: str = "") -> ModelDescriptor:
    details = payload.get("details") if isinstance(payload.get("details"), dict) else {}
    name = payload.get("modelfile")  # not useful
    # Prefer explicit model field from show responses
    for key in ("model", "name"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            name = val
            break
    else:
        name = name_fallback or ""

    digest = payload.get("digest") or payload.get("model_info", {})
    dig: str | None = None
    if isinstance(payload.get("digest"), str):
        dig = payload["digest"]
    elif isinstance(payload.get("details"), dict) and isinstance(
        payload["details"].get("parent_model"), str
    ):
        pass

    # Ollama show may put digest only on tags; keep optional.
    if dig is None and isinstance(payload.get("model_info"), dict):
        # Some builds expose digest at top level only.
        pass

    size = payload.get("size")
    size_i = int(size) if isinstance(size, (int, float)) and not isinstance(size, bool) else None
    param = details.get("parameter_size")
    quant = details.get("quantization_level")
    family = details.get("family")
    if isinstance(family, list):
        family = family[0] if family else None

    ctx = _context_length_from_model_info(payload.get("model_info"))
    # Parameters block may also list num_ctx
    params = payload.get("parameters")
    if ctx is None and isinstance(params, str):
        for line in params.splitlines():
            line = line.strip()
            if line.startswith("num_ctx"):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        ctx = int(parts[-1])
                    except ValueError:
                        pass

    return ModelDescriptor(
        name=str(name) if name else name_fallback,
        digest=dig,
        size=size_i,
        parameter_size=str(param) if param is not None else None,
        quantization=str(quant) if quant is not None else None,
        family=str(family) if family is not None else None,
        context_length=ctx,
        capabilities=_capabilities_from_show(payload),
        modified_at=None,
    )


def running_from_ps_entry(entry: dict[str, Any]) -> RunningModelInfo | None:
    name = entry.get("name") or entry.get("model")
    if not isinstance(name, str) or not name.strip():
        return None
    size = entry.get("size")
    size_vram = entry.get("size_vram")
    ctx = entry.get("context_length") or entry.get("context")
    dig = entry.get("digest")
    return RunningModelInfo(
        name=name,
        model=str(entry["model"]) if isinstance(entry.get("model"), str) else None,
        size=int(size) if isinstance(size, (int, float)) and not isinstance(size, bool) else None,
        size_vram=(
            int(size_vram)
            if isinstance(size_vram, (int, float)) and not isinstance(size_vram, bool)
            else None
        ),
        context_length=(
            int(ctx) if isinstance(ctx, (int, float)) and not isinstance(ctx, bool) else None
        ),
        digest=str(dig) if isinstance(dig, str) else None,
        expires_at=str(entry["expires_at"]) if entry.get("expires_at") is not None else None,
    )


class OllamaClient:
    def __init__(self, base_url: str = "http://127.0.0.1:11434", timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        # Non-stream HTTP only. Chat streams intentionally use no socket timeout.
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

    def get_version(self) -> str:
        """Ollama server version string from ``GET /api/version``."""
        with self._request("GET", "/api/version") as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        version = payload.get("version")
        if isinstance(version, str) and version.strip():
            return version.strip()
        return str(payload) if payload else ""

    def list_models(self) -> list[str]:
        with self._request("GET", "/api/tags") as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        models = payload.get("models") or []
        names = [m.get("name", "") for m in models if m.get("name")]
        return sorted(names, key=str.lower)

    def list_models_detail(self) -> list[ModelDescriptor]:
        """Installed models from ``/api/tags`` as normalized descriptors."""
        with self._request("GET", "/api/tags") as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        models = payload.get("models") or []
        out: list[ModelDescriptor] = []
        for m in models:
            if not isinstance(m, dict):
                continue
            desc = descriptor_from_tags_entry(m)
            if desc is not None:
                out.append(desc)
        return sorted(out, key=lambda d: d.name.lower())

    def show_model(self, name: str) -> ModelDescriptor:
        """Model metadata from ``POST /api/show`` (normalized)."""
        if not name or not str(name).strip():
            raise OllamaError("No model name for show")
        body = {"name": str(name).strip()}
        with self._request("POST", "/api/show", body=body) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise OllamaError("Invalid show response")
        desc = descriptor_from_show(payload, name_fallback=str(name).strip())
        # Prefer the requested name if show omits it.
        if not desc.name:
            desc = ModelDescriptor(
                name=str(name).strip(),
                digest=desc.digest,
                size=desc.size,
                parameter_size=desc.parameter_size,
                quantization=desc.quantization,
                family=desc.family,
                context_length=desc.context_length,
                capabilities=desc.capabilities,
                modified_at=desc.modified_at,
            )
        return desc

    def list_running_models(self) -> list[str]:
        """Names currently loaded in memory (from /api/ps)."""
        return [m.name for m in self.list_running_models_detail()]

    def list_running_models_detail(self) -> list[RunningModelInfo]:
        """Loaded models from ``/api/ps`` as normalized rows."""
        try:
            with self._request("GET", "/api/ps") as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except OllamaError:
            return []
        models = payload.get("models") or []
        out: list[RunningModelInfo] = []
        for m in models:
            if not isinstance(m, dict):
                continue
            info = running_from_ps_entry(m)
            if info is not None:
                out.append(info)
        return out

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
        options: dict[str, Any] | None = None,
        keep_alive: Any = None,
    ) -> Iterator[dict[str, Any]]:
        """Warm a model into memory via /api/generate (empty prompt).

        Yields NDJSON chunks so the UI can show status / byte progress when
        Ollama provides them (pull-style completed/total, or status strings).
        Optional ``options`` / ``keep_alive`` are omitted when unset so warm-up
        matches Ollama defaults (and chat profile when both are wired).
        """
        if not model:
            raise OllamaError("No model selected")
        body = build_generate_body(
            model,
            prompt="",
            stream=True,
            options=options,
            keep_alive=keep_alive,
        )
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
        options: dict[str, Any] | None = None,
        keep_alive: Any = None,
        think: Any = None,
        on_done: Callable[[dict[str, Any]], None] | None = None,
    ) -> Iterator[str]:
        """Stream a chat completion.

        Uses http.client directly (rather than urlopen) so a cancellation
        can shut down the exact connection socket from another thread and
        wake a blocked readline() immediately, instead of waiting for the
        model to produce another token. Normal generation gets no socket
        timeout — a model that pauses for a long time is not an error.

        Content chunks still yield as strings. When a final ``done`` object
        arrives, ``on_done`` is invoked once with that object (if provided).
        Cancellation or connection loss without a ``done`` chunk does not
        call ``on_done``.
        """
        parsed = urllib.parse.urlsplit(self.base_url)
        conn_cls = (
            http.client.HTTPSConnection
            if parsed.scheme == "https"
            else http.client.HTTPConnection
        )
        conn = conn_cls(parsed.hostname, parsed.port)
        body = json.dumps(
            build_chat_body(
                model,
                messages,
                stream=True,
                options=options,
                keep_alive=keep_alive,
                think=think,
            )
        ).encode("utf-8")

        watcher: threading.Thread | None = None
        # Set once this call is done (normally, on error, or cancelled) so
        # the watcher — woken via cancel_event purely to release it — can
        # tell "actually cancelled" apart from "just cleaning up" and skip
        # the shutdown() in the latter case.
        stream_finished = threading.Event()
        done_notified = False

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
                    if on_done is not None and not done_notified:
                        done_notified = True
                        try:
                            on_done(chunk)
                        except Exception:  # noqa: BLE001
                            # Metrics must never break generation completion.
                            pass
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
