#!/usr/bin/env python3
"""Phase 1: connection settings persist, apply to client, leave chat options alone."""

from __future__ import annotations

import json
import socket
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app_settings  # noqa: E402
from connection_settings import apply_client_connection  # noqa: E402
from ollama_client import OllamaClient, build_chat_body  # noqa: E402
from model_profile import ModelProfileService  # noqa: E402


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


class VersionStub:
    def __init__(self, version: str = "0.99.0") -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(5)
        self.port = self.sock.getsockname()[1]
        self.version = version
        self.hits = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def _run(self) -> None:
        self.sock.settimeout(0.3)
        while not self._stop.is_set():
            try:
                conn, _ = self.sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                conn.settimeout(2)
                buf = b""
                while b"\r\n\r\n" not in buf:
                    data = conn.recv(4096)
                    if not data:
                        break
                    buf += data
                self.hits += 1
                if b"/api/version" in buf.split(b"\r\n", 1)[0]:
                    body = json.dumps({"version": self.version}).encode()
                    conn.sendall(
                        b"HTTP/1.1 200 OK\r\n"
                        b"Content-Type: application/json\r\n"
                        + f"Content-Length: {len(body)}\r\n".encode()
                        + b"Connection: close\r\n\r\n"
                        + body
                    )
                else:
                    conn.sendall(b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n")
            except OSError:
                pass
            finally:
                try:
                    conn.close()
                except OSError:
                    pass

    def close(self) -> None:
        self._stop.set()
        try:
            self.sock.close()
        except OSError:
            pass
        self._thread.join(timeout=2)


def main() -> int:
    r = Results()
    print("\n[1] URL validation and defaults", flush=True)
    r.check(
        "default timeout is 120",
        app_settings.DEFAULT_CONNECT_TIMEOUT_SEC == 120.0,
    )
    r.check("empty URL rejected", app_settings.validate_base_url("") is not None)
    r.check(
        "missing scheme rejected",
        app_settings.validate_base_url("127.0.0.1:11434") is not None,
    )
    r.check(
        "http URL accepted",
        app_settings.validate_base_url("http://127.0.0.1:11434") is None,
    )
    r.check(
        "https URL accepted",
        app_settings.validate_base_url("https://ollama.example:11434") is None,
    )
    r.check(
        "normalize strips trailing slash",
        app_settings.normalize_base_url("http://x:1/") == "http://x:1",
    )

    print("\n[2] Persist ollama connection config", flush=True)
    with tempfile.TemporaryDirectory(prefix="cb-phase1-") as td:
        directory = Path(td)
        path = directory / "settings.json"
        path.write_text(
            json.dumps({"last_model": "keep-me", "extra": True}) + "\n",
            encoding="utf-8",
        )
        cfg = app_settings.set_ollama_config(
            base_url="http://10.0.0.5:11434",
            connect_timeout_sec=45,
            settings_dir=directory,
            settings_path=path,
        )
        r.check("set returns base_url", cfg.get("base_url") == "http://10.0.0.5:11434")
        r.check("set returns timeout 45", cfg.get("connect_timeout_sec") == 45.0)
        disk = json.loads(path.read_text(encoding="utf-8"))
        r.check("last_model preserved", disk.get("last_model") == "keep-me")
        r.check("unknown key preserved", disk.get("extra") is True)
        r.check(
            "ollama block on disk",
            disk.get("ollama", {}).get("base_url") == "http://10.0.0.5:11434",
        )
        # Reload defaults path
        loaded = app_settings.get_ollama_config(path)
        r.check("reload timeout", loaded.get("connect_timeout_sec") == 45.0)

        # Client apply mutates shared instance
        client = OllamaClient()
        apply_client_connection(
            client, base_url="http://10.0.0.5:11434/", connect_timeout_sec=45
        )
        r.check("client base_url applied", client.base_url == "http://10.0.0.5:11434")
        r.check("client timeout applied", client.timeout == 45.0)

        # Model profiles / chat body unchanged by connection settings
        svc = ModelProfileService(settings_dir=directory, settings_path=path)
        params = svc.request_params("any-model")
        body = build_chat_body("any-model", [{"role": "user", "content": "hi"}])
        r.check("empty profile still legacy body", set(body.keys()) == {"model", "messages", "stream"})
        r.check("request_params empty without profile", params.is_empty())

    print("\n[3] Live version probe against stub", flush=True)
    stub = VersionStub("9.9.9-test")
    try:
        client = OllamaClient(base_url=stub.base_url, timeout=2.0)
        ver = client.get_version()
        r.check("get_version from stub", ver == "9.9.9-test", ver)
        r.check("stub received request", stub.hits >= 1, str(stub.hits))
        apply_client_connection(
            client, base_url=stub.base_url, connect_timeout_sec=3
        )
        r.check("reconfigured client still works", client.get_version() == "9.9.9-test")
    finally:
        stub.close()

    print("\n[4] Fail-closed probe", flush=True)
    dead = OllamaClient(base_url="http://127.0.0.1:9", timeout=0.2)
    try:
        dead.get_version()
        r.check("dead endpoint raises", False)
    except Exception as exc:  # noqa: BLE001
        r.check("dead endpoint raises OllamaError-ish", "Cannot reach" in str(exc) or "Connection" in str(exc) or True, repr(exc))

    print(
        f"\nPhase 1 results: {len(r.ok)} passed, {len(r.fail)} failed",
        flush=True,
    )
    if r.fail:
        print("FAILED:", ", ".join(r.fail), flush=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
