import socket
import threading
import datetime
import sys
import time

PROXY_HOST = "0.0.0.0"
PROXY_PORT = 8080
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8000
TIMEOUT_SEC = 10
BACKLOG = 20

#
# Cache Management
#
cache_store = {}
cache_lock = threading.Lock()


def cache_get(path: str):
    with cache_lock:
        return cache_store.get(path, None)


def cache_set(path: str, data: bytes):
    with cache_lock:
        cache_store[path] = data


def cache_info() -> str:
    with cache_lock:
        return f"Cache size: {len(cache_store)} entries, " \
               f"{sum(len(v) for v in cache_store.values())} bytes"


#
# Helpers
#
def log(tag: str, message: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    log_line = f"[{ts}] [{tag}] {message}"
    print(log_line, flush=True)
    
    # Also write to log file
    try:
        with open("proxy.log", "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
    except:
        pass


def error_response(code: int, text: str, detail: str = "") -> bytes:
    body = f"<html><body><h1>{code} {text}</h1><p>{detail}</p></body></html>".encode()
    headers = (
        f"HTTP/1.1 {code} {text}\r\n"
        f"Content-Type: text/html; charset=utf-8\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Connection: close\r\n"
        f"X-Proxy: SimpleProxy/1.0\r\n"
        f"\r\n"
    )
    return headers.encode() + body


def extract_path(raw: bytes) -> str:
    """Ambil path dari baris pertama HTTP request."""
    try:
        first_line = raw.split(b"\r\n")[0].decode("utf-8", errors="replace")
        parts = first_line.split(" ")
        if len(parts) >= 2:
            return parts[1]
    except Exception:
        pass
    return "/"


def extract_status_code(response: bytes) -> str:
    """Ambil status code dari response HTTP."""
    try:
        first_line = response.split(b"\r\n")[0].decode("utf-8", errors="replace")
        parts = first_line.split(" ")
        return parts[1] if len(parts) >= 2 else "???"
    except Exception:
        return "???"


def patch_response_header(response: bytes, extra_header: str) -> bytes:
    """Sisipkan header tambahan (X-Cache) ke response."""
    try:
        idx = response.index(b"\r\n\r\n")
        header_part = response[:idx]
        body_part = response[idx:]
        header_part += f"\r\n{extra_header}".encode()
        return header_part + body_part
    except Exception:
        return response


def forward_to_server(raw_request: bytes) -> bytes:
    """
    Buka koneksi TCP baru ke Web Server, kirim request, terima response penuh.
    Raise ConnectionError jika gagal / timeout.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(TIMEOUT_SEC)
    try:
        sock.connect((SERVER_HOST, SERVER_PORT))
        sock.sendall(raw_request)

        response = b""
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            response += chunk
        return response
    except socket.timeout:
        raise ConnectionError("Gateway Timeout: Web Server tidak merespons.")
    except ConnectionRefusedError:
        raise ConnectionError("Bad Gateway: Web Server menolak koneksi.")
    except Exception as e:
        raise ConnectionError(f"Bad Gateway: {e}")
    finally:
        sock.close()


#
# Client Handler
#
def handle_client(conn: socket.socket, addr):
    client_ip = addr[0]
    start_time = time.time()

    try:
        conn.settimeout(15)
        raw = b""
        while b"\r\n\r\n" not in raw:
            chunk = conn.recv(4096)
            if not chunk:
                break
            raw += chunk

        if not raw:
            return

        path = extract_path(raw)

        cached = cache_get(path)
        if cached is not None:
            response = patch_response_header(cached, "X-Cache: HIT")
            conn.sendall(response)
            elapsed = (time.time() - start_time) * 1000
            log("PROXY", f"[HIT ] {client_ip} GET {path} | "
                         f"status={extract_status_code(cached)} | "
                         f"size={len(cached)}B | {elapsed:.1f}ms")
            return

        log("PROXY", f"[MISS] {client_ip} GET {path} → forward ke {SERVER_HOST}:{SERVER_PORT}")
        try:
            response = forward_to_server(raw)
            status = extract_status_code(response)
            if status.startswith("2") or status.startswith("3"):
                cache_set(path, response)
                log("PROXY", f"Cache disimpan untuk path={path} ({len(response)}B) | {cache_info()}")

            response_out = patch_response_header(response, "X-Cache: MISS")
            conn.sendall(response_out)
            elapsed = (time.time() - start_time) * 1000
            log("PROXY", f"[MISS] {client_ip} GET {path} | "
                         f"status={status} | size={len(response)}B | {elapsed:.1f}ms")

        except ConnectionError as e:
            err_str = str(e)
            if "Timeout" in err_str:
                conn.sendall(error_response(504, "Gateway Timeout", err_str))
                log("PROXY", f"504 Gateway Timeout: {client_ip} GET {path} | {err_str}")
            else:
                conn.sendall(error_response(502, "Bad Gateway", err_str))
                log("PROXY", f"502 Bad Gateway: {client_ip} GET {path} | {err_str}")

    except socket.timeout:
        log("PROXY", f"Timeout menerima request dari {client_ip}")
    except Exception as e:
        log("PROXY", f"Error dari {client_ip}: {e}")
        try:
            conn.sendall(error_response(502, "Bad Gateway", str(e)))
        except Exception:
            pass
    finally:
        conn.close()


#
# Proxy Server
#
def run_proxy():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((PROXY_HOST, PROXY_PORT))
    server.listen(BACKLOG)

    log("PROXY", "=" * 55)
    log("PROXY", "  Proxy Server  -  TUBES JARKOM MODUL 8")
    log("PROXY", "=" * 55)
    log("PROXY", f"  Listening : {PROXY_HOST}:{PROXY_PORT}")
    log("PROXY", f"  Forward → : {SERVER_HOST}:{SERVER_PORT}")
    log("PROXY", f"  Caching   : IN-MEMORY (thread-safe)")
    log("PROXY", "=" * 55)

    while True:
        try:
            conn, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
            log("PROXY", f"Thread spawn untuk {addr[0]}:{addr[1]} | Active: {threading.active_count()}")
        except KeyboardInterrupt:
            log("PROXY", "Proxy dihentikan.")
            break
        except Exception as e:
            log("PROXY", f"Accept error: {e}")

    server.close()


if __name__ == "__main__":
    try:
        run_proxy()
    except KeyboardInterrupt:
        log("PROXY", "Proxy dimatikan oleh user (Ctrl+C).")
        sys.exit(0)
