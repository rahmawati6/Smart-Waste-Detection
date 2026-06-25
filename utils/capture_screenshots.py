from __future__ import annotations

import base64
import json
import os
import shutil
import socket
import subprocess
import time
import uuid
from pathlib import Path
from urllib import error, parse, request


ROOT = Path(__file__).resolve().parents[1]
SCREENSHOT_DIR = ROOT / "docs" / "screenshots"
BASE_URL = os.environ.get("ECOLENS_SCREENSHOT_URL", "http://127.0.0.1:5000")
USERNAME = os.environ.get("ECOLENS_SCREENSHOT_USERNAME", "admin")
PASSWORD = os.environ.get("ECOLENS_SCREENSHOT_PASSWORD", "ecolens123")
PORT = int(os.environ.get("ECOLENS_CHROME_DEBUG_PORT", "9222"))

PAGES = {
    "dashboard": "/dashboard",
    "analysis": "/analysis",
    "upload": "/upload",
    "camera": "/camera",
    "dataset": "/dataset",
    "history": "/history",
    "report": "/report",
    "about": "/about",
}


def find_chrome() -> str:
    candidates = [
        os.environ.get("CHROME_PATH"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    for command in ("chrome", "msedge", "chromium"):
        found = shutil.which(command)
        if found:
            return found
    raise RuntimeError("Chrome/Edge tidak ditemukan. Set CHROME_PATH ke lokasi browser.")


def http_json(url: str) -> dict:
    with request.urlopen(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


class NoRedirectHandler(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: N802 - stdlib hook
        return None


def fetch_session_cookie() -> str:
    opener = request.build_opener(NoRedirectHandler)
    payload = parse.urlencode({"username": USERNAME, "password": PASSWORD}).encode("utf-8")
    req = request.Request(
        f"{BASE_URL}/login",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        response = opener.open(req, timeout=10)
        headers = response.headers
    except error.HTTPError as exc:
        headers = exc.headers
        if exc.code != 302:
            raise RuntimeError(f"Login gagal dengan status HTTP {exc.code}") from exc
    cookie_header = headers.get("Set-Cookie") or ""
    for part in cookie_header.split(";"):
        part = part.strip()
        if part.startswith("session="):
            return part.split("=", 1)[1]
    raise RuntimeError("Respons login tidak mengirim cookie session.")


class CDPWebSocket:
    def __init__(self, websocket_url: str):
        if not websocket_url.startswith("ws://"):
            raise ValueError("Only ws:// websocket URLs are supported.")
        rest = websocket_url[len("ws://") :]
        host_port, path = rest.split("/", 1)
        host, port = host_port.split(":")
        self.host = host
        self.port = int(port)
        self.path = "/" + path
        self.sock = socket.create_connection((self.host, self.port), timeout=10)
        self.sock.settimeout(60)
        self.next_id = 0
        self._handshake()

    def _handshake(self) -> None:
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request_text = (
            f"GET {self.path} HTTP/1.1\r\n"
            f"Host: {self.host}:{self.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(request_text.encode("ascii"))
        response = self.sock.recv(4096)
        if b"101" not in response.split(b"\r\n", 1)[0]:
            raise RuntimeError("WebSocket handshake gagal.")

    def _send_frame(self, payload: str) -> None:
        data = payload.encode("utf-8")
        header = bytearray([0x81])
        length = len(data)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.extend([0x80 | 126, (length >> 8) & 255, length & 255])
        else:
            header.append(0x80 | 127)
            header.extend(length.to_bytes(8, "big"))
        mask = os.urandom(4)
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(data))
        self.sock.sendall(bytes(header) + mask + masked)

    def _recv_exact(self, size: int) -> bytes:
        chunks = bytearray()
        while len(chunks) < size:
            chunk = self.sock.recv(size - len(chunks))
            if not chunk:
                raise RuntimeError("WebSocket connection closed.")
            chunks.extend(chunk)
        return bytes(chunks)

    def _recv_frame(self) -> dict:
        first, second = self._recv_exact(2)
        opcode = first & 0x0F
        masked = bool(second & 0x80)
        length = second & 0x7F
        if length == 126:
            length = int.from_bytes(self._recv_exact(2), "big")
        elif length == 127:
            length = int.from_bytes(self._recv_exact(8), "big")
        mask = self._recv_exact(4) if masked else b""
        payload = bytearray(self._recv_exact(length))
        if masked:
            payload = bytearray(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        if opcode == 8:
            raise RuntimeError("WebSocket closed by browser.")
        if opcode == 9:
            return self._recv_frame()
        return json.loads(payload.decode("utf-8"))

    def command(self, method: str, params: dict | None = None, timeout: float = 20) -> dict:
        self.next_id += 1
        command_id = self.next_id
        self._send_frame(json.dumps({"id": command_id, "method": method, "params": params or {}}))
        deadline = time.time() + timeout
        while time.time() < deadline:
            message = self._recv_frame()
            if message.get("id") == command_id:
                if "error" in message:
                    raise RuntimeError(f"CDP error {method}: {message['error']}")
                return message.get("result", {})
        raise TimeoutError(f"Timeout waiting for {method}")


def wait_for_debug_port() -> None:
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            http_json(f"http://127.0.0.1:{PORT}/json/version")
            return
        except Exception:
            time.sleep(0.3)
    raise TimeoutError("Chrome debug port tidak siap.")


def wait_ready(cdp: CDPWebSocket, pause: float = 1.0) -> None:
    time.sleep(pause)
    deadline = time.time() + 20
    while time.time() < deadline:
        state = cdp.command("Runtime.evaluate", {"expression": "document.readyState", "returnByValue": True})
        if state.get("result", {}).get("value") == "complete":
            time.sleep(0.6)
            return
        time.sleep(0.25)
    raise TimeoutError("Halaman belum selesai dimuat.")


def navigate(cdp: CDPWebSocket, path: str) -> None:
    cdp.command("Page.navigate", {"url": f"{BASE_URL}{path}"})
    wait_ready(cdp)


def chrome_screenshot(chrome: str, profile_dir: Path, path: str, output: Path) -> None:
    command = [
        chrome,
        "--headless=new",
        f"--user-data-dir={profile_dir}",
        "--window-size=1440,1000",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        f"--screenshot={output}",
        f"{BASE_URL}{path}",
    ]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)


def main() -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    profile_dir = ROOT / ".cache" / f"chrome-screenshots-{uuid.uuid4().hex[:8]}"
    public_profile_dir = ROOT / ".cache" / f"chrome-screenshots-public-{uuid.uuid4().hex[:8]}"
    chrome = find_chrome()
    session_cookie = fetch_session_cookie()
    chrome_screenshot(chrome, public_profile_dir, "/login", SCREENSHOT_DIR / "login.png")

    process = subprocess.Popen(
        [
            chrome,
            "--headless=new",
            f"--remote-debugging-port={PORT}",
            f"--user-data-dir={profile_dir}",
            "--window-size=1440,1000",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        wait_for_debug_port()
        tabs = http_json(f"http://127.0.0.1:{PORT}/json")
        cdp = CDPWebSocket(tabs[0]["webSocketDebuggerUrl"])
        cdp.command("Page.enable")
        cdp.command("Runtime.enable")
        cdp.command("Network.enable")
        cdp.command(
            "Emulation.setDeviceMetricsOverride",
            {"width": 1440, "height": 1000, "deviceScaleFactor": 1, "mobile": False},
        )

        cdp.command(
            "Network.setCookie",
            {
                "name": "session",
                "value": session_cookie,
                "url": BASE_URL,
                "expires": int(time.time()) + 24 * 60 * 60,
                "httpOnly": True,
                "sameSite": "Lax",
            },
        )
    finally:
        try:
            cdp.command("Browser.close", timeout=5)
        except Exception:
            process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()

    for name, path in PAGES.items():
        chrome_screenshot(chrome, profile_dir, path, SCREENSHOT_DIR / f"{name}.png")
        print(f"captured {name}: {SCREENSHOT_DIR / (name + '.png')}")


if __name__ == "__main__":
    main()
