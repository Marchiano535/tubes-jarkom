# Tubes Jaringan Komputer – Modul 8
## Implementasi Client-Proxy-Server (Socket Python)

Kelompok 2 orang. Proxy dan web server dijalankan di satu laptop yang sama.

## Struktur File

```
├── webserver.py   ← Web Server (TCP:8000 HTTP + UDP:9000 Echo)
├── proxy.py       ← Proxy Server (TCP:8080, forward + cache)
├── client.py      ← Client (TCP HTTP via Proxy + UDP QoS Pinger)
├── index.html     ← Halaman utama
├── page.html      ← Halaman cache test
├── about.html     ← Halaman about
└── README.md      ← Panduan
```

Perhatian: Tidak boleh ada file Python tambahan. Semua kode ada di 3 file di atas.

## Cara Menjalankan

Urutan penting: jalankan webserver → proxy → client di 3 terminal berbeda.

### 1. Jalankan Web Server dulu
```bash
python webserver.py
```
Harusnya keluar output seperti ini:
```
[MAIN] Web Server berjalan di 0.0.0.0:8000 (HTTP)
[UDP ] UDP Echo Server berjalan di 0.0.0.0:9000
```

### 2. Buka terminal baru, jalankan Proxy
```bash
python proxy.py
```
Output:
```
[PROXY] Listening : 0.0.0.0:8080
[PROXY] Forward → : 127.0.0.1:8000
```

### 3. Terminal ketiga untuk Client

**Mode TCP** (request via proxy):
```bash
python client.py --mode tcp
python client.py --mode tcp --url /page.html --count 3
```

**Mode UDP** (test QoS pinger):
```bash
python client.py --mode udp
python client.py --mode udp --count 20
```

**Atau jalankan keduanya** (both):
```bash
python client.py --mode both
```

**Multi-client simulation** (simulasi beban dengan thread konkuren, minimal 5 client):
```bash
python client.py --mode multi --clients 5
```

## Topologi Jaringan

Karena kelompok 2 orang dan co-located (satu laptop):
```
Laptop B (Client)               Laptop A (Proxy + Web Server)
    client.py ────TCP:8080───► proxy.py
                                    │
                              TCP:8000
                                    │
                              webserver.py
                              (UDP:9000)
```
Jika hanya punya 1 laptop, pakai localhost 127.0.0.1 untuk semua.

## Konfigurasi IP

Bagian atas client.py:
```python
PROXY_HOST  = "192.168.1.11"   # IP Laptop A
SERVER_HOST = "192.168.1.11"   # UDP server
```

Di proxy.py:
```python
SERVER_HOST = "127.0.0.1"      # Co-located
```

Alternatif: pakai argumen command line saat jalankan:
```bash
python client.py --mode tcp --proxy-host 192.168.1.11
python client.py --mode udp --server-host 192.168.1.11
```

## Fitur yang Sudah Diimplementasikan

| Fitur | Status | Keterangan |
|-------|--------|------------|
| TCP HTTP Server | ✅ | GET, parsing header, response HTTP/1.1 |
| Error 404 / 500 | ✅ | Penanganan file tidak ditemukan |
| UDP Echo Server | ✅ | Echo payload tanpa modifikasi |
| Konkurensi (threading) | ✅ | Thread per-connection (server & proxy) |
| Proxy Forwarding | ✅ | Teruskan request client → server |
| Proxy Caching | ✅ | In-memory, thread-safe, HIT/MISS |
| Error 502 / 504 | ✅ | Bad Gateway, Gateway Timeout |
| X-Cache Header | ✅ | HIT/MISS dikirim ke client |
| Client HTTP TCP | ✅ | GET via Proxy, tampilkan HTML |
| Client UDP QoS | ✅ | Kirim 10+ paket, hitung statistik |
| Statistik RTT | ✅ | Min/Avg/Max RTT per paket |
| Packet Loss (%) | ✅ | (lost/sent) × 100 |
| Jitter | ✅ | σ(ΔRTTi) – std deviasi selisih RTT |
| Throughput | ✅ | Total payload / durasi (kbps) |
| Multi-client | ✅ | 5 thread konkuren via `--mode multi` |
| Log lengkap | ✅ | Timestamp, IP, path, status, cache |

## Test Cases

1. **Direct ke web server** (bypass proxy)
   ```bash
   python client.py --mode tcp --proxy-host 127.0.0.1 --proxy-port 8000 --url /index.html
   ```

2. **Test cache** - request yang sama dua kali harus lebih cepat (HIT)
   ```bash
   python client.py --mode tcp --url /page.html
   python client.py --mode tcp --url /page.html
   ```

3. **Test 404**
   ```bash
   python client.py --mode tcp --url /missing.html
   ```

4. **Test UDP echo**
   ```bash
   python client.py --mode udp --count 10
   ```

5. **Test concurrent clients** (min 5)
   ```bash
   python client.py --mode multi --clients 5
   ```

## Troubleshooting

| Gejala | Penyebab | Solusi |
|--🐛 ------|----------|--------|
| `Connection refused` | Server/proxy belum jalan atau port salah | Jalankan urutan: webserver → proxy → client |
| `Timeout UDP` | Firewall memblokir UDP / server crash | Nonaktifkan firewall; pastikan UDP server jalan di port 9000 |
| Cache tidak berfungsi | Proxy belum jalan | Pastikan proxy.py aktif |
| HTML kosong | Parsing HTTP header salah | Pastikan request format `GET /path HTTP/1.1\r\n\r\n` |
| Multi-client blocking | join() dipanggil sebelum semua thread start | Sudah ditangani di client.py (start semua dulu, baru join) |

---

## Parameter QoS (Rumus)

| Parameter | Rumus |
|--📊 Parameter QoS
| RTT | T_recv − T_send |
| Packet Loss | (paket_hilang / total_dikirim) × 100% |
| Jitter | σ(RTTi − RTTi-1) |
| Throughput | total_payload_bytes × 8 / durasi_detik (bps) |

## Deliverables

- [ ] Screenshot log `webserver.py` saat menerima request
- [ ] Screenshot log `proxy.py` menunjukkan Cache HIT dan MISS
- [ ] Screenshot output `client.py --mode tcp` (render HTML)
- [ ] Screenshot output `client.py --mode udp` (statistik QoS)
- [ ] Screenshot `client.py --mode multi --clients 5` (5 instance)
- [ ] Screenshot Wireshark: filter `tcp.port==8000 || tcp.port==8080 || udp.port==9000`

---
