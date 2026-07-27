#!/usr/bin/env python3
"""Regression coverage for interruptible chat_stream cancellation.

Uses a local stub HTTP server (real sockets, no mocking of http.client)
so the tests exercise the actual cancellation mechanism: a per-stream
threading.Event plus a watcher thread that shuts down the live socket,
rather than a polling timeout.

Covers:
  1. stalled-open response + cancellation: returns fast, no OllamaError
  2. long legitimate pause + resumed output: stream stays connected
  3. normal completion: NDJSON parsing/behavior unchanged
  4. remote close/error without cancellation: raises OllamaError
  5. repeated cancel cycles: no surviving worker/watcher threads
"""

from __future__ import annotations

import json
import socket
import struct
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ollama_client import OllamaClient, OllamaError  # noqa: E402


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


class StubServer:
    """A minimal, single-connection stub /api/chat endpoint.

    accept -> read request -> send chunked NDJSON headers -> send
    `chunks`, one at a time -> then either pause forever, pause then
    resume with more chunks, or abruptly close, depending on the test.
    """

    def __init__(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self.conn: socket.socket | None = None
        self.accepted = threading.Event()

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def _accept_and_read_request(self) -> None:
        conn, _ = self.sock.accept()
        self.conn = conn
        conn.settimeout(5)
        buf = b""
        while b"\r\n\r\n" not in buf:
            data = conn.recv(4096)
            if not data:
                break
            buf += data
        # Drain any Content-Length body (best-effort, headers only matter)
        conn.settimeout(0.2)
        try:
            while conn.recv(4096):
                pass
        except OSError:
            pass
        conn.settimeout(None)
        self.accepted.set()

    def _send_headers(self) -> None:
        self.conn.sendall(
            b"HTTP/1.1 200 OK\r\n"
            b"Content-Type: application/x-ndjson\r\n"
            b"Transfer-Encoding: chunked\r\n"
            b"Connection: keep-alive\r\n"
            b"\r\n"
        )

    def _send_chunk(self, obj: dict) -> None:
        payload = (json.dumps(obj) + "\n").encode("utf-8")
        self.conn.sendall(f"{len(payload):x}\r\n".encode() + payload + b"\r\n")

    def _end_chunked(self) -> None:
        self.conn.sendall(b"0\r\n\r\n")

    def serve_delay_then_hang(self, delay_before_headers: float) -> None:
        """Accept and read the request, but send nothing at all — not even
        headers — for `delay_before_headers` seconds, then hang forever.
        Used to test cancellation while blocked in getresponse()."""

        def run() -> None:
            try:
                self._accept_and_read_request()
                time.sleep(delay_before_headers)
                self._send_headers()
                while True:
                    data = self.conn.recv(4096)
                    if not data:
                        break
            except OSError:
                pass  # client cancelled/closed before we finished sleeping

        threading.Thread(target=run, daemon=True).start()

    def serve_graceful_close_no_done(self, contents: list[str]) -> None:
        """Send `contents`, then close the connection gracefully (no RST)
        without ever sending a done:true chunk — a truncated response that
        looks, at the socket level, just like our own cancel shutdown."""

        def run() -> None:
            self._accept_and_read_request()
            self._send_headers()
            for text in contents:
                self._send_chunk({"message": {"content": text}, "done": False})
            self.conn.close()

        threading.Thread(target=run, daemon=True).start()

    def serve_http_error(self, status: int, error_body: dict) -> None:
        """Return a non-2xx status with an Ollama-style JSON error body,
        no chunked streaming at all."""

        def run() -> None:
            self._accept_and_read_request()
            payload = json.dumps(error_body).encode("utf-8")
            reason = {500: "Internal Server Error", 404: "Not Found"}.get(status, "Error")
            self.conn.sendall(
                f"HTTP/1.1 {status} {reason}\r\n".encode()
                + b"Content-Type: application/json\r\n"
                + f"Content-Length: {len(payload)}\r\n".encode()
                + b"Connection: close\r\n\r\n"
                + payload
            )
            self.conn.close()

        threading.Thread(target=run, daemon=True).start()

    def serve_then_hang(self, contents: list[str]) -> None:
        """Send `contents` as non-final chunks, then hold the connection
        open indefinitely, sending nothing more, until the peer closes it."""

        def run() -> None:
            try:
                self._accept_and_read_request()
                self._send_headers()
                for text in contents:
                    self._send_chunk({"message": {"content": text}, "done": False})
                while True:
                    data = self.conn.recv(4096)
                    if not data:
                        break
            except OSError:
                pass  # client cancelled/closed before or while we were sending

        threading.Thread(target=run, daemon=True).start()

    def serve_pause_then_resume(
        self, contents: list[str], *, pause_seconds: float, resume_text: str
    ) -> None:
        def run() -> None:
            self._accept_and_read_request()
            self._send_headers()
            for text in contents:
                self._send_chunk({"message": {"content": text}, "done": False})
            time.sleep(pause_seconds)
            self._send_chunk({"message": {"content": resume_text}, "done": True})
            self._end_chunked()

        threading.Thread(target=run, daemon=True).start()

    def serve_normal(self, contents: list[str]) -> None:
        def run() -> None:
            self._accept_and_read_request()
            self._send_headers()
            for text in contents:
                self._send_chunk({"message": {"content": text}, "done": False})
            self._send_chunk({"message": {"content": ""}, "done": True})
            self._end_chunked()

        threading.Thread(target=run, daemon=True).start()

    def serve_then_abort(self, contents: list[str], *, delay: float = 0.3) -> None:
        """Send some chunks, then kill the connection with an RST (no
        graceful close) before `done`, simulating a real failure."""

        def run() -> None:
            self._accept_and_read_request()
            self._send_headers()
            for text in contents:
                self._send_chunk({"message": {"content": text}, "done": False})
            time.sleep(delay)
            self.conn.setsockopt(
                socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0)
            )
            self.conn.close()

        threading.Thread(target=run, daemon=True).start()

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass
        if self.conn is not None:
            try:
                self.conn.close()
            except OSError:
                pass


def active_thread_names() -> set[str]:
    return {t.name for t in threading.enumerate() if t.is_alive()}


def main() -> int:
    results = Results()

    # === [1] Stalled-open response + cancellation ===
    print("\n[1] Stalled-open response: Stop returns fast, no error", flush=True)
    srv = StubServer()
    srv.serve_then_hang(["hello "])
    client = OllamaClient(base_url=srv.base_url)
    cancel = threading.Event()
    collected: list[str] = []
    err: Exception | None = None

    def run_stream() -> None:
        nonlocal err
        try:
            for piece in client.chat_stream("m", [], cancel_event=cancel):
                collected.append(piece)
        except Exception as exc:  # noqa: BLE001
            err = exc

    t = threading.Thread(target=run_stream, daemon=True)
    t.start()
    srv.accepted.wait(timeout=5)
    time.sleep(0.3)  # let the first chunk arrive and the loop settle mid-block
    start = time.time()
    cancel.set()
    t.join(timeout=5)
    elapsed = time.time() - start
    results.check("chat_stream returns within ~1s of cancel", elapsed < 2.0, f"{elapsed:.2f}s")
    results.check("worker thread actually finished", not t.is_alive())
    results.check("content received before Stop was yielded", collected == ["hello "], str(collected))
    results.check("cancellation does not raise OllamaError", err is None, repr(err))
    srv.close()

    # === [1b] Cancel before response headers ever arrive ===
    print("\n[1b] Cancel while blocked before headers arrive", flush=True)
    srv1b = StubServer()
    srv1b.serve_delay_then_hang(delay_before_headers=2.0)
    client1b = OllamaClient(base_url=srv1b.base_url)
    cancel1b = threading.Event()
    got1b: list[str] = []
    err1b: Exception | None = None

    def run_stream_1b() -> None:
        nonlocal err1b
        try:
            for piece in client1b.chat_stream("m", [], cancel_event=cancel1b):
                got1b.append(piece)
        except Exception as exc:  # noqa: BLE001
            err1b = exc

    t1b = threading.Thread(target=run_stream_1b, daemon=True)
    t1b.start()
    srv1b.accepted.wait(timeout=5)
    time.sleep(0.3)  # still blocked in getresponse(); no headers sent yet
    start1b = time.time()
    cancel1b.set()
    t1b.join(timeout=5)
    elapsed1b = time.time() - start1b
    results.check("returns fast while blocked before headers", elapsed1b < 2.0, f"{elapsed1b:.2f}s")
    results.check("no error when cancelled before headers", err1b is None, repr(err1b))
    results.check("no content yielded", got1b == [], str(got1b))
    srv1b.close()

    # === [2] Long legitimate pause, then resume ===
    print("\n[2] Long pause then resume: stays connected, completes", flush=True)
    srv2 = StubServer()
    srv2.serve_pause_then_resume(["part-one "], pause_seconds=2.0, resume_text="part-two")
    client2 = OllamaClient(base_url=srv2.base_url)
    cancel2 = threading.Event()
    start2 = time.time()
    pieces = list(client2.chat_stream("m", [], cancel_event=cancel2))
    elapsed2 = time.time() - start2
    results.check(
        "full content received across the pause",
        pieces == ["part-one ", "part-two"],
        str(pieces),
    )
    results.check("actually waited out the pause (>= ~2s)", elapsed2 >= 1.8, f"{elapsed2:.2f}s")
    srv2.close()

    # === [3] Normal completion, no pauses ===
    print("\n[3] Normal completion unchanged", flush=True)
    srv3 = StubServer()
    srv3.serve_normal(["a", "b", "c"])
    client3 = OllamaClient(base_url=srv3.base_url)
    pieces3 = list(client3.chat_stream("m", []))
    results.check("all chunks received in order", pieces3 == ["a", "b", "c"], str(pieces3))
    srv3.close()

    # === [4] Abrupt remote reset (RST) without cancellation raises OllamaError ===
    print("\n[4] Abrupt reset (no cancel) raises OllamaError", flush=True)
    srv4 = StubServer()
    srv4.serve_then_abort(["only-part "], delay=0.3)
    client4 = OllamaClient(base_url=srv4.base_url)
    raised: Exception | None = None
    got: list[str] = []
    try:
        for piece in client4.chat_stream("m", []):
            got.append(piece)
    except Exception as exc:  # noqa: BLE001
        raised = exc
    results.check("raises OllamaError", isinstance(raised, OllamaError), repr(raised))
    results.check("got the partial content before the drop", got == ["only-part "], str(got))
    srv4.close()

    # === [4b] Graceful close, no done:true, without cancellation ===
    print("\n[4b] Graceful premature close (no done:true) raises OllamaError", flush=True)
    srv4b = StubServer()
    srv4b.serve_graceful_close_no_done(["partial-answer "])
    client4b = OllamaClient(base_url=srv4b.base_url)
    raised4b: Exception | None = None
    got4b: list[str] = []
    try:
        for piece in client4b.chat_stream("m", []):
            got4b.append(piece)
    except Exception as exc:  # noqa: BLE001
        raised4b = exc
    results.check(
        "graceful premature EOF still raises OllamaError (not silently accepted)",
        isinstance(raised4b, OllamaError),
        repr(raised4b),
    )
    results.check("got the partial content before the drop", got4b == ["partial-answer "], str(got4b))
    srv4b.close()

    # === [4c] HTTP non-2xx with Ollama JSON error body ===
    print("\n[4c] HTTP error response preserves Ollama's JSON error detail", flush=True)
    srv4c = StubServer()
    srv4c.serve_http_error(500, {"error": "model runner crashed"})
    client4c = OllamaClient(base_url=srv4c.base_url)
    raised4c: Exception | None = None
    try:
        list(client4c.chat_stream("m", []))
    except Exception as exc:  # noqa: BLE001
        raised4c = exc
    results.check(
        "raises OllamaError with Ollama's error detail (not a generic status)",
        isinstance(raised4c, OllamaError) and str(raised4c) == "model runner crashed",
        repr(raised4c),
    )
    srv4c.close()

    # === [5] Repeated cancel cycles leave no surviving named watcher threads ===
    print("\n[5] Repeated cancel cycles: no thread leak", flush=True)
    before = len(threading.enumerate())
    for i in range(5):
        srv5 = StubServer()
        srv5.serve_then_hang([f"cycle-{i} "])
        client5 = OllamaClient(base_url=srv5.base_url)
        cancel5 = threading.Event()
        got5: list[str] = []

        def run5() -> None:
            for piece in client5.chat_stream("m", [], cancel_event=cancel5):
                got5.append(piece)

        th = threading.Thread(target=run5, daemon=True)
        th.start()
        srv5.accepted.wait(timeout=5)
        time.sleep(0.15)
        cancel5.set()
        th.join(timeout=5)
        srv5.close()
        time.sleep(0.05)  # let the watcher's daemon thread fully unwind
        surviving = [
            n
            for n in active_thread_names()
            if n == "ollama-chat-stream-watcher"
        ]
        results.check(
            f"no surviving named watcher thread after cycle {i}",
            not surviving,
            str(surviving),
        )
    after = len(threading.enumerate())
    results.check(
        "no accumulated worker/watcher threads after 5 cancel cycles",
        after <= before,
        f"before={before} after={after}",
    )

    print("\n=== Summary ===", flush=True)
    print(f"Passed: {len(results.ok)}  Failed: {len(results.fail)}", flush=True)
    for f in results.fail:
        print(f"  - {f}", flush=True)
    return 1 if results.fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
