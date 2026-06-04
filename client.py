import socket
import time
import datetime
import sys
import argparse
import threading
import math


#
# Configuration
#
PROXY_HOST  = "127.0.0.1"
PROXY_PORT  = 8080
SERVER_HOST = "127.0.0.1"   # Langsung ke Web Server untuk UDP
UDP_PORT    = 9000
UDP_TIMEOUT = 1.0            # 1 detik per paket
DEFAULT_UDP_COUNT = 10
DEFAULT_URL = "/index.html"


#
# Helpers
#
def log(tag: str, message: str):
    ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{ts}] [{tag}] {message}", flush=True)


#
# TCP Mode: HTTP Request via Proxy
#
def http_get(path: str = "/index.html") -> dict:
    """
    Kirim HTTP GET ke Proxy, kembalikan dict hasil.
    """
    result = {"path": path, "status": None, "body": "", "size": 0,
              "rtt_ms": None, "cache": ""}

    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {PROXY_HOST}:{PROXY_PORT}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    ).encode("utf-8")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(15)

        t_start = time.time()
        sock.connect((PROXY_HOST, PROXY_PORT))
        sock.sendall(request)

        response_raw = b""
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            response_raw += chunk
        t_end = time.time()
        sock.close()

        rtt_ms = (t_end - t_start) * 1000
        result["rtt_ms"] = rtt_ms
        result["size"]   = len(response_raw)

        # Parse status
        first_line = response_raw.split(b"\r\n")[0].decode("utf-8", errors="replace")
        parts = first_line.split(" ")
        result["status"] = parts[1] if len(parts) >= 2 else "???"

        # Parse X-Cache header
        if b"X-Cache: HIT" in response_raw:
            result["cache"] = "HIT"
        elif b"X-Cache: MISS" in response_raw:
            result["cache"] = "MISS"

        # Ambil body
        sep = response_raw.find(b"\r\n\r\n")
        if sep != -1:
            result["body"] = response_raw[sep+4:].decode("utf-8", errors="replace")

    except ConnectionRefusedError:
        result["status"] = "ERR"
        result["body"]   = f"[ERROR] Proxy tidak bisa dihubungi di {PROXY_HOST}:{PROXY_PORT}"
    except socket.timeout:
        result["status"] = "ERR"
        result["body"]   = "[ERROR] Request timeout"
    except Exception as e:
        result["status"] = "ERR"
        result["body"]   = f"[ERROR] {e}"

    return result


def run_tcp_mode(url: str = DEFAULT_URL, count: int = 1):
    print("\n" + "=" * 60)
    print("  MODE TCP – HTTP Request via Proxy")
    print(f"  Target : {PROXY_HOST}:{PROXY_PORT}{url}")
    print(f"  Jumlah : {count} request")
    print("=" * 60)

    for i in range(1, count + 1):
        print(f"\n── Request #{i} ──────────────────────────────────")
        res = http_get(url)
        status_str = res["status"] if res["status"] else "???"
        cache_str  = f"[{res['cache']}]" if res["cache"] else ""
        rtt_str    = f"{res['rtt_ms']:.1f}ms" if res["rtt_ms"] else "N/A"

        log("TCP", f"GET {res['path']} → HTTP {status_str} {cache_str} | "
                   f"RTT={rtt_str} | size={res['size']}B")

        # Tampilkan body HTML (potong jika terlalu panjang)
        body = res["body"].strip()
        if body:
            preview = body[:800] + ("..." if len(body) > 800 else "")
            print(f"\n{'─'*20} RESPONSE BODY {'─'*20}")
            print(preview)
            print("─" * 55)

        if count > 1 and i < count:
            time.sleep(0.3)

    print("\n[TCP] Selesai.\n")


#
# UDP Mode: QoS Pinger
#
def run_udp_mode(count: int = DEFAULT_UDP_COUNT, target_host: str = SERVER_HOST):
    print("\n" + "=" * 60)
    print("  MODE UDP – QoS Pinger")
    print(f"  Target : {target_host}:{UDP_PORT}")
    print(f"  Paket  : {count}")
    print(f"  Timeout: {UDP_TIMEOUT}s per paket")
    print("=" * 60 + "\n")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(UDP_TIMEOUT)

    rtts        = []
    sent        = 0
    received    = 0
    total_bytes = 0
    t_session_start = time.time()

    for seq in range(1, count + 1):
        timestamp_send = time.time()
        payload = f"Ping {seq} {timestamp_send:.6f}".encode("utf-8")

        try:
            sock.sendto(payload, (target_host, UDP_PORT))
            sent += 1

            data, _ = sock.recvfrom(65535)
            timestamp_recv = time.time()

            rtt_ms = (timestamp_recv - timestamp_send) * 1000
            rtts.append(rtt_ms)
            received += 1
            total_bytes += len(data)

            log("UDP", f"seq={seq:3d} | RTT={rtt_ms:7.3f}ms | payload={data.decode('utf-8', errors='replace')[:50]}")

        except socket.timeout:
            log("UDP", f"seq={seq:3d} | Request timed out")

        time.sleep(0.1)   # Jeda antar paket

    sock.close()
    t_session_end = time.time()
    duration_s = t_session_end - t_session_start

    # Statistics
    lost        = sent - received
    loss_pct    = (lost / sent * 100) if sent > 0 else 0
    throughput  = (total_bytes * 8 / 1000 / duration_s) if duration_s > 0 else 0  # kbps

    # Jitter: std deviasi selisih RTT berurutan σ(RTTi - RTTi-1)
    jitter = 0.0
    if len(rtts) >= 2:
        deltas = [abs(rtts[i] - rtts[i-1]) for i in range(1, len(rtts))]
        mean_d = sum(deltas) / len(deltas)
        jitter = math.sqrt(sum((d - mean_d)**2 for d in deltas) / len(deltas))

    rtt_min = min(rtts) if rtts else 0
    rtt_avg = sum(rtts) / len(rtts) if rtts else 0
    rtt_max = max(rtts) if rtts else 0

    print("\n" + "=" * 60)
    print("  STATISTIK QoS UDP")
    print("=" * 60)
    print(f"  Paket Dikirim  : {sent}")
    print(f"  Paket Diterima : {received}")
    print(f"  Packet Loss    : {loss_pct:.1f}%  ({lost}/{sent})")
    print(f"  RTT Min        : {rtt_min:.3f} ms")
    print(f"  RTT Avg        : {rtt_avg:.3f} ms")
    print(f"  RTT Max        : {rtt_max:.3f} ms")
    print(f"  Jitter         : {jitter:.3f} ms  (σ ΔRTTi)")
    print(f"  Throughput     : {throughput:.3f} kbps")
    print(f"  Durasi Sesi    : {duration_s:.2f} s")
    print("=" * 60 + "\n")

    return {
        "sent": sent, "received": received, "loss_pct": loss_pct,
        "rtt_min": rtt_min, "rtt_avg": rtt_avg, "rtt_max": rtt_max,
        "jitter": jitter, "throughput_kbps": throughput
    }


#
# Multi-Client Mode: Concurrent Load Simulation
#
def run_multi_client(url: str = DEFAULT_URL, num_clients: int = 5):
    """
    Jalankan N client secara bersamaan (single-machine simulation).
    Setiap client membuat koneksi TCP sendiri ke Proxy.
    """
    print("\n" + "=" * 60)
    print(f"  MODE MULTI-CLIENT – {num_clients} instance konkuren")
    print(f"  Target : {PROXY_HOST}:{PROXY_PORT}{url}")
    print("=" * 60 + "\n")

    results = [None] * num_clients
    threads = []

    def client_task(idx, path):
        log("MC", f"Client-{idx+1} START")
        t0 = time.time()
        res = http_get(path)
        elapsed = (time.time() - t0) * 1000
        results[idx] = res
        cache_str = f"[{res['cache']}]" if res["cache"] else ""
        rtt_str   = f"{res['rtt_ms']:.1f}ms" if res["rtt_ms"] else "N/A"
        log("MC", f"Client-{idx+1} DONE | status={res['status']} {cache_str} | "
                  f"RTT={rtt_str} | total={elapsed:.1f}ms")

    # Setiap client request path berbeda (uji MISS) dan sama (uji HIT)
    paths = [url] * num_clients
    # Client ganjil request path berbeda untuk memicu cache MISS
    alternate_paths = ["/index.html", "/page.html", "/about.html", "/index.html", "/page.html"]
    for i in range(min(num_clients, len(alternate_paths))):
        paths[i] = alternate_paths[i]

    t_start = time.time()
    for i in range(num_clients):
        t = threading.Thread(target=client_task, args=(i, paths[i]))
        threads.append(t)

    # Start semua hampir bersamaan
    for t in threads:
        t.start()

    for t in threads:
        t.join()

    t_total = (time.time() - t_start) * 1000

    # Ringkasan
    print(f"\n── Ringkasan Multi-Client ──────────────────────────")
    success = sum(1 for r in results if r and r["status"] == "200")
    print(f"  Total   : {num_clients} clients")
    print(f"  Sukses  : {success}/{num_clients}")
    print(f"  Durasi  : {t_total:.1f}ms (total wall-clock)")
    avg_rtt = sum(r["rtt_ms"] for r in results if r and r["rtt_ms"]) / max(success, 1)
    print(f"  RTT Avg : {avg_rtt:.1f}ms")
    hits  = sum(1 for r in results if r and r["cache"] == "HIT")
    misses= sum(1 for r in results if r and r["cache"] == "MISS")
    print(f"  Cache   : {hits} HIT, {misses} MISS")
    print("─" * 55 + "\n")


#
# Argument Parser
#
def parse_args():
    parser = argparse.ArgumentParser(
        description="TUBES JARKOM - Client (TCP/UDP)",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "Contoh:\n"
            "  python client.py --mode tcp\n"
            "  python client.py --mode tcp --url /page.html --count 3\n"
            "  python client.py --mode udp --count 15\n"
            "  python client.py --mode both\n"
            "  python client.py --mode multi --clients 5\n"
        )
    )
    parser.add_argument("--mode", choices=["tcp", "udp", "both", "multi"],
                        default="tcp",
                        help="Mode: tcp | udp | both | multi (default: tcp)")
    parser.add_argument("--url",     default=DEFAULT_URL,
                        help=f"Path URL untuk request TCP (default: {DEFAULT_URL})")
    parser.add_argument("--count",   type=int, default=1,
                        help="Jumlah request TCP atau paket UDP (default: 1 / 10)")
    parser.add_argument("--clients", type=int, default=5,
                        help="Jumlah client konkuren untuk mode multi (default: 5)")
    parser.add_argument("--proxy-host", default=PROXY_HOST,
                        help=f"IP Proxy (default: {PROXY_HOST})")
    parser.add_argument("--proxy-port", type=int, default=PROXY_PORT,
                        help=f"Port Proxy (default: {PROXY_PORT})")
    parser.add_argument("--server-host", default=SERVER_HOST,
                        help=f"IP Web Server untuk UDP (default: {SERVER_HOST})")
    parser.add_argument("--udp-port", type=int, default=UDP_PORT,
                        help=f"Port UDP Echo (default: {UDP_PORT})")
    return parser.parse_args()


#
# Main
#
if __name__ == "__main__":
    args = parse_args()

    # Override global config dari args
    PROXY_HOST  = args.proxy_host
    PROXY_PORT  = args.proxy_port
    SERVER_HOST = args.server_host
    UDP_PORT    = args.udp_port

    print("\n" + "=" * 60)
    print("  TUBES JARKOM MODUL 8 – CLIENT")
    print(f"  Proxy  : {PROXY_HOST}:{PROXY_PORT}")
    print(f"  Server : {SERVER_HOST}:{UDP_PORT} (UDP)")
    print("=" * 60)

    mode = args.mode

    if mode == "tcp":
        count = args.count if args.count > 0 else 1
        run_tcp_mode(url=args.url, count=count)

    elif mode == "udp":
        count = args.count if args.count >= 10 else DEFAULT_UDP_COUNT
        run_udp_mode(count=count, target_host=SERVER_HOST)

    elif mode == "both":
        run_tcp_mode(url=args.url, count=args.count if args.count > 0 else 1)
        run_udp_mode(count=max(args.count, DEFAULT_UDP_COUNT), target_host=SERVER_HOST)

    elif mode == "multi":
        run_multi_client(url=args.url, num_clients=args.clients)
