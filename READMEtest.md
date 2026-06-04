# Tubes Jaringan Komputer – Modul 8
## Implementasi Client-Proxy-Server (Socket Python)

Kelompok 2 orang dengan 2 laptop terpisah. Laptop A menjalankan Proxy dan Web Server, Laptop B menjalankan Client.

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

## Cara Menjalankan - Setup 2 Laptop

**Laptop A (Proxy + Web Server):**

**Terminal 1** - Jalankan Web Server:
```bash
python webserver.py
```
Output:
```
[MAIN] Web Server berjalan di 0.0.0.0:8000 (HTTP)
[UDP ] UDP Echo Server berjalan di 0.0.0.0:9000
```

**Terminal 2** - Jalankan Proxy Server:
```bash
python proxy.py
```
Output:
```
[PROXY] Listening : 0.0.0.0:8080
[PROXY] Forward → : 127.0.0.1:8000
```

Catat IP Laptop A (misal `ipconfig` di Windows atau `ifconfig` di Linux).

---

**Laptop B (Client):**

Edit **client.py** baris atas, ubah PROXY_HOST dan SERVER_HOST ke IP Laptop A:
```python
PROXY_HOST  = "192.168.1.10"   # <-- Ganti dengan IP Laptop A
SERVER_HOST = "192.168.1.10"   # <-- Ganti dengan IP Laptop A
```

Lalu jalankan test:

**Mode TCP** (HTTP request via proxy):
```bash
python client.py --mode tcp
python client.py --mode tcp --url /page.html --count 3
```

**Mode UDP** (QoS pinger):
```bash
python client.py --mode udp --server-host 192.168.1.10
```

**Dual mode** (TCP dan UDP):
```bash
python client.py --mode both --proxy-host 192.168.1.10 --server-host 192.168.1.10
```

**Multi-client** (5 concurrent):
```bash
python client.py --mode multi --clients 5 --proxy-host 192.168.1.10
```

Atau edit client.py sekali saja, jadi cukup jalankan tanpa argumen.

## Topologi Jaringan

Setup dengan 2 laptop terpisah:
```
Laptop B (Client)                    Laptop A (Proxy + Web Server)
  client.py ───TCP:8080────────────► proxy.py
                                         │
                                    TCP:8000
                                         │
                                    webserver.py
                                    (UDP:9000)
```

Contoh IP:
- Laptop A: 192.168.1.10 (network 192.168.1.0/24)
- Laptop B: 192.168.1.11

Jika pakai WiFi atau IP berbeda, sesuaikan dengan jaringan lokal kalian.

## Konfigurasi IP

**Di Laptop A (Proxy + Web Server):**

proxy.py - server mendengarkan di semua interface:
```python
PROXY_HOST = "0.0.0.0"      # Listening di semua interface
PROXY_PORT = 8080
SERVER_HOST = "127.0.0.1"   # Forward ke web server lokal
SERVER_PORT = 8000
```

webserver.py - sudah default benar:
```python
TCP_HOST = "0.0.0.0"   # HTTP listening
TCP_PORT = 8000
UDP_HOST = "0.0.0.0"   # Echo listening
UDP_PORT = 9000
```

**Di Laptop B (Client):**

Pastikan client.py menggunakan IP Laptop A (misalnya 192.168.1.10):
```python
PROXY_HOST  = "192.168.1.10"   # IP Laptop A
PROXY_PORT  = 8080
SERVER_HOST = "192.168.1.10"   # IP Laptop A (untuk UDP)
UDP_PORT    = 9000
```

Atau gunakan argumen saat jalankan tanpa edit file:
```bash
python client.py --mode tcp --proxy-host 192.168.1.10
python client.py --mode udp --server-host 192.168.1.10
python client.py --mode both --proxy-host 192.168.1.10 --server-host 192.168.1.10
python client.py --mode multi --clients 5 --proxy-host 192.168.1.10
```

## Cara Cek IP Laptop

**Windows (Laptop A):**
```powershell
ipconfig
```
Cari "IPv4 Address" di bagian Ethernet atau WiFi adapter.

**Linux/Mac:**
```bash
ifconfig
# atau
ip addr
```

## Fitur yang Sudah Diimplementasikan

- TCP HTTP Server (GET saja)
- Error handling: 404, 500, 405
- UDP Echo Server
- Threading untuk concurrent connections
- Proxy forwarding ke server
- In-memory caching (thread-safe)
- X-Cache header menunjukkan HIT/MISS
- Client bisa kirim HTTP request via proxy
- UDP QoS testing (pinger)
- Hitung RTT, Jitter, Packet Loss, Throughput
- Mode multi-client (concurrent load)
- Logging lengkap dengan timestamp
- **CSV export untuk hasil test** (TCP, UDP, Multi-client)
- **File logging** untuk webserver dan proxy

## Test Cases (2 Laptop Setup)

1. **Ping webserver** dari Laptop B (cek koneksi)
   ```bash
   ping 192.168.1.10    # <-- Ganti IP Laptop A
   ```

2. **Test HTTP via proxy** (TCP mode)
   ```bash
   python client.py --mode tcp --proxy-host 192.168.1.10
   ```

3. **Test cache** - request 2x path yang sama
   ```bash
   python client.py --mode tcp --url /page.html --proxy-host 192.168.1.10
   python client.py --mode tcp --url /page.html --proxy-host 192.168.1.10  # HIT
   ```

4. **Test UDP QoS**
   ```bash
   python client.py --mode udp --server-host 192.168.1.10
   ```

5. **Test multi-client** (5 concurrent dari Laptop B)
   ```bash
   python client.py --mode multi --clients 5 --proxy-host 192.168.1.10
   ```

## Troubleshooting

**Setup umum:**
- Pastikan kedua laptop di network yang sama (WiFi atau LAN yang sama)
- Cek IP dengan `ipconfig` (Windows) atau `ifconfig` (Linux/Mac)
- Lakukan ping test untuk memastikan kedua laptop bisa berkomunikasi

**Error: Connection refused**
- Di Laptop A: webserver dan proxy belum jalan atau port sudah dipakai
- Di Laptop B: IP yang digunakan salah atau Laptop A tidak aktif
- Solusi: Jalankan webserver → proxy terlebih dahulu di Laptop A, coba ping dari Laptop B

**Error: Timeout UDP**
- Firewall memblokir UDP (port 9000)
- Solusi: Nonaktifkan firewall Windows atau atur firewall allow port 8000, 8080, 9000

**Cache tidak bekerja**
- Proxy belum aktif di Laptop A
- Solusi: Pastikan `python proxy.py` jalan di Laptop A

**HTML kosong / parsing error**
- Format HTTP request tidak sesuai
- Solusi: Cek format harus `GET /path HTTP/1.1\r\n\r\n`

**Network unreachable**
- Kedua laptop tidak terhubung di network yang sama
- Solusi: Gunakan ping untuk test koneksi, pastikan WiFi/LAN sama

**webserver.log atau proxy.log tidak terbuat**
- File permission issue atau directory tidak writable
- Solusi: Jalankan dengan permission yang sesuai, atau jalankan di home directory

---

## QoS Metrics

- **RTT** = T_recv − T_send
- **Packet Loss** = (paket_hilang / total) × 100%
- **Jitter** = standard deviation dari delta RTT
- **Throughput** = total_bytes × 8 / durasi (bits per second)

## Deliverables

- [ ] Screenshot log `webserver.py` saat menerima request
- [ ] Screenshot log `proxy.py` menunjukkan Cache HIT dan MISS
- [ ] Screenshot output `client.py --mode tcp` (render HTML)
- [ ] Screenshot output `client.py --mode udp` (statistik QoS)
- [ ] Screenshot `client.py --mode multi --clients 5` (5 instance)
- [ ] Screenshot Wireshark: filter `tcp.port==8000 || tcp.port==8080 || udp.port==9000`

## Output Files

Setiap test akan menghasilkan file CSV dengan hasil:
- **TCP Mode**: `tcp_results_YYYYMMDD_HHMMSS.csv` - Hasil request (status, cache, RTT, ukuran)
- **UDP Mode**: `udp_results_YYYYMMDD_HHMMSS.csv` - Statistik QoS (RTT, jitter, packet loss, throughput)
- **Multi-Client**: `multi_client_results_YYYYMMDD_HHMMSS.csv` - Hasil dari setiap client

Log files (real-time):
- **webserver.log** - Catatan semua request HTTP dan UDP echo
- **proxy.log** - Catatan semua request proxy, cache HIT/MISS, error

---
