import socket
import threading
import os
import sys
import datetime
import mimetypes


#
# Configuration
#
TCP_HOST = "0.0.0.0"
TCP_PORT = 8000
UDP_HOST = "0.0.0.0"
UDP_PORT = 9000
WEBROOT  = os.path.dirname(os.path.abspath(__file__))   # direktori webserver.py
BACKLOG  = 10


#
# Helpers
#
def log(tag: str, message: str):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    log_line = f"[{ts}] [{tag}] {message}"
    print(log_line, flush=True)
    
    # Also write to log file
    try:
        with open("webserver.log", "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
    except:
        pass


#
# HTTP Response Builder
#
def build_response(status_code: int, status_text: str,
                   body: bytes, content_type: str = "text/html; charset=utf-8") -> bytes:
    headers = (
        f"HTTP/1.1 {status_code} {status_text}\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(body)}\r\n"
        f"Connection: close\r\n"
        f"Server: SimpleWebServer/1.0\r\n"
        f"\r\n"
    )
    return headers.encode("utf-8") + body


def response_200(body: bytes, content_type: str = "text/html; charset=utf-8") -> bytes:
    return build_response(200, "OK", body, content_type)


def response_404() -> bytes:
    body = b"<html><body><h1>404 Not Found</h1><p>File tidak ditemukan.</p></body></html>"
    return build_response(404, "Not Found", body)


def response_500(detail: str = "") -> bytes:
    body = f"<html><body><h1>500 Internal Server Error</h1><p>{detail}</p></body></html>".encode()
    return build_response(500, "Internal Server Error", body)


def response_400() -> bytes:
    body = b"<html><body><h1>400 Bad Request</h1></body></html>"
    return build_response(400, "Bad Request", body)


#
# HTTP Request Parser
#
def parse_request(raw: bytes):
    """
    Return (method, path, version) atau raise ValueError jika malformed.
    """
    try:
        header_section = raw.split(b"\r\n\r\n")[0].decode("utf-8", errors="replace")
        lines = header_section.split("\r\n")
        request_line = lines[0]
        parts = request_line.split(" ")
        if len(parts) < 3:
            raise ValueError("Malformed request line")
        method, path, version = parts[0], parts[1], parts[2]
        return method, path, version
    except Exception as e:
        raise ValueError(f"Parse error: {e}")


#
# TCP Connection Handler
#
def handle_tcp_client(conn: socket.socket, addr):
    client_ip = addr[0]
    log("TCP", f"Koneksi masuk dari {client_ip}:{addr[1]}")
    try:
        # Terima data (baca sampai \r\n\r\n)
        raw = b""
        conn.settimeout(10)
        while b"\r\n\r\n" not in raw:
            chunk = conn.recv(4096)
            if not chunk:
                break
            raw += chunk

        if not raw:
            return

        try:
            method, path, version = parse_request(raw)
        except ValueError as e:
            log("TCP", f"Bad Request dari {client_ip}: {e}")
            conn.sendall(response_400())
            return

        # Hanya tangani GET
        if method != "GET":
            body = b"<html><body><h1>405 Method Not Allowed</h1></body></html>"
            resp = build_response(405, "Method Not Allowed", body)
            conn.sendall(resp)
            log("TCP", f"{client_ip} {method} {path} -> 405")
            return

        # Resolve path file
        # Jika path "/" → index.html
        if path == "/" or path == "":
            path = "/index.html"

        # Sanitasi path (cegah directory traversal)
        safe_path = os.path.normpath(path.lstrip("/"))
        file_path = os.path.join(WEBROOT, safe_path)

        # Pastikan dalam WEBROOT
        if not os.path.abspath(file_path).startswith(os.path.abspath(WEBROOT)):
            log("TCP", f"{client_ip} GET {path} -> 403 (traversal attempt)")
            body = b"<html><body><h1>403 Forbidden</h1></body></html>"
            conn.sendall(build_response(403, "Forbidden", body))
            return

        # Baca file
        if os.path.isfile(file_path):
            try:
                mime_type, _ = mimetypes.guess_type(file_path)
                if mime_type is None:
                    mime_type = "application/octet-stream"
                with open(file_path, "rb") as f:
                    body = f.read()
                resp = response_200(body, mime_type)
                conn.sendall(resp)
                log("TCP", f"{client_ip} GET {path} -> 200 OK ({len(body)} bytes)")
            except Exception as e:
                conn.sendall(response_500(str(e)))
                log("TCP", f"{client_ip} GET {path} -> 500 ({e})")
        else:
            conn.sendall(response_404())
            log("TCP", f"{client_ip} GET {path} -> 404 Not Found")

    except socket.timeout:
        log("TCP", f"Timeout koneksi dari {client_ip}")
    except Exception as e:
        log("TCP", f"Error pada {client_ip}: {e}")
    finally:
        conn.close()


#
# TCP Server (HTTP)
#
def run_tcp_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((TCP_HOST, TCP_PORT))
    server.listen(BACKLOG)
    log("TCP", f"Web Server berjalan di {TCP_HOST}:{TCP_PORT} (HTTP)")
    log("TCP", f"Serving files dari: {WEBROOT}")

    while True:
        try:
            conn, addr = server.accept()
            t = threading.Thread(target=handle_tcp_client, args=(conn, addr), daemon=True)
            t.start()
            log("TCP", f"Thread baru untuk {addr[0]}:{addr[1]} | Active threads: {threading.active_count()}")
        except KeyboardInterrupt:
            log("TCP", "Server dihentikan.")
            break
        except Exception as e:
            log("TCP", f"Accept error: {e}")

    server.close()


#
# UDP Server (QoS Echo)
#
def run_udp_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind((UDP_HOST, UDP_PORT))
    log("UDP", f"UDP Echo Server berjalan di {UDP_HOST}:{UDP_PORT}")

    while True:
        try:
            data, addr = server.recvfrom(65535)
            # Echo: kirim balik payload yang sama TANPA modifikasi
            server.sendto(data, addr)
            log("UDP", f"Echo {len(data)} bytes ke {addr[0]}:{addr[1]} | payload: {data.decode('utf-8', errors='replace')[:60]}")
        except KeyboardInterrupt:
            log("UDP", "UDP Server dihentikan.")
            break
        except Exception as e:
            log("UDP", f"Error: {e}")

    server.close()


#
# Main
#
if __name__ == "__main__":
    log("MAIN", "=" * 55)
    log("MAIN", "  Web Server (TCP HTTP + UDP Echo)  -  TUBES JARKOM")
    log("MAIN", "=" * 55)
    log("MAIN", f"  TCP  : {TCP_HOST}:{TCP_PORT}  (HTTP/1.1)")
    log("MAIN", f"  UDP  : {UDP_HOST}:{UDP_PORT}  (Echo/QoS)")
    log("MAIN", f"  Root : {WEBROOT}")
    log("MAIN", "=" * 55)

    # Jalankan UDP di thread terpisah
    udp_thread = threading.Thread(target=run_udp_server, daemon=True)
    udp_thread.start()

    # TCP server di main thread
    try:
        run_tcp_server()
    except KeyboardInterrupt:
        log("MAIN", "Server dimatikan oleh user (Ctrl+C).")
        sys.exit(0)
